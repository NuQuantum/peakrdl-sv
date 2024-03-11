#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import UserList
from pathlib import Path
from typing import Optional, Union, Any, List
from systemrdl.node import AddrmapNode, RootNode
from mako.template import Template
from pkg_resources import resource_filename
from peakrdl_sv.node import AddressMap, RegisterFile, Register
from peakrdl_sv.listener import Listener

class VerilogExporter:
    def __init__(self):
        self.listener = Listener()

    def walk(self, node: RootNode | AddrmapNode) -> None:
        if isinstance(node, RootNode):
            node = node.top

        self.listener.walk(node, unroll=True)

    def export(
        self,
        node: RootNode | AddrmapNode | None,
        options: argparse.Namespace,
    ) -> None:
        if node:
            self.walk(node)
        elif not self.top:
            raise RuntimeError

        outpath = Path(options.output)
        if not outpath.exists():
            outpath.mkdir(parents=True, exist_ok=True)

        reg_pkg_path = outpath / f"{node.inst_name}_reg_pkg.sv"
        reg_top_path = outpath / f"{node.inst_name}_reg_top.sv"

        reg_top_tpl = Template(filename=resource_filename("peakrdl_sv", "reg_top.sv.tpl"))
        with reg_top_path.open('w') as f:
            f.write(reg_top_tpl.render(block=self.listener.top_node))
        
        reg_pkg_tpl = Template(filename=resource_filename("peakrdl_sv", "reg_pkg.sv.tpl"))
        with reg_pkg_path.open('w') as f:
            f.write(reg_pkg_tpl.render(block=self.listener.top_node))
