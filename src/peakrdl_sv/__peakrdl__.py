from __future__ import annotations

import argparse

from peakrdl.plugins.exporter import ExporterSubcommandPlugin
from systemrdl.node import AddrmapNode

from .exporter import VerilogExporter


def validate_reset_polarity(string):
    if string not in ("high", "low"):
        raise argparse.ArgumentError
    return string


def validate_reset_type(string):
    if string not in ("async", "sync"):
        raise argparse.ArgumentError
    return string


class Exporter(ExporterSubcommandPlugin):
    short_desc = "A SystemVerilog SystemRDL exporter"

    def add_exporter_arguments(self, arg_group: argparse.ArgumentParser) -> None:
        arg_group.add_argument(
            "--reset-polarity",
            default="high",
            type=validate_reset_polarity,
            help="Set the reset polarity",
        )

        arg_group.add_argument(
            "--reset-type",
            default="sync",
            type=validate_reset_type,
            help="set the reset type",
        )

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        exporter = VerilogExporter()
        exporter.export(top_node, options)
