from __future__ import annotations

from systemrdl import RDLListener
from systemrdl import RDLWalker
from systemrdl.node import AddrmapNode
from systemrdl.node import FieldNode
from systemrdl.node import RegfileNode
from systemrdl.node import RegNode
from systemrdl.node import RootNode

from peakrdl_sv.node import AddressMap
from peakrdl_sv.node import Field
from peakrdl_sv.node import Register
from peakrdl_sv.node import RegisterFile


class Listener(RDLListener):
    def __init__(self):
        self._active_node = []  # REVISIT: better name
        self.top_node = None

    @property
    def _current_node(self):
        return self._active_node[-1]

    def push(self, node: AddressMap | RegisterFile | Register):
        try:
            self._current_node.append(node)
        except IndexError:
            pass
        self._active_node.append(node)

    def pop(self) -> None:
        self.top_node = self._active_node.pop()

    def enter_Addrmap(self, node) -> None:
        self.push(AddressMap(node, None))

    def exit_Addrmap(self, node) -> None:
        self.pop()

    def enter_Regfile(self, node: RegfileNode) -> None:
        self.push(RegisterFile(node, self._current_node))

    def exit_Regfile(self, node: RegfileNode) -> None:
        self.pop()

    def enter_Reg(self, node: RegNode) -> None:
        self.push(Register(node, self._current_node))

    def exit_Reg(self, node: RegNode) -> None:
        self.pop()

    def enter_Field(self, node: FieldNode) -> None:
        self.push(Field(node, self._current_node))

    def exit_Field(self, node: FieldNode) -> None:
        self.pop()

    def walk(self, node: RootNode | AddrmapNode, unroll: bool = True):
        if isinstance(node, RootNode):
            node = node.top
        RDLWalker(unroll=True).walk(node, self)
