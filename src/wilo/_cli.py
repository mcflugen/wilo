from __future__ import annotations

import argparse
import os
import tomllib
from collections.abc import Iterable
from typing import TypedDict

from wilo._commands import cmd_init
from wilo._commands import cmd_optimize
from wilo._commands import cmd_picks
from wilo._commands import cmd_predict
from wilo._commands import cmd_ratings
from wilo._commands import cmd_season
from wilo._commands import cmd_standings
from wilo._errors import WiloError
from wilo._errors import WiloIOError
from wilo._errors import WiloValidationError
from wilo._output import print_error
from wilo._version import __version__

ConfigDefaults = TypedDict(
    "ConfigDefaults",
    {
        "players": Iterable[str] | None,
        "points": dict[int, float],
        "season": int | None,
        "data-dir": str,
    },
)


CONFIG: ConfigDefaults = {
    "players": None,
    "points": dict(enumerate([1.0] * 17, start=1)),
    "season": None,
    "data-dir": ".",
}


def build_pre_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wilo", allow_abbrev=False, add_help=False)
    parser.add_argument("--config", default="wilo.toml")
    parser.add_argument("--season")

    return parser


def build_parser(config: ConfigDefaults) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wilo", allow_abbrev=False)
    parser.add_argument("--version", action="version", version=f"wilo {__version__}")
    parser.add_argument(
        "--data",
        metavar="PATH",
        default=config["data-dir"],
        help="path to data files",
    )
    parser.add_argument("--config")
    parser.add_argument("--season", default=config["season"], type=int)

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument(
        "--player",
        action="append",
        required=config["players"] is None,
        default=config["players"],
    )
    init_parser.set_defaults(points=config["points"])
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


def load_config(path: str, season: str | None) -> ConfigDefaults:
    if not os.path.isfile(path):
        return CONFIG.copy()

    try:
        with open(path, "rb") as stream:
            config = tomllib.load(stream)
    except OSError as error:
        raise WiloIOError(str(error)) from error
    except tomllib.TOMLDecodeError as error:
        raise WiloValidationError(str(error)) from error

    season = config.get("default-season") if season is None else season
    seasons = config.get("seasons", {})

    if season is None and len(seasons) == 1:
        season = next(iter(seasons))
    if season is None:
        raise WiloValidationError("missing default-season")
    if season not in seasons:
        raise WiloValidationError(f"{season}: missing season")

    config = {
        **CONFIG,
        **config.get("pool", {}),
        **seasons[season],
    }
    if isinstance(config["points"], list):
        config["points"] = dict(enumerate(config["points"], 1))

    return {
        "players": config["players"],
        "points": config["points"],
        "season": int(season),
        "data-dir": config["data-dir"],
    }


def main(argv: list[str] | None = None) -> int:
    pre_parser = build_pre_parser()
    args, _ = pre_parser.parse_known_args(argv)

    try:
        config = load_config(args.config, season=args.season)
    except WiloError as error:
        config = CONFIG
        config_error: WiloError | None = error
    else:
        config_error = None

    parser = build_parser(config)
    args = parser.parse_args(argv)

    if config_error:
        print_error(f"{parser.prog}: {config_error}")
        return 1

    if args.command == "init" and args.season is None:
        parser.error("init requires --season or a configured default season")

    if hasattr(args, "func"):
        try:
            return args.func(args)
        except WiloError as error:
            print_error(f"{parser.prog}: {error}")
            return 1

    parser.print_help()

    return 0
