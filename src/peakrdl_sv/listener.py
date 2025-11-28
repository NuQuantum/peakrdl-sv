"""A custom PeakRDL-sv listener based on the systemRDL RDLListener."""

from __future__ import annotations

import contextlib
from typing import TypeAlias

from systemrdl import RDLListener, RDLWalker
from systemrdl.node import AddrmapNode, FieldNode, RegfileNode, RegNode, RootNode

from peakrdl_sv.node import AddressMap, Field, Register, RegisterFile

Node: TypeAlias = AddrmapNode | RegfileNode | RegNode | FieldNode


class Listener(RDLListener):
    """A stack based node manager."""

    def __init__(self) -> None:
        """Initialise the listener."""
        self._active_node : list[Node] = []  # REVISIT: better name
        self.top_node = None

    @property
    def _current_node(self) -> Node:
        """The head of the stack."""
        return self._active_node[-1]

    def push(self, node: Node) -> None:
        """Push a node onto the stack.

        Args:
          node: AddressMap | RegisterFile | Register:

        """
        with contextlib.suppress(IndexError):
            self._current_node.append(node)
        self._active_node.append(node)

    def pop(self) -> None:
        """Set the `top_node` member to the head of the stack."""
        self.top_node = self._active_node.pop()

    def enter_Addrmap(self, node: Node) -> None:
        """Create an address map on the stack with the provided root Node.

        Args:
          node (Node): The root node of the address map

        """
        self.push(AddressMap(node, None))

    def exit_Addrmap(self, _: None) -> None:
        """Alias for pop().

        Args:
          node(None): unused.

        """
        self.pop()

    def enter_Regfile(self, node: RegfileNode) -> None:
        """Create a RegisterFile on the stack with the provided RegFileNode.

        Args:
          node (RegfileNode): The node to create the RegisterFile from

        """
        self.push(RegisterFile(node, self._current_node))

    def exit_Regfile(self, node: RegfileNode) -> None:
        """Alias for pop().

        Args:
          node(RegFileNode): unused.

        """
        self.pop()

    def enter_Reg(self, node: RegNode) -> None:
        """Create a Register on the stack from the provided RegNode.

        Args:
          node (RegNode): The node to create the Register from.

        """
        self.push(Register(node, self._current_node))

    def exit_Reg(self, node: RegNode) -> None:
        """Alias for pop().

        Args:
          node (RegNode): unused.

        """
        self.pop()

    def enter_Field(self, node: FieldNode) -> None:
        """Create a Field on the stack from the provided RegNode.

        Args:
          node (FieldNode): The node to create the Field from.

        """
        self.push(Field(node, self._current_node))

    def exit_Field(self, node: FieldNode) -> None:
        """Alias for pop().

        Args:
          node (FieldNode): unused.

        """
        self.pop()

    def walk(self, node: RootNode | AddrmapNode, unroll: bool = True) -> None:
        """Walk the address map from a provided RootNode or AddmapNode.

        Args:
          node: RootNode | AddrmapNode: The root node to walk from
          unroll (bool): If true unroll RDLWalker (Default value = True).

        """
        if isinstance(node, RootNode):
            node = node.top
        RDLWalker(unroll=unroll).walk(node, self)
