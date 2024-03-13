from __future__ import annotations

from typing import Callable
from typing import Coroutine

import numpy as np
from systemrdl import RDLCompiler

from peakrdl_sv.listener import Listener
from peakrdl_sv.node import AddressMap
from peakrdl_sv.node import Register

WriteCallback = Callable[[int, int, int], None]
AsyncWriteCallback = Callable[[int, int, int], Coroutine[None, None, None]]


class CallbackSet:
    """Class to hold a set of callbacks, this reduces the number of callback that need
    to be passed around

    :param write_callback: write regardless of space, defaults to None
    :type write_callback: Optional[WriteCallback], optional
    :param write_block_callback: write and block if no space, defaults to None
    :type write_block_callback: Optional[AsyncWriteCallback], optional
    """

    __slots__ = ["_write_callback", "_write_block_callback"]

    def __init__(
        self,
        write_callback: WriteCallback | None = None,
        write_block_callback: AsyncWriteCallback | None = None,
    ):
        self._write_callback = write_callback
        self._write_block_callback = write_block_callback

    @property
    def write_callback(self) -> WriteCallback | None:
        """single non-blocking write callback function

        :return: call back function
        :rtype: Optional[WriteCallback]
        """
        return self._write_callback

    @property
    def write_block_callback(self) -> AsyncWriteCallback | None:
        """single blocking write callback function

        :return: call back function
        :rtype: Optional[AsyncWriteCallback]
        """
        return self._write_block_callback


