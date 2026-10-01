from __future__ import annotations

import argparse

from wilo._commands import cmd_init
from wilo._commands import cmd_optimize
from wilo._commands import cmd_picks
from wilo._commands import cmd_predict
from wilo._commands import cmd_ratings
from wilo._commands import cmd_season
from wilo._commands import cmd_standings
from wilo._errors import WiloError
from wilo._output import print_error
from wilo._version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wilo", allow_abbrev=False)
    parser.add_argument("--version", action="version", version=f"wilo {__version__}")
    parser.add_argument(
        "--data",
        metavar="PATH",
        default=".",
        help="path to data files",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--season", type=int, required=True)
    init_parser.add_argument("--player", action="append", required=True)
    init_parser.set_defaults(func=cmd_init)

    pool_parser = subparsers.add_parser("picks")
    pool_parser.set_defaults(func=cmd_picks)
    pool_parser.add_argument("--table", action="store_true")

    pool_parser.add_argument("--player", action="append", default=None)
    pool_parser.add_argument("--week", action="append", type=int, default=None)

    season_parser = subparsers.add_parser("season")
    season_parser.set_defaults(func=cmd_season)

    season_output_parser = season_parser.add_mutually_exclusive_group(required=False)
    season_output_parser.add_argument("--table", action="store_true")
    season_output_parser.add_argument("--update", action="store_true")

    season_source_parser = season_parser.add_mutually_exclusive_group(required=False)
    season_source_parser.add_argument("--download", action="store_true")
    season_source_parser.add_argument("path", nargs="?", metavar="SOURCE")

    ratings_parser = subparsers.add_parser("ratings")
    ratings_parser.set_defaults(func=cmd_ratings)

    ratings_output_parser = ratings_parser.add_mutually_exclusive_group(required=False)
    ratings_output_parser.add_argument("--table", action="store_true")
    ratings_output_parser.add_argument("--update", action="store_true")

    ratings_source_parser = ratings_parser.add_mutually_exclusive_group(required=False)
    ratings_source_parser.add_argument("--download", action="store_true")
    ratings_source_parser.add_argument("path", nargs="?", metavar="SOURCE")

    optimize_parser = subparsers.add_parser("optimize")
    optimize_parser.add_argument("--table", action="store_true")
    optimize_parser.add_argument("--player", required=True)
    optimize_parser.set_defaults(func=cmd_optimize)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.set_defaults(func=cmd_predict)

    standings_parser = subparsers.add_parser("standings")
    standings_parser.add_argument("--table", action="store_true")
    standings_parser.set_defaults(func=cmd_standings)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        try:
            return args.func(args)
        except WiloError as error:
            print_error(f"{parser.prog}: {error}")
            return 1
    else:
        parser.print_help()
    return 0
