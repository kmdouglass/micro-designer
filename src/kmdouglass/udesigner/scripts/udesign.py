import argparse
from pathlib import Path
import sys

from kmdouglass.udesigner import dpm, mfki


CHOICES = ["dpm", "mf_koehler_integrator"]


def doc_func(design_type: str, input_file: Path, output_file: Path) -> None:
    if design_type == "dpm":
        dpm.main(input_file, output_file)
    elif design_type == "mf_koehler_integrator":
        mfki.main(input_file, output_file)
    else:
        raise ValueError(f"Unknown design type: {design_type}")
    

def inputs_func(design_type: str, output_file: Path) -> None:
    if design_type == "dpm":
        dpm.defaults_to_json(output_file)
    elif design_type == "mf_koehler_integrator":
        mfki.defaults_to_json(output_file)
    else:
        raise ValueError(f"Unknown design type: {design_type}")


def parse_cli_args(cli_args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generates design documents for microscopes and illumination systems"
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=CHOICES,
        required=True,
        help="The type of microscope or illuminator design",
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
    doc_parser.set_defaults(func=doc_func)
    
    input_parser = subparsers.add_parser("inputs", help="Generate an input file for the design document")
    input_parser.add_argument(
        "-o",
        "--output_file",
        type=Path,
        default=Path("inputs.json"),
        help="The output file to write the design inputs to",
    )
    input_parser.set_defaults(func=inputs_func)

    return parser.parse_args(cli_args)


def main():
    args = parse_cli_args(sys.argv[1:])

    if args.subparser_name == "inputs":
        args.func(args.type, output_file=args.output_file)
    elif args.subparser_name == "doc":
        args.func(args.type, args.input_file, output_file=args.output_file)
    else:
        raise ValueError(f"Unknown subcommand: {args.subparser_name}")
