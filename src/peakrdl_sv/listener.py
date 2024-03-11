from systemrdl import RDLWalker, RDLListener
from systemrdl.node import RootNode, AddrmapNode, RegfileNode, RegNode, FieldNode
from peakrdl_sv.node import AddressMap, RegisterFile, Register, Field
from typing import Union

class Listener(RDLListener):
    def __init__(self):
        self._active_node = [] # REVISIT: better name
        self.top_node = None

    @property
    def _current_node(self):
        return self._active_node[-1]
    
    def push(self, node: Union[AddressMap, RegisterFile, Register]):
        try:
            self._current_node.append(node)
        except IndexError:
            pass
        self._active_node.append(node)

    def pop(self) -> None:
        self.top_node = self._active_node.pop()

    def enter_Addrmap(self, node) -> None:
        self.push(AddressMap(node))

    def exit_Addrmap(self, node) -> None:
        self.pop()

    def enter_Regfile(self, node: RegfileNode) -> None:
        self.push(RegisterFile(node))

    def exit_Regfile(self, node: RegfileNode) -> None:
        self.pop()

    def enter_Reg(self, node: RegNode) -> None:
        self.push(Register(node))

    def exit_Reg(self, node: RegNode) -> None:
        self.pop()

    def enter_Field(self, node: FieldNode) -> None:
        self.push(Field(node))

    def exit_Field(self, node: FieldNode) -> None:
        self.pop()        
        
    def walk(self, node: Union[RootNode, AddrmapNode], unroll: bool=True):
        RDLWalker(unroll=True).walk(node, self)
