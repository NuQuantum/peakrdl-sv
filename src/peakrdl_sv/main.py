"""CLI application for peakrdl-sv."""

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from importlib.resources import files
from pathlib import Path

from systemrdl import RDLCompiler

from peakrdl_sv.exporter import VerilogExporterBase

logger = logging.getLogger(__name__)


def create_output_directory(output: str) -> Path:
    """Create a directory at the specified location.

    Args:
      output (str): The output directory name

    Returns:
        Path: The path to the created directory

    """
    try:
        outpath = Path(output)
        outpath.mkdir(parents=True, exist_ok=True)
        return outpath.absolute()
    except TypeError:
        return Path().absolute()


def export(args: argparse.Namespace) -> None:
    """Run the peakrdl-sv tool on an input file, and dumps the output to a file.

    Args:
      args: Namespace containing "output" and "filename"

    """
    outpath = create_output_directory(args.output)
    logging.debug("running peakrdl-sv; output dumped to " + str(outpath))

    rdlc = RDLCompiler()
    rdlc.compile_file(args.filename)

    root = rdlc.elaborate()
    exporter = VerilogExporterBase()
    exporter.export(root, args)

    if args.include_subreg:
        install(args)


def install(args: argparse.Namespace) -> None:
    """Install the peakrdl-sv output verillog to a particular directory.

    Args:
      args: Namespace containing "output"

    """
    outpath = create_output_directory(args.output)
    logging.debug("installing SV to " + str(outpath))
    for src in [
        item
        for item in files("peakrdl_sv").joinpath("data").iterdir()
        if item.is_file() and item.name.endswith(".sv")
    ]:
        dst = outpath / src.name
        logger.debug(f"copying {src} to {dst}")
        shutil.copy2(str(src), dst.name)


def get_parser() -> argparse.ArgumentParser:
    """Generate the CLI parser."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # Global args
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Specify the output path",
    )

    # Export subparser
    parser_export = subparsers.add_parser(
        "export",
        help="Run the SystemVerlog RDL exporter",
    )
    parser_export.set_defaults(func=export)
    parser_export.add_argument(
        "filename",
        metavar="FILE",
        help="The SystemRDL file to process",
    )
    parser_export.add_argument(
        "--include-subreg",
        action="store_true",
        help="Include the RTL dependencies",
    )
    parser_export.add_argument(
        "--include-core",
        action="store_true",
        help="Include a FuseSoC core file",
    )

    # Install subparser
    parser_install = subparsers.add_parser(
        "install",
        help="Install SV source files into local tree",
    )
    parser_install.set_defaults(func=install)

    return parser


def parse_args() -> argparse.Namespace | None:
    """Parse the CLI args."""
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        return args

    if hasattr(args, "subparser"):
        args.subparser.print_help()
    else:
        parser.print_help()

    return None


def main() -> None:
    """Execte the peakrdl-sv exported application."""
    args = parse_args()
    if args is None:
        sys.exit(0)

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s : %(message)s")

    args.func(args)


if __name__ == "__main__":
    main()
