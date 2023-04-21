import argparse
from pathlib import Path
import sys

from kmdouglass.udesigner import dpm


def parse_cli_args(cli_args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generates design documents for different types of microscopes"
    )

    parser.add_argument(
        "-o",
        "--output_file",
        type=Path,
        default=Path("output.html"),
        help="The output file to write the design document to",
    )

    return parser.parse_args(cli_args)

def main():
    args = parse_cli_args(sys.argv[1:])
    dpm.main(args.output_file)
