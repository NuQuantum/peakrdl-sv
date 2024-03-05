#!/usr/bin/env python3

import argparse
from collections import UserList

from pathlib import Path
from typing import Optional, Union, Any, List
from systemrdl.node import AddrmapNode, RegfileNode, RegNode, FieldNode, RootNode
from systemrdl import RDLWalker, RDLListener
from mako.template import Template
from pkg_resources import resource_filename

class Node(UserList):
    def __init__(self, node: Union[AddrmapNode, RegfileNode, RegNode, FieldNode]) -> None:
        self.node = node
        super().__init__()

    def __getattr__(self, item):
        return getattr(self.node, item)
    
    @property
    def name(self):
        return self.inst_name
    
    @property
    def path(self):
        return self.get_rel_path(self.owning_addrmap, hier_separator="_", array_suffix="_{index:d}")
    
    
class Field(Node):
    @property
    def onread(self):
        return self.get_property('onread')
    
    @property
    def onwrite(self):
        return self.get_property('onwrite')
    
    @property
    def reset(self):
        return self.get_property('reset')
    
    @property
    def swmod(self):
        return self.get_property('swmod')
    
    @property
    def swacc(self):
        return self.get_property('swacc')
    
    @property
    def bits(self):
        if self.msb == self.lsb:
            return str(self.msb)
        else:
            return f"{str(self.msb)}:{str(self.lsb)}"
        

class Register(Node):
    pass


class RegisterFile(Node):
    pass


class AddressMap(Node):
    def get_registers(self) -> List[Register]:
        def get_child_regs(child, regs):
            if isinstance(child, (AddressMap, Field)):
                raise RuntimeError(f"unexpected call to get_child_regs on object {child}")
            elif isinstance(child, RegisterFile):
                for ch in child:
                    get_child_regs(ch, regs)
            elif isinstance(child, Register):
                regs.append(child)
            else:
                raise RuntimeError(f"unrecognised type: {type(child)}")
        
        registers = []
        for i,child in enumerate(self):
            get_child_regs(child, registers)
        return registers
    
    @property
    def addrwidth(self) -> int:
        return self.size.bit_length()
    
    @property
    def accesswidth(self) -> int:
        return min([reg.get_property('accesswidth') for reg in self.get_registers()])


class VerilogExporter(RDLListener):
    def __init__(self):
        self._active_node = [] # REVISIT: better name
        self.top = None

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
        self.top = self._active_node.pop()

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

    def export(self, node: Union[RootNode, AddrmapNode], options: argparse.Namespace) -> None:
        if isinstance(node, RootNode):
            node = node.top

        RDLWalker(unroll=True).walk(node, self)

        outpath = Path(options.output)
        if not outpath.exists():
            outpath.mkdir(parents=True, exist_ok=True)

        reg_pkg_path = outpath / f"{node.inst_name}_reg_pkg.sv"
        reg_top_path = outpath / f"{node.inst_name}_reg_top.sv"

        reg_top_tpl = Template(filename=resource_filename("peakrdl_sv", "reg_top.sv.tpl"))
        with reg_top_path.open('w') as f:
            f.write(reg_top_tpl.render(block=self.top))
        
        reg_pkg_tpl = Template(filename=resource_filename("peakrdl_sv", "reg_pkg.sv.tpl"))
        with reg_pkg_path.open('w') as f:
            f.write(reg_pkg_tpl.render(block=self.top))
