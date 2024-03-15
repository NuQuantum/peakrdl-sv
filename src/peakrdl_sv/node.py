from __future__ import annotations

from collections import UserList

from systemrdl.node import AddrmapNode
from systemrdl.node import FieldNode
from systemrdl.node import RegfileNode
from systemrdl.node import RegNode


class Node(UserList):
    def __init__(
        self,
        node: AddrmapNode | RegfileNode | RegNode | FieldNode,
        parent: AddrmapNode | RegfileNode | RegNode | None,
    ) -> None:
        self.node = node
        if parent is not None:
            self.parent = parent
        super().__init__()

    def __getattr__(self, item):
        return getattr(self.node, item)

    @property
    def name(self):
        return self.inst_name

    @property
    def path(self):
        return self.get_rel_path(
            self.owning_addrmap,
            hier_separator="_",
            array_suffix="_{index:d}",
        )


class Field(Node):
    @property
    def onread(self):
        return self.get_property("onread")

    @property
    def onwrite(self):
        return self.get_property("onwrite")

    @property
    def reset(self):
        return self.get_property("reset")

    @property
    def swmod(self):
        return self.get_property("swmod")

    @property
    def swacc(self):
        return self.get_property("swacc")

    @property
    def needs_qe(self) -> bool:
        """Returns True if hardware needs to be notified of a SW write."""
        return self.is_sw_writable and (self.swacc or self.swmod)

    @property
    def needs_qre(self):
        """Returns True if hardware needs to be notified of a SW read."""
        return self.is_sw_readable and (
            self.swacc or (self.swmod and self.onread is not None)
        )

    @property
    def absolute_address(self):
        address_base = self.parent.absolute_address
        if not self.parent.is_wide:
            return address_base
        return address_base + (self.msb // 8)

    def get_bit_slice(self):
        """Returns a bit slice defining the width of the field."""
        if self.msb == self.lsb:
            return f"{self.msb}"
        else:
            return f"{self.msb}:{self.lsb}"

    def get_cpuif_bit_slice(self) -> str:
        """Returns the bit slice used by SW to access the field.

        In the simple case when (regwidth == accesswidth), this method returns the same
        string as self.get_bit_slice().  When (regwidth > accesswidth), then ...

        """
        accesswidth = self.parent.get_property("accesswidth")
        subreg_idx = self.msb // accesswidth
        msb = self.msb - (subreg_idx * accesswidth)
        lsb = self.lsb - (subreg_idx * accesswidth)
        if msb == lsb:
            return f"{msb}"
        else:
            return f"{msb}:{lsb}"

    def get_reg2hw_struct_bits(self) -> int:
        """Returns the number of bits used in the reg2hw struct.

        This is a helper method for templating.  It returns the number of bits used
        in the reg2hw struct that contains the 'q', 'qe', and 're' fields.

        """
        if not self.is_hw_readable:
            return 0
        return self.width + int(self.needs_qe) + int(self.needs_qre)

    def get_hw2reg_struct_bits(self) -> int:
        """Returns the number of bits used in the hw2reg struct.

        As above, but for the 'd', 'de' bits.

        REVISIT: at the moment we don't check whether the field sw/hw access properties
        result in a storage requirement.  This needs to be udpated.  In some cases we
        need to implement a constant or a passthrough wire.

        """
        if not self.is_hw_writable:
            return 0
        return self.width + int(not self.external)


class Register(Node):
    @property
    def accesswidth(self) -> int:
        """Returns the SW access width in bytes."""
        return self.get_property("accesswidth")

    @property
    def regwidth(self) -> int:
        """Returns the width of the register in bytes."""
        return self.get_property("regwidth")

    @property
    def is_wide(self) -> bool:
        """Returns True if the register is wider than the SW access width.

        If True, this means that software takes multiple cycles to access all fields
        within the register.

        """
        return self.regwidth > self.accesswidth

    @property
    def addressincr(self) -> int:
        """How many bytes each SW access addresses.

        This is only really useful for wide registers where you need to calculate the
        subreg offset within a register.  The RDL base classes only give you the
        absolute address of the base register so you have to manually calculate the
        offset within that register.

        """
        return self.accesswidth // 8

    @property
    def subregs(self) -> int:
        """Returns an int identifying how many sub-registers are present.

        If the regwidth is greater than the accesswidth, then the register is divided
        into a number of sub-registers that are accessed at different cpuif address.

        """
        return self.regwidth // self.accesswidth

    def get_subreg_fields(self, subreg: int):
        """Returns a list of fields that are present in a sub-register."""
        fields = []
        for f in self:
            if (f.msb // self.accesswidth) == subreg:
                fields.append(f)
        return fields


class RegisterFile(Node):
    pass


class AddressMap(Node):
    def get_registers(self) -> list[Register]:
        def get_child_regs(child, regs):
            if isinstance(child, (AddressMap, Field)):
                raise RuntimeError(
                    f"unexpected call to get_child_regs on object {child}",
                )
            elif isinstance(child, RegisterFile):
                for ch in child:
                    get_child_regs(ch, regs)
            elif isinstance(child, Register):
                regs.append(child)
            else:
                raise RuntimeError(f"unrecognised type: {type(child)}")

        registers = []
        for i, child in enumerate(self):
            get_child_regs(child, registers)
        return registers

    @property
    def addrwidth(self) -> int:
        return self.size.bit_length()

    @property
    def accesswidth(self) -> int:
        return min([reg.get_property("accesswidth") for reg in self.get_registers()])
