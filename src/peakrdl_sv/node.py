# mypy: disable-error-code="no-any-return"
"""Wrappers around the PeakRDL node types to support peakrdl-sv mako templates."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar, Union

from systemrdl.node import AddrmapNode, FieldNode, RegfileNode, RegNode, SignalNode
from systemrdl.rdltypes.builtin_enums import OnReadType, OnWriteType
from systemrdl.rdltypes.references import PropertyReference

TParent = TypeVar(
    "TParent", bound=Union["AddressMap", "Register", "RegisterFile", None]
)
TInner = TypeVar("TInner", AddrmapNode, FieldNode, RegfileNode, RegNode)
TChild = TypeVar(
    "TChild", bound=Union["AddressMap", "Register", "RegisterFile", "Field", None]
)


class NodeWrapper(Generic[TParent, TInner, TChild]):
    """Wraps a SystemRDL node, pairing it with its parent and child nodes.

    This class is parameterised
    """

    parent: TParent
    inner: TInner
    children: list[TChild]

    def __init__(
        self,
        node: TInner,
        parent: TParent,
    ) -> None:
        """Initialise node and parent."""
        self.inner = node
        if parent is None:
            assert isinstance(
                node,
                AddrmapNode,
            ), f"Root node must be of type AddrmapNode, not {type(node)}"
        else:
            self.parent = parent
        self.children = []
        super().__init__()

    def __iter__(self) -> Iterable[TChild]:
        """Iterate over the node's children."""
        yield from self.children

    @property
    def name(self) -> str:
        """The node's instance name."""
        return self.inner.inst_name

    @property
    def size(self) -> int:
        """The node's size in bytes."""
        match self.inner:
            case AddrmapNode() | RegfileNode() | RegNode():
                return self.inner.size
            case FieldNode():
                raise AttributeError("Cannot query the size of a field node")
            case _:
                raise TypeError("Unknown node type")

    def path(self, hier_separator: str = "_", array_suffix: str = "_{index:d}") -> str:
        """Generate a relative path string to internal node wrt to owning addr map.

        Args:
          hier_separator: str:  (Default value = "_")
          array_suffix: str:  (Default value = "_{index:d}").

        Returns:
            str: The path

        """
        owning_addrmap = self.inner.owning_addrmap
        if owning_addrmap is None:
            raise RuntimeError(
                f"Node {self} does not have an owning addrmap (this is the root node)"
            )

        return self.inner.get_rel_path(
            owning_addrmap,
            hier_separator=hier_separator,
            array_suffix=array_suffix,
        )


