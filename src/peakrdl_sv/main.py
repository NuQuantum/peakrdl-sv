#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

from pkg_resources import resource_filename
from systemrdl import RDLCompiler

from peakrdl_sv.exporter import VerilogExporter


logger = logging.getLogger(__name__)


def create_output_directory(output):
    try:
        outpath = Path(output)
        outpath.mkdir(parents=True, exist_ok=True)
        return outpath.absolute()
    except TypeError:
        return Path(".").absolute()


def export(args):
    outpath = create_output_directory(args.output)
    logging.debug("running peakrdl-sv; output dumped to " + str(outpath))

    rdlc = RDLCompiler()
    rdlc.compile_file(args.filename)

    root = rdlc.elaborate()
    exporter = VerilogExporter()
    exporter.export(root, args)

    if args.include_subreg:
        install(args)


def install(args):
    outpath = create_output_directory(args.output)
    logging.debug("installing SV to " + str(outpath))
    data = Path(resource_filename("peakrdl_sv", "data"))
    for src in data.glob("*.sv"):
        dst = outpath / src.name
        logger.debug(f"copying {src} to {dst}")
        shutil.copy2(src, dst)


def get_parser():
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


def parse_args():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        return args
    if hasattr(args, "subparser"):
        args.subparser.print_help()
    else:
        parser.print_help()
        return None


def main():
    args = parse_args()
    if not args:
        exit(0)

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s : %(message)s")

    args.func(args)


if __name__ == "__main__":
    main()
