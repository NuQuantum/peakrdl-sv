"""Provide classes for modelling register access in a coco.tb simulation."""

from __future__ import annotations

import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import numpy as np
from systemrdl import RDLCompiler

from peakrdl_sv.callbacks import CallbackSet
from peakrdl_sv.listener import Listener
from peakrdl_sv.node import AddressMap, Field, Register


@dataclass
class FieldWrapper:
    """Wraps a Field by storing along side it a (desired) value."""

    field: Field
    value: int


class RegModel:
    """Register Abstraction Layer Model.

    This class provides an interface for interacting with a SystenRFL register map
    within an RTL simulation

    """

    def __init__(
        self,
        rdlfile: str,
        callbacks: CallbackSet,
        log: logging.Logger,
        debug: bool = False,
    ) -> None:
        """Initialise the RAL model.

        Args:
            rdlfile(str): The rdl file from which we create the model
            callbacks(CallbackSet): The set of coco.tb callbacks to perform read/write operations
            log(logging.Logger): A logger
            debug (bool): If true, set log level to debug.

        """  # noqa: E501
        self._callbacks = callbacks
        self._top_node: AddressMap = self._parse_rdl(rdlfile)
        self._reg_map = self._map_registers()
        self._desired_values = self._map_fields()
        self._log = log

        if debug:
            self._log.setLevel(logging.DEBUG)

    # --------------------------------------------------------------------------------
    # Initialisation
    # --------------------------------------------------------------------------------

    def _parse_rdl(self, rdlfile: str) -> AddressMap:
        """Parse the RDL file into an AddressMap object.

        Args:
            rdlfile (str): Path to the address map

        Returns:
            AddressMap: The generated PeakRDL-sv AddressMap

        """
        rdlc = RDLCompiler()
        rdlc.compile_file(rdlfile)
        root = rdlc.elaborate()
        listener = Listener()
        listener.walk(root, unroll=True)
        return listener.top_node

    def _map_registers(self) -> dict[str, Register]:
        """Build a dictionary which maps register relative paths to the register.

        Returns:
          Dict[str, Register]: A map of register relative paths to Register objects

        """
        return {
            register.path("."): register for register in self._top_node.get_registers()
        }

    def _map_fields(self) -> dict[str, dict[str, FieldWrapper]]:
        """Map register names to dictionaries of fields which maps to (desired) values.

        Returns:
          Dict[str, Dict[str, FieldWrapper]]: A dict of {register names : dict of {field names : (field, value)}}

        Raises:
          AttributeError: _map_fields called before _map_registers

        """  # noqa: E501
        try:
            return {
                reg_name: {
                    field.inst_name: FieldWrapper(field, field.reset or 0)
                    for field in reg
                }
                for reg_name, reg in self._reg_map.items()
            }
        except AttributeError as e:
            raise Exception(
                "Must call self._map_registers() before self._map_fields()",
            ) from e

    # --------------------------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------------------------

    def get_register_by_name(self, reg_name: str) -> Register | None:
        """Get a register by its relative path name.

        The reg_name must be '.' separated per tier of the hierarchy.

        Args:
          reg_name(str): The register name as a . separated string

        Returns:
          Register | None: The target register, None if the register name is not found

        """
        try:
            return self._reg_map[reg_name]
        except KeyError as e:
            raise KeyError(f"Could not find register in {self._reg_map.keys()}") from e

    def get_field_by_name(self, reg_name: str, field_name: str) -> FieldWrapper:
        """Get a field by its relative path.

        Args:
          reg_name(str): The register name as a . separated string
          field_name(str): The field name within the register

        Returns:
          FieldWrapper: The target field and its desired value as a FieldWrapper

        """
        try:
            return self._desired_values[reg_name][field_name]
        except KeyError as e:
            all_keys = (
                *self._desired_values.keys(),
                *self._desired_values[reg_name].keys(),
            )
            raise KeyError(f"Could not find field in {all_keys}") from e

    def split_value_over_fields(
        self,
        target: Register,
        value: int,
    ) -> Generator[tuple[Any, int], Any, None]:
        """Split a value over the fields of a register with correct masking depending on the field location.

        Args:
          target(Register): The register to target
          value(int):  The value to write to the registers

        Yields:
            tuples of the field address and the value to write)

        """  # noqa: E501
        # format the write value as a `regwidth`-bit binary string
        bits = f"{value:0{target.regwidth}b}"

        # Extract the bits we are going to write and convert them to int
        for field in target:
            # get the slice indices of the field
            lower = target.regwidth - field.msb - 1
            upper = target.regwidth - field.lsb

            # perform the slice (python slicing non inclusive)
            yield (field.absolute_address, int(bits[lower:upper], 2))

    # --------------------------------------------------------------------------------
    # Generic read and write wrappers
    # --------------------------------------------------------------------------------

    async def write(
        self,
        reg_name: str,
        data: int | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Write the value of the DUT register.

        Two options for calling:
        (1) register name + data -> write to named register a particular value
        (2) register name -> write desired value to a named register

        Args:
            reg_name (str | int): Register name to write to
            data (int | None): Data to write to register, defaults to None
            kwargs (Any): kwargs to pass to async_write_callback

        """
        self._log.debug(f"Performing write to target register {reg_name}")

        target = self.get_register_by_name(reg_name)

        self._log.debug(f"Target ({reg_name}) has {target.subregs} subregs")

        # If no data provided, get from mirror get the register value
        write_data = data if data is not None else self.get(reg_name)

        # we need to write in `accesswidth` chunks
        for subreg in range(target.subregs):
            # shift and mask the value to write
            shifted = write_data >> (target.accesswidth * subreg)
            masked = shifted & ((1 << target.accesswidth) - 1)

            # write the word
            self._log.debug(
                f"Writing data {hex(masked)} to addr"
                f" {target.absolute_address + subreg} ",
            )

            await self._callbacks.async_write_callback(
                target.absolute_address + subreg,
                masked,
                **kwargs,
            )

        # set mirrored value if we provided a new value to write
        if data is not None:
            self.set(reg_name, data)

    async def read(self, reg_name: str, field_name: str | None = None) -> int:
        """Read the value of a register or field from the DUT.

        reg_name (str): The register name to read from
        field_name (str | None): The field name to read from, defaults to None

        Returns:
            int: The value read from the DUT

        """
        self._log.debug(f"Performing read from target register {reg_name}.{field_name}")

        target = self.get_register_by_name(reg_name)

        self._log.debug(
            f"Target ({reg_name}.{field_name}) has {target.subregs} subregs",
        )

        async def read_register(target: Register) -> int:
            """Readsa registers in `accesswidth` sized chunks."""
            result = 0
            # if its wide we need to read in accesswidth chunks
            for subreg in range(target.subregs):
                addr = target.absolute_address + subreg
                value = await self._callbacks.async_read_callback(addr)
                self._log.debug(f"Read value: {hex(value)}")
                result = result | (value << (target.accesswidth * subreg))
            return result

        async def read_field(target: Register, field_name: str) -> int:
            """Read an individual field from a regster and references it to 0.

            Assumes field width is limited by access width
            """
            # find the field
            target_field = self.get_field_by_name(target.name, field_name).field

            # perform the read
            addr = target_field.absolute_address
            value = await self._callbacks.async_read_callback(addr)

            # Refer the field to zero and mask out higher bits
            shamt = target_field.lsb % target.accesswidth
            mask = (1 << target_field.width) - 1
            return (value >> shamt) & mask

        if field_name is None:
            return await read_register(target)
        else:
            return await read_field(target, field_name)

    # --------------------------------------------------------------------------------
    # UVM Register operations
    # --------------------------------------------------------------------------------

    def set(self, reg_name: str, value: int) -> None:
        """Set a the desired value of a register.

        This method will split the passed in value over the bits of the field
        i.e. if you pass in 0xE5 == 0b11101010 and the register has the format
        reg my_reg {
            field {} data0 [1:0]
            field {} data1 [7:4]
        }
        then we'd have data0 = 2b10, data1 = 4b1110

        Args:
          reg_name(str): The target register's name
          value(int): The value to write to the register

        """
        self._log.debug(f"Setting reg ({reg_name}) with value {value}")

        target = self.get_register_by_name(reg_name)

        # Extract the bits we are going to write and conver them to int
        masked_values = [
            value for _, value in self.split_value_over_fields(target, value)
        ]

        # Write the values to the respective fields
        for idx, field in enumerate(target):
            self._desired_values[reg_name][field.inst_name].value = masked_values[idx]

    def set_field(self, reg_name: str, field_name: str, value: int) -> None:
        """Set the desired value of a field.

        Args:
          reg_name(str): The target register's name
          field_name(str): The name of the field to update
          value(int): the value to write to the field

        """
        self._log.debug(f"Setting field ({reg_name}.{field_name}) with value {value}")

        try:
            self._desired_values[reg_name][field_name].value = value
        except KeyError as e:
            raise Exception(
                f"The specified field ({reg_name}.{field_name}) does not exist!"
                f" ({self._desired_values.keys()})",
            ) from e

    def get(self, reg_name: str) -> int:
        """Get the desired value of a register.

        Args:
          reg_name(str): The target register's name
          reg_name: str:

        Returns:
          int: the register's value

        """
        self._log.debug(f"Getting reg ({reg_name}) value")

        target = self.get_register_by_name(reg_name)

        value = 0
        for field in target:
            # shift in the value at the offset given by the actual field
            part = self._desired_values[reg_name][field.inst_name].value << field.lsb
            value = value | part

        return value

    def get_field(self, reg_name: str, field_name: str) -> int:
        """Get the desired value of a field.

        Args:
          reg_name(str): The target register's name
          field_name(str): The name of the field to update
          reg_name: str:
          field_name: str:

        Returns:
          int: The field's value

        """
        self._log.debug(f"Getting field ({reg_name}.{field_name}) value")

        try:
            return self._desired_values[reg_name][field_name].value
        except KeyError as e:
            raise KeyError(
                f"The specified field ({reg_name}.{field_name}) does not exist!"
                f" ({self._desired_values.keys()})",
            ) from e

    def randomize(self, reg_name: str) -> None:
        """Randomizes the value of a register.

        Args:
          reg_name(str): The name of the register to randomise
          reg_name: str:

        """
        target = self.get_register_by_name(reg_name)

        self.set(reg_name, np.random.randint(0, 1 << target.regwidth))

    def randomize_field(self, reg_name: str, field_name: str) -> None:
        """Randomizes the value of a field in a register.

        Args:
          reg_name(str): The name of the parent register
          field_name(str): The name of the field to randomize
          reg_name: str:
          field_name: str:

        """
        target_field = self.get_field_by_name(reg_name, field_name)

        self.set_field(
            reg_name,
            field_name,
            np.random.randint(0, 1 << target_field.field.width),
        )

    def reset(self, reg_name: str) -> None:
        """Reset the desired value of a register.

        Args:
          reg_name(str): The register you wish to reset
          reg_name: str:

        """
        target = self.get_register_by_name(reg_name)

        # write each reset value to each field
        for field in target:
            self._desired_values[reg_name][field.inst_name].value = field.reset or 0

    def reset_field(self, reg_name: str, field_name: str) -> None:
        """Reset the desired value of a field within a register.

        Args:
          reg_name(str): The register you wish to target
          field_name(str): The field you wish to reset
          reg_name: str:
          field_name: str:

        """
        target = self._desired_values[reg_name][field_name]

        # set the reset value
        target.value = target.field.reset or 0