class Field(NodeWrapper["Register", FieldNode, None]):
    """A generic Field Node."""

    @property
    def onread(self) -> OnReadType | None:
        """Get onread propoert."""
        return self.inner.get_property("onread")

    @property
    def onwrite(self) -> OnWriteType | None:
        """Get onwite propoerty."""
        return self.inner.get_property("onwrite")

    @property
    def reset(self) -> int | FieldNode | SignalNode | PropertyReference | None:
        """Get reset propoerty."""
        return self.inner.get_property("reset")

    @property
    def swmod(self) -> bool:
        """Get swmod propoerty."""
        return self.inner.get_property("swmod")

    @property
    def swacc(self) -> bool:
        """Get swacc propoerty."""
        return self.inner.get_property("swacc")

    @property
    def needs_qe(self) -> bool:
        """Returns True if hardware needs to be notified of a SW write."""
        return self.inner.is_sw_writable and (self.swacc or self.swmod)

    @property
    def needs_qre(self) -> bool:
        """Returns True if hardware needs to be notified of a SW read."""
        return self.inner.is_sw_readable and (
            self.swacc or (self.swmod and self.onread is not None)
        )

    @property
    def present_in_reg2hw(self) -> bool:
        """Return True if the field will be present in the reg2hw struct.

        For a field that is hw = w, sw = r, there is no access of the register from HW
        and no register is implemented, just a wire. In this case there is no entry in
        the reg2hw struct for this field.
        """
        return self.needs_qe or self.needs_qre or self.inner.implements_storage

    @property
    def absolute_address(self) -> int:
        """Absolute address as base address + parent absolute address."""
        address_base = self.parent.inner.absolute_address
        if not self.parent.is_wide:
            return address_base
        return address_base + (self.inner.msb // 8)

    def get_bit_slice(self) -> str:
        """Return a bit slice defining the width of the field.

        Returns:
            str: The bitslice string

        """
        if self.inner.msb == self.inner.lsb:
            return f"{self.inner.msb}"
        else:
            return f"{self.inner.msb}:{self.inner.lsb}"

    def get_cpuif_bit_slice(self) -> str:
        """Return the bit slice used by SW to access the field.

        In the simple case when (regwidth == accesswidth), this method returns the same
        string as self.get_bit_slice().  When (regwidth > accesswidth), then ...

        Returns:
            str: The bitslice string

        """
        accesswidth = self.parent.inner.get_property("accesswidth")
        subreg_idx = self.inner.msb // accesswidth
        msb = self.inner.msb - (subreg_idx * accesswidth)
        lsb = self.inner.lsb - (subreg_idx * accesswidth)
        if msb == lsb:
            return f"{msb}"
        else:
            return f"{msb}:{lsb}"

    def get_reg2hw_struct_bits(self) -> int:
        """Return the number of bits used in the reg2hw struct.

        This is a helper method for templating.  It returns the number of bits used
        in the reg2hw struct that contains the 'q', 'qe', and 're' fields.

        Returns:
            int: The number of bits

        """
        bits = self.inner.width if self.inner.implements_storage else 0
        return bits + int(self.needs_qe) + int(self.needs_qre)

    def get_hw2reg_struct_bits(self) -> int:
        """Return the number of bits used in the hw2reg struct.

        As above, but for the 'd', 'de' bits.

        REVISIT: at the moment we don't check whether the field sw/hw access properties
        result in a storage requirement.  This needs to be udpated.  In some cases we
        need to implement a constant or a passthrough wire.

        Returns:
            int: The number of bits

        """
        if not self.inner.is_hw_writable:
            return 0
        return self.inner.width + int(not self.inner.external)


class Register(NodeWrapper[Union["AddressMap", "RegisterFile"], RegNode, Field]):
    """A generic Register node."""

    @property
    def needs_qe(self) -> bool:
        """Whether the register needs a qe signal."""
        return any(f.needs_qe for f in self.children)

    @property
    def needs_qre(self) -> bool:
        """Whether the register needs a qre signal."""
        return any(f.needs_qre for f in self.children)

    @property
    def accesswidth(self) -> int:
        """Returns the SW access width in bits."""
        return self.inner.get_property("accesswidth")

    @property
    def regwidth(self) -> int:
        """Returns the width of the register in bits."""
        return self.inner.get_property("regwidth")

    @property
    def is_wide(self) -> bool:
        """Returns True if the register is wider than the SW access width.

        If True, this means that software takes multiple cycles to access all fields
        within the register.

        Returns:
            bool: True if regwidth > accesswidth

        """
        return self.regwidth > self.accesswidth

    @property
    def present_in_reg2hw(self) -> bool:
        """Return True if the register will be present in the reg2hw struct."""
        return self.needs_qe or self.needs_qre or self.inner.has_hw_readable

    @property
    def present_in_hw2reg(self) -> bool:
        """Return True if the register will be present in the hw2reg struct."""
        return self.inner.has_hw_writable

    @property
    def addressincr(self) -> int:
        """How many bytes each SW access addresses.

        This is only really useful for wide registers where you need to calculate the
        subreg offset within a register.  The RDL base classes only give you the
        absolute address of the base register so you have to manually calculate the
        offset within that register.

        Returns:
            int: The increment size of each address

        """
        return self.accesswidth // 8

    @property
    def subregs(self) -> int:
        """Return an int identifying how many sub-registers are present.

        If the regwidth is greater than the accesswidth, then the register is divided
        into a number of sub-registers that are accessed at different cpuif address.

        Returns:
            int: The number of sub-registers present

        """
        return self.regwidth // self.accesswidth

    def get_subreg_fields(self, subreg: int) -> list[Field]:
        """Return a list of fields that are present in a sub-register.

        Args:
          subreg (int): The address of the subreg

        Returns:
            list[Field] The list of fields

        """
        return [f for f in self.children if (f.inner.msb // self.accesswidth) == subreg]


class RegisterFile(
    NodeWrapper["AddressMap", RegfileNode, Union["RegisterFile", Register]]
):
    """Represents a field within a Register."""

    pass


class AddressMap(
    NodeWrapper[None, AddrmapNode, Union["AddressMap", Register, Field, RegisterFile]]
):
    """Represents an address map."""

    @property
    def register_files(self) -> list[RegisterFile]:
        """Return a list of all the register files in an address map.

        Returns:
          list[RegisterFile]: The list of register files in the address map

        """
        return [c for c in self.children if isinstance(c, RegisterFile)]

    @property
    def registers(self) -> list[Register]:
        """A list of all registers from all levels of hierarchy in the addr map.

        Returns:
          list[Register]: The list of registers in the address map

        """

        def get_child_regs(
            child: AddressMap | Field | RegisterFile | Register, regs: list[Register]
        ) -> None:
            """Get all child registers of a RegisterFile.

            Args:
              child: The RegisterFile to inspect
              regs: the running list of registers

            Returns:
                list[Register]: The list of child registers

            """
            match child:
                case AddressMap() | Field():
                    raise RuntimeError(
                        f"unexpected call to get_child_regs on object {child}",
                    )
                case RegisterFile():
                    for c in child.children:
                        get_child_regs(c, regs)
                case Register():
                    regs.append(child)
                case _:
                    raise RuntimeError(f"unrecognised type: {type(child)}")

        registers: list[Register] = []
        for child in self.children:
            get_child_regs(child, registers)

        return registers

    @property
    def has_hw2reg(self) -> bool:
        """Returns True if any register has a hw2reg struct."""
        return any(reg.present_in_hw2reg for reg in self.registers)

    @property
    def has_reg2hw(self) -> bool:
        """Returns True if any register has a reg2hw struct."""
        return any(reg.present_in_reg2hw for reg in self.registers)

    @property
    def addrwidth(self) -> int:
        """The address map address width in bits."""
        return (self.size - 1).bit_length()

    @property
    def accesswidth(self) -> int:
        """The minimum access width it bits of registers in the map."""
        return min([reg.accesswidth for reg in self.registers])
