"""Support for peakrdl-sv as an exporter within peakrdl."""

from __future__ import annotations

import argparse

from peakrdl.plugins.exporter import ExporterSubcommandPlugin
from systemrdl.node import AddrmapNode

from .exporter import PythonExporterBase, VerilogExporterBase


class VerilogExporter(ExporterSubcommandPlugin):
    """peakrdl-sv verilog exporter peakrdl entrypoint support."""

    short_desc = "A SystemVerilog SystemRDL exporter"

    def add_exporter_arguments(self, arg_group: argparse.ArgumentParser) -> None:
        """Peakrdl-sv custom arguments.

        Args:
          arg_group (argparse.ArgumentParser): The parser to append arguments to

        """
        arg_group.add_argument(
            "--reset-polarity",
            default="high",
            type=str,
            choices=["high", "low"],
            help="Set the reset polarity",
        )

        arg_group.add_argument(
            "--reset-type",
            default="sync",
            type=str,
            choices=["async", "sync"],
            help="set the reset type",
        )

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        """Export a SV output from an Address Map root node."""
        exporter = VerilogExporterBase()
        exporter.export(top_node, options)


class PythonExporter(ExporterSubcommandPlugin):
    """peakrdl-sv python exporter peakrdl entrypoint support."""

    short_desc = "A Python register map SystemRDL exporter"

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        """Export a Python output from an Address Map root node."""
        exporter = PythonExporterBase()
        exporter.export(top_node, options)
