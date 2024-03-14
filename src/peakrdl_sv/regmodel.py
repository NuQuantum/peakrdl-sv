from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Generator

import numpy as np
from systemrdl import RDLCompiler

from peakrdl_sv.callbacks import CallbackSet
from peakrdl_sv.listener import Listener
from peakrdl_sv.node import AddressMap
from peakrdl_sv.node import Field
from peakrdl_sv.node import Register


@dataclass
class FieldWrapper:
    """Wraps a Field by storing along side it a (desired) value"""

    field: Field
    value: int


class RegModel:
    """Register Abstraction Layer Model

    :param rdlfile: The rdl file from which we create the model
    :type rdlfile: str
    :param callbacks: The set of coco.tb callbacks to perform read/write operations
    :type callbacks: CallbackSet
    :param log: A logger
    :type log: Any
    """

    def __init__(self, rdlfile: str, callbacks: CallbackSet, log):
        self._callbacks = callbacks
        self._top_node: AddressMap = self._parse_rdl(rdlfile)
        self._reg_map = self._map_registers()
        self._desired_values = self._map_fields()
        self._log = log

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

    def _map_fields(self) -> dict[str, dict[str, FieldWrapper]]:
        """Maps register names to dictionaries of fields which maps to (desired) values

        :raises AttributeError: _map_fields called before _map_registers
        :return: A dict of {register names : dict of {field names : (field, value)}}
        :rtype: Dict[str, Dict[str, FieldWrapper]]
        """

        if not hasattr(self, "_reg_map"):
            raise AttributeError(
                "Must call self._map_registers() before self._map_desired_values()",
            )

        return {
            reg_name: {field.inst_name: FieldWrapper(field, 0) for field in reg}
            for reg_name, reg in self._reg_map.items()
        }

    # --------------------------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------------------------

    def get_register_by_name(self, reg_name: str) -> Register | None:
        """Gets a register by its relative path name, '.' separated per tier of the
        hierarchy

        :param reg_name: The register name as a . separated string
        :type reg_name: str
        :return: The target register, None if the register name is not found in the
        regmap
        :rtype: Register | None
        """
        try:
            return self._reg_map[reg_name]
        except KeyError:
            self._log.info(f"Could not find register in {self._reg_map.keys()}")
            return None

    def split_value_over_fields(
        self,
        target: Register,
        value: int,
    ) -> Generator[tuple[Any, int], Any, None]:
        """Split a value over the fields of a register with correct masking depending
        on the field location

        :param target: The register to target
        :type target: Register
        :param value: The value to write to the registers
        :type value: int
        :yield: tuples of the field address and the value to write
        :rtype: Generator[tuple[Any, int], Any, None]
        """

        # format the write value an `regwidth`-bit binary string
        bits = f"{value:0{target.regwidth}b}"

        # Extract the bits we are going to write and conver them to int
        for field in target:
            # get the slice indices of the field
            lower = target.regwidth - field.msb - 1
            upper = target.regwidth - field.lsb

            # perform the slice (python slicing non inclusive)
            yield (field.absolute_address, int(bits[lower:upper], 2))  # noqa: E203

    # --------------------------------------------------------------------------------
    # Generic read and write wrappers
    # --------------------------------------------------------------------------------

    async def write(self, reg_name: str, data: int | None = None, **kwargs) -> None:
        """Writes the value of the DUT register. Two options for calling:

        (1) register name + data -> write to named register a particular value
        (2) register name -> write desired value to a named register

        :param reg_name: Register name to write to
        :type reg_name: str | int
        :param data: Data to write to register, defaults to None
        :type data: int | None, optional
        """

        async def write_desired_to_named_reg(reg_name: str):
            """Writes a desired value to the DUT"""

            target = self.get_register_by_name(reg_name)

            # write the register value as multiple `accesswidth` chunks
            if target.regwidth > target.accesswidth:
                for field in target:
                    await self._callbacks.async_write_callback(
                        field.absolute_address,
                        self._desired_values[reg_name][field.inst_name].value,
                        **kwargs,
                    )

            # one singular write
            else:
                await self._callbacks.async_write_callback(
                    target.absolute_address,
                    self.get(reg_name),
                    **kwargs,
                )

        async def write_literal_to_named_reg(reg_name: str, data: int):
            """Writes a literal value to a register specified by name or absolute
            address"""

            target = self.get_register_by_name(reg_name)

            for address, value in self.split_value_over_fields(target, data):
                # write the value
                await self._callbacks.async_write_callback(
                    address,
                    value,
                    **kwargs,
                )  # noqa: E203

        # if no data is provided we write the value in self._desired_value
        if data is None:
            assert isinstance(
                reg_name,
                str,
            ), "Must provide register name when writing without explicit data"
            await write_desired_to_named_reg(reg_name)

        # otherwise we write the data provided by the user
        else:
            await write_literal_to_named_reg(reg_name, data)
            # update the desired value
            self.set(reg_name, data)

    async def read(self, reg_name: str, field_name: str | None = None) -> int:
        """Reads the value of a register or field from the DUT

        :param reg_name: The register name to read from
        :type reg_name: str
        :param field_name: The field name to read from, defaults to None
        :type field_name: str | None, optional
        :return: The value read from the DUT
        :rtype: int
        """

        target = self.get_register_by_name(reg_name)

        async def read_register(target: Register) -> int:
            """Reads a register, including all fields"""

            result = 0
            for i, field in enumerate(target):
                addr = field.absolute_address
                value = await self._callbacks.async_read_callback(addr)
                result = result | (value << (target.accesswidth * i))
            return result

        async def read_field(target: Register, field_name: str) -> int:
            """Reads an individual field from a regster and references to 0"""

            def get_target_field(target: Register) -> Field:
                for field in target:
                    if field.inst_name == field_name:
                        return field

            # find the field absolute address
            target_field = get_target_field(target)

            # perform the read
            addr = target_field.absolute_address
            value = await self._callbacks.async_read_callback(addr)

            return value >> target_field.lsb

        if field_name is None:
            return await read_register(target)
        else:
            return await read_field(target, field_name)

    # --------------------------------------------------------------------------------
    # UVM Register operations
    # --------------------------------------------------------------------------------

    def set(self, reg_name: str, value: int) -> None:
        """Sets a the desired value of a register

        This method will split the passed in value over the bits of the field
        i.e. if you pass in 0xE5 == 0b11101010 and the register has the format
        reg my_reg {
            field {} data0 [1:0]
            field {} data1 [7:4]
        }
        then we'd have data0 = 2b10, data1 = 4b1110

        :param reg_name: The target register's name
        :type reg_name: str
        :param value: The value to write to the register
        :type value: int
        """
        target = self.get_register_by_name(reg_name)

        # Extract the bits we are going to write and conver them to int
        masked_values = []
        for _, value in self.split_value_over_fields(target, value):
            masked_values.append(value)

        # Write the values to the respective fields
        for idx, field in enumerate(target):
            self._desired_values[reg_name][field.inst_name].value = masked_values[idx]

    def set_field(self, reg_name: str, field_name: str, value: int) -> None:
        """Sets the desired value of a field

        :param reg_name: The target register's name
        :type reg_name: str
        :param field_name: The name of the field to update
        :type field_name: str
        :param value: the value to write to the field
        :type value: int
        """
        try:
            self._desired_values[reg_name][field_name].value = value
        except KeyError as e:
            raise Exception(
                f"The specified field ({reg_name}.{field_name}) does not exist!"
                f" ({self._desired_values.keys()})",
            ) from e

    def get(self, reg_name: str) -> int:
        """Gets the desired value of a register

        :param reg_name: The target register's name
        :type reg_name: str
        :return: the register's value
        :rtype: int
        """
        target = self.get_register_by_name(reg_name)

        value = 0
        for field in target:
            # shift in the value at the offset given by the actual field
            part = self._desired_values[reg_name][field.inst_name].value << field.lsb
            value = value | part

        return value

    def get_field(self, reg_name: str, field_name: str) -> int:
        """Gets the desired value of a field

        :param reg_name: The target register's name
        :type reg_name: str
        :param field_name: The name of the field to update
        :type field_name: str
        :return: The field's value
        :rtype: int
        """
        try:
            return self._desired_values[reg_name][field_name].value
        except KeyError as e:
            raise Exception(
                f"The specified field ({reg_name}.{field_name}) does not exist!"
                f" ({self._desired_values.keys()})",
            ) from e

    def randomize(self, reg_name: str):
        """Randomizes the value of a register

        :param reg_name: The name of the register to randomise
        :type reg_name: str
        """
        target = self.get_register_by_name(reg_name)
        self.set(reg_name, np.random.randint(0, 1 << target.regwidth))

    def reset(self, reg_name: str) -> None:
        """Resets the desired value of a register

        :param reg_name: The register you wish to reset
        :type reg_name: str
        """
        target = self.get_register_by_name(reg_name)

        # write each reset value to each field
        for field in target:
            self._desired_values[reg_name][field.inst_name].value = field.reset or 0

    def reset_field(self, reg_name: str, field_name: str) -> None:
        """Resets the desired value of a field within a register

        :param reg_name: The register you wish to target
        :type reg_name: str
        :param field_name: The field you wish to reset
        :type field_name: str
        """
        target = self._desired_values[reg_name][field_name]

        # set the reset value
        target.value = target.field.reset or 0
