#!/usr/bin/env python3
"""Exporter classes for PeakRDL-sv."""

from __future__ import annotations

import argparse
from pathlib import Path

from mako.template import Template
from pkg_resources import resource_filename
from systemrdl.node import AddrmapNode, RootNode

from peakrdl_sv.listener import Listener


class VerilogExporterBase:
    """A SystemRDL to Verilog exporter."""

    def __init__(self) -> None:
        """Initialise the exporter with a listener."""
        self.listener = Listener()

    def walk(self, node: RootNode | AddrmapNode) -> None:
        """Walk an addr map from a root node.

        Args:
          node: RootNode | AddrmapNode: The root node of the map, or the map itself

        """
        if isinstance(node, RootNode):
            node = node.top

        self.listener.walk(node, unroll=True)

    def export(
        self,
        node: RootNode | AddrmapNode | None,
        options: argparse.Namespace,
    ) -> None:
        """Export a register map to (System)Verilog.

        Args:
          node: RootNode | AddrmapNode | None: The root node of the PeakRDL reg map
          options: argparse.Namespace: the output path

        """
        if node:
            self.walk(node)
        elif not self.top:
            raise RuntimeError

        outpath = Path(options.output)
        if not outpath.exists():
            outpath.mkdir(parents=True, exist_ok=True)

        reg_pkg_path = outpath / f"{node.inst_name.lower()}_reg_pkg.sv"
        reg_top_path = outpath / f"{node.inst_name.lower()}_reg_top.sv"

        reg_top_tpl = Template(
            filename=resource_filename("peakrdl_sv", "reg_top.sv.tpl"),
        )
        with reg_top_path.open("w") as f:
            f.write(reg_top_tpl.render(block=self.listener.top_node))

        reg_pkg_tpl = Template(
            filename=resource_filename("peakrdl_sv", "reg_pkg.sv.tpl"),
        )
        with reg_pkg_path.open("w") as f:
            f.write(reg_pkg_tpl.render(block=self.listener.top_node))


class PythonExporterBase:
    """A simple exporter for RDL -> Python."""

    def __init__(self) -> None:
        """Initialise the exporter with a listener."""
        self.listener = Listener()

    def walk(self, node: RootNode | AddrmapNode) -> None:
        """Walk an addr map from a root node.

        Args:
          node: RootNode | AddrmapNode: The root node of the map, or the map itself

        """
        if isinstance(node, RootNode):
            node = node.top

        self.listener.walk(node, unroll=True)

    def export(
        self,
        node: RootNode | AddrmapNode | None,
        options: argparse.Namespace,
    ) -> None:
        """Export a register map to Python.

        Args:
          node: RootNode | AddrmapNode | None: The root node of the PeakRDL reg map
          options: argparse.Namespace: the output path

        """
        if node is not None:
            self.walk(node)
        elif not self.top:
            raise RuntimeError

        outpath = Path(options.output)
        if not outpath.exists():
            outpath.mkdir(parents=True, exist_ok=True)

        reg_map_path = outpath / f"{node.inst_name.lower()}_reg_map.py"

        reg_map_tpl = Template(
            filename=resource_filename("peakrdl_sv", "reg_map.py.tpl"),
        )
        with reg_map_path.open("w") as f:
            f.write(reg_map_tpl.render(block=self.listener.top_node))
