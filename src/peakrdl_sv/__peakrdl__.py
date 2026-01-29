from __future__ import annotations

import argparse

from peakrdl.plugins.exporter import ExporterSubcommandPlugin
from systemrdl.node import AddrmapNode

from .exporter import PythonExporterBase
from .exporter import VerilogExporterBase


class VerilogExporter(ExporterSubcommandPlugin):
    short_desc = "A SystemVerilog SystemRDL exporter"

    def add_exporter_arguments(self, arg_group: argparse.ArgumentParser) -> None:
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

        arg_group.add_argument(
            "--cpuif",
            default="csr",
            type=str,
            help="Set the CPU interface type: csr, axi-lite",
        )

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        exporter = VerilogExporterBase()
        exporter.export(top_node, options)


class PythonExporter(ExporterSubcommandPlugin):
    short_desc = "A Python register map SystemRDL exporter"

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        exporter = PythonExporterBase()
        exporter.export(top_node, options)