class RegModel:
    """Register Abstraction Layer Model

    :param rdlfile: the rdl file from which we create the model
    :type rdlfile: str
    :param callbacks: the set of coco.tb callbacks to perform read/write operations
    :type callbacks: CallbackSet
    """

    def __init__(self, rdlfile: str, callbacks: CallbackSet):
        self._callbacks = callbacks
        self._top_node: AddressMap = self._parse_rdl(rdlfile)
        self._reg_map = self._map_registers()
        self._desired_values = self._map_fields()

    # --------------------------------------------------------------------------------
    # Initialisation
    # --------------------------------------------------------------------------------

    def _parse_rdl(self, rdlfile: str) -> AddressMap:
        rdlc = RDLCompiler()
        rdlc.compile_file(rdlfile)
        root = rdlc.elaborate()
        listener = Listener()
        listener.walk(root, unroll=True)
        return listener.top_node

    def _map_registers(self) -> dict[str, Register]:
        """Builds a dictionary which maps register relative paths to the register
        itself, from which its properties may be extracted

        :return: A map of register relative paths to Register objects
        :rtype: Dict[str, Register]
        """
        return {
            register.path("."): register for register in self._top_node.get_registers()
        }

    def _map_fields(self) -> dict[str, dict[str, int]]:
        """Builds the desired value dictionary

        :raises AttributeError: _description_
        :return: _description_
        :rtype: Dict[str, Dict[str, int]]
        """

        if not hasattr(self, "_reg_map"):
            raise AttributeError(
                "Must call self._map_registers() before self._map_desired_values()",
            )
        # An empty dictionary which maps each reg name to a dictionary of field names
        # that maps to the field values
        return {
            reg_name: dict.fromkeys([field.name for field in reg.fields()])
            for reg_name, reg in self._reg_map.items()
        }

    # --------------------------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------------------------

    def get_register_by_name(self, reg_name: str) -> Register | None:
        """Gets a register by its relative path name, '.' separated per tier of the
        hierarchy

        :param reg_name: The register name as a . separater string
        :type reg_name: str
        :return: the target register, None if the register name is not found in the
        regmap
        :rtype: Register | None
        """
        try:
            return self._reg_map[reg_name]
        except KeyError:
            return None

    # --------------------------------------------------------------------------------
    # Generic read and write wrappers
    # --------------------------------------------------------------------------------

    async def write(
        self,
        reg_name_or_addr: str | int,
        data: int | None = None,
        **kwargs,
    ) -> None:
        """Writes the value of the DUT register. Three options for calling:

        (1) absolute addr + data -> write to absolute address a particular value
        (2) register name + data -> write to named register a particular value
        (3) register name -> write desired value to a named register

        :param reg_name_or_addr: Register name or address to write to
        :type reg_name_or_addr: str | int
        :param data: Data to write to register, defaults to None
        :type data: int | None, optional
        :raises TypeError: non int or string `reg_name_or_addr`
        """

        async def write_desired_to_named_reg(reg_name: str):
            """Writes a desired value to the DUT"""

            target = self.get_register_by_name(reg_name)

            # write the register value as multiple <accesswidth> chunks
            if target.regwidth > target.accesswidth:
                for desired, field in zip(
                    self._desired_values[reg_name].values(),
                    target.fields(),
                ):
                    await self.write(field.absolute_address, desired)

            # one singular write
            else:
                await self._callbacks.write_block_callback(
                    target.absolute_address,
                    self.get(reg_name),
                    **kwargs,
                )

        async def write_literal_to_named_reg(reg_name: str, data: int):
            """Writes a literal value to a register specified by name or absolute
            address"""

            target = self.get_register_by_name(reg_name)

            # write the register value as multiple <accesswidth> chunks
            if target.regwidth > target.accesswidth:
                mask = (1 << target.accesswidth) - 1
                for i in range(target.subregs):
                    write_data = data >> (target.accesswidth * i) | mask
                    await self._callbacks.write_block_callback(
                        target.absolute_address,
                        write_data,
                        **kwargs,
                    )

            # one singular write
            else:
                await self._callbacks.write_block_callback(
                    target.absolute_address,
                    data,
                    **kwargs,
                )

        async def write_literal_to_addressed_reg(reg_addr: int, data: int):
            """Writes a literal value to a register (or field) specified by an absolute
            address"""
            await self._callbacks.write_block_callback(reg_addr, data, **kwargs)

        # if no data is provided we write the value in self._desired_value
        if data is None:
            assert isinstance(
                reg_name_or_addr,
                str,
            ), "Must provide register name when writing without explicit data"

            await write_desired_to_named_reg(reg_name_or_addr)

        # otherwise we write the data provided by the user
        else:
            if isinstance(reg_name_or_addr, str):
                await write_literal_to_named_reg(reg_name_or_addr, data)
            elif isinstance(reg_name_or_addr, int):
                await write_literal_to_addressed_reg(reg_name_or_addr, data)
            else:
                raise TypeError(
                    f"Incorrect type {type(reg_name_or_addr)} passed to write()",
                )

    async def read(self, reg_name_or_addr: str | int) -> int:
        """Reads the value of the DUT register

        :param reg_name_or_addr: _description_
        :type reg_name_or_addr: str | int
        :raises NotImplementedError: _description_
        :return: _description_
        :rtype: int
        """
        raise NotImplementedError(self.read)

    # --------------------------------------------------------------------------------
    # UVM Register operations
    # --------------------------------------------------------------------------------

    def set(self, reg_name: str, value: int) -> None:
        """Sets a the desired value of a register, does not perform a read of the DUT
        value

        need to split the passed in value over the bits of the field
        i.e. if you pass in 0xE6 and the register has format
        reg {
            field {} data0 [1:0]
            field {} data1 [7:4]
        }
        then we'd have data0 = 2b10, data1 = 4b1110

        :param reg_name: _description_
        :type reg_name: str
        :param value: _description_
        :type value: int
        """
        target = self.get_register_by_name(reg_name)

        # format the write value an `targer-size`-bit binary string
        bits = f"{value:0{target.regwidth}b}"  # FIXME?

        # Extract the bits we are going to write and conver them to int
        masked_values = []
        for field in target.fields():
            upper, lower = field.get_cpuif_bit_slice().split(":")
            masked_values.append(int(bits[int(lower) : int(upper)], 2))  # noqa: E203

        # Write the values to the respective fields
        for idx, key in enumerate(self._desired_values[reg_name].keys()):
            self._desired_values[reg_name][key] = masked_values[idx]

    def set_field(self, reg_name: str, field_name: str, value: int) -> None:
        """Updates the value of a field in the desired value and not the field value in
        the DUT

        :param reg_name: The name of the register you are targeting
        :type reg_name: str
        :param field_name: The name of the field to update
        :type field_name: str
        :param value: the value to write to the field
        :type value: int
        """
        try:
            self._desired_values[reg_name][field_name] = value
        except KeyError as e:
            raise Exception(
                f"The specified field ({reg_name}.{field_name}) does not exist!",
            ) from e

    def get(self, reg_name: str) -> int:
        """Reads the desired value of a register

        :param reg_name: _description_
        :type reg_name: str
        :return: _description_
        :rtype: int
        """
        target = self.get_register_by_name(reg_name)

        value = 0
        for desired, field in zip(
            self._desired_values[reg_name].values(),
            target.fields(),
        ):
            # shift in the value at the offset given by the actual field
            value = value | (desired << field.lsb)

        return value

    def get_field(self, reg_name: str, field_name: str) -> int:
        """Gets a a field value from the register desired value and not the field value
        in the DUT

        :param reg_name: The name of the register you are targeting
        :type reg_name: str
        :param field_name: The name of the field to update
        :type field_name: str
        :return: The field's value
        :rtype: int
        """
        try:
            return self._desired_values[reg_name][field_name]
        except KeyError as e:
            raise Exception(
                f"The specified field ({reg_name}.{field_name}) does not exist!",
            ) from e

    def randomize(self, reg_name: str):
        """randomizes the value of a register

        :raises NotImplementedError: _description_
        """
        target = self.get_register_by_name(reg_name)
        self.set(reg_name, np.random.randint(0, 1 << target.regwidth))  # TODO: fixme

    def reset(self, reg_name: str) -> None:
        """Resets the desired value of a register

        :param reg_name: The register you wish to reset
        :type reg_name: str
        """
        target = self.get_register_by_name(reg_name)

        # get the field reset values
        reset_values = [field.reset or 0 for field in target.fields()]

        # write each reset value to each field
        for idx, key in enumerate(self._desired_values[reg_name].keys()):
            self._desired_values[reg_name][key] = reset_values[idx]

    def reset_field(self, reg_name: str, field_name: str) -> None:
        """Resets the desired value of a field within a register

        :param reg_name: The register you wish to target
        :type reg_name: str
        :param field_name: The field you wish to reset
        :type field_name: str
        """
        target = self.get_register_by_name(reg_name)

        # get the reset value of the targeted field
        idx = self._desired_values[reg_name].keys().index(field_name)
        reset_value = target.fields()[idx].reset or 0

        # set the reset value
        self._desired_values[reg_name][field_name] = reset_value
