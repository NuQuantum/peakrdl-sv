from peakrdl_sv.node import AddressMap, RegisterFile, Register, Field
from peakrdl_sv.listener import Listener
from systemrdl import RDLCompiler
from systemrdl.node import RootNode, AddrmapNode
from typing import List, Callable

class RegModel:
    def __init__(self, rdlfile: str, callbacks: List[Callable]):
        self.callbacks = callbacks
        self.top_node: AddressMap = self._parse_rdl(rdlfile)
        
    def _parse_rdl(self, rdlfile: str) -> AddressMap:
        rdlc = RDLCompiler()
        rdlc.compile_file(rdlfile)
        root = rdlc.elaborate()
        listener = Listener()
        listener.walk(root, unroll=True)
        return listener.top_node
        
    def get_register_by_name(self, name: str) -> Register:
        for register in self.top_node.get_registers():
            if register.name == name:
                return register
        return None