import argparse
from pathlib import Path
import sys

from kmdouglass.udesigner import dpm


def parse_cli_args(cli_args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generates design documents for diffraction phase microscopes"
    )
    subparsers = parser.add_subparsers(dest="subparser_name")

    doc_parser = subparsers.add_parser("doc", help="Generate a design document")
    doc_parser.add_argument(
        "-i",
        "--input_file",
        type=Path,
        default=Path("inputs.json"),
        help="The JSON file containing the design inputs",
    )
    doc_parser.add_argument(
        "-o",
        "--output_file",
        type=Path,
        default=Path("output.html"),
        help="The output file to write the design document to",
    )
    doc_parser.set_defaults(func=dpm.main)
    
    input_parser = subparsers.add_parser("inputs", help="Generate an input file for the design document")
    input_parser.add_argument(
        "-o",
        "--output_file",
        type=Path,
        default=Path("inputs.json"),
        help="The output file to write the design inputs to",
    )
    input_parser.set_defaults(func=dpm.defaults_to_json)

    return parser.parse_args(cli_args)


def main():
    args = parse_cli_args(sys.argv[1:])

    if args.subparser_name == "inputs":
        args.func(output_file=args.output_file)
    elif args.subparser_name == "doc":
        args.func(args.input_file, output_file=args.output_file)
    else:
        raise ValueError(f"Unknown subcommand: {args.subparser_name}")
