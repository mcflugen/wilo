from __future__ import annotations

import argparse
import os
from collections.abc import Collection
from collections.abc import Iterable
from dataclasses import asdict

from wilo._config import PoolConfig
from wilo._errors import WiloError
from wilo._json import pretty_json
from wilo._output import format_table
from wilo._output import print_error
from wilo._output import update_path
from wilo._picks import Pick
from wilo._player import first_empty_week
from wilo._pool import empty_pool
from wilo._pool import load_pool
from wilo._pool import save_pool
from wilo._predict import predict_games
from wilo._ratings import Ratings
from wilo._season import Season
from wilo._standings import calculate_standings

CONFIG_FILENAME = "config.json"
GAMES_FILENAME = "games.json"
RATINGS_FILENAME = "ratings.json"
PICKS_FILENAME = "picks.json"


def cmd_init(args: argparse.Namespace) -> int:
    data_dir = os.path.abspath(args.data)
    config_file = os.path.join(data_dir, CONFIG_FILENAME)
    picks_file = os.path.join(data_dir, PICKS_FILENAME)

    config = PoolConfig(
        players=args.player,
        points=args.points,
        season=args.season,
    )
    pool = empty_pool(config.players)

    for fname in (config_file, picks_file):
        if os.path.isfile(fname):
            raise WiloError(f"{fname}: file exists")

    os.makedirs(data_dir, exist_ok=True)
    with open(config_file, "w") as stream:
        print(pretty_json(config.as_dict()), file=stream)
    with open(picks_file, "w") as stream:
        print(save_pool(pool), file=stream)

    return 0


def cmd_season(args: argparse.Namespace) -> int:
    config = PoolConfig.from_file(os.path.join(args.data, CONFIG_FILENAME))

    if args.download:
        season = Season.download(season=config.season)

    if args.path:
        season = Season.import_file(args.path, season=config.season)

    if not args.download and not args.path:
        season = Season.from_file(os.path.join(args.data, GAMES_FILENAME))

    if args.table:
        out = season.tabulate()
    else:
        out = pretty_json(season.as_dict(), inline_depth=3)

    if args.update:
        update_path(os.path.join(args.data, GAMES_FILENAME), out, backup=".bak")
        return 0

    print(out)
    return 0


def cmd_ratings(args: argparse.Namespace) -> int:
    if args.download:
        ratings = Ratings.download()

    if args.path:
        ratings = Ratings.import_file(args.path, source="elway")

    if not args.download and not args.path:
        ratings = Ratings.from_file(os.path.join(args.data, RATINGS_FILENAME))

    if args.table:
        out = format_table(ratings.items(), headers=["Team", "ELO"])
    else:
        out = pretty_json(dict(ratings))

    if args.update:
        update_path(os.path.join(args.data, RATINGS_FILENAME), out, backup=".bak")
        return 0

    print(out)
    return 0


def cmd_picks(args: argparse.Namespace) -> int:
    config = PoolConfig.from_file(os.path.join(args.data, CONFIG_FILENAME))

    pool = load_pool(os.path.join(args.data, PICKS_FILENAME))

    players = set(pool if args.player is None else args.player)
    validate_player(players, allowed=config.players)

    weeks = set(config.points if args.week is None else args.week)
    validate_week(weeks, allowed=config.points)

    filtered = {}
    for player in players:
        filtered[player] = {week: pool[player].for_week(week) for week in weeks}

    if args.table:
        out = (
            format_picks_by_player(filtered)
            if args.player
            else format_picks_by_week(filtered)
        )
    else:
        out = pretty_json(
            {
                week: {
                    player: asdict(filtered[player][week])
                    for player in sorted(filtered)
                }
                for week in sorted(weeks)
            }
        )

    print(out)
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    schedule = Season.from_file(os.path.join(args.data, GAMES_FILENAME))
    ratings = Ratings.from_file(os.path.join(args.data, RATINGS_FILENAME))

    predictions = predict_games(schedule, ratings)

    print(pretty_json(predictions))

    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    try:
        from wilo._optimize import plan_picks
    except ImportError as error:
        raise WiloError("Optimization requires installing 'wilo[optimize]'.") from error

    schedule = Season.from_file(os.path.join(args.data, GAMES_FILENAME))
    ratings = Ratings.from_file(os.path.join(args.data, RATINGS_FILENAME))
    config = PoolConfig.from_file(os.path.join(args.data, CONFIG_FILENAME))
    pool = load_pool(os.path.join(args.data, PICKS_FILENAME))

    validate_player(args.player, allowed=set(pool))

    available_selections = pool[args.player].available
    start_week = first_empty_week(pool[args.player])
    if start_week < 0:
        print_error("no more weeks left to pick")
        return 0

    weeks = range(start_week, 18)

    points = {week: config.points[week] for week in weeks}

    picks = plan_picks(
        schedule.for_weeks(weeks),
        ratings,
        points=points,
        available=available_selections,
    )

    if args.table:
        out = format_picks_by_player(
            {args.player: {week: picks.for_week(week) for week in weeks}}
        )
    else:
        out = pretty_json(
            {
                week: {
                    "winner": picks.for_week(week).winner,
                    "loser": picks.for_week(week).loser,
                }
                for week in weeks
            },
            inline_depth=1,
        )

    print(out)

    return 0


def cmd_standings(args: argparse.Namespace) -> int:
    config = PoolConfig.from_file(os.path.join(args.data, CONFIG_FILENAME))
    season = Season.from_file(os.path.join(args.data, GAMES_FILENAME))
    pool = load_pool(os.path.join(args.data, PICKS_FILENAME))

    standings = calculate_standings(season, pool, config)

    if args.table:
        rows = sorted(standings.items(), key=lambda item: item[1], reverse=True)
        out = format_table(rows, headers=["Name", "Points"])
    else:
        out = pretty_json(standings)

    print(out)

    return 0


def validate_player(
    player: str | Collection[str],
    *,
    allowed: Collection[str] | None = None,
) -> None:
    allowed = set() if allowed is None else allowed

    if isinstance(player, str):
        player = [player]

    unknown_players = set(player) - set(allowed)
    if unknown_players:
        raise WiloError(f"{', '.join(sorted(unknown_players))}: unknown player")


def validate_week(
    week: int | Collection[int],
    *,
    allowed: Collection[int] | None = None,
) -> None:
    allowed = set() if allowed is None else allowed

    if isinstance(week, int):
        week = [week]

    unknown_weeks = set(week) - set(allowed)
    if unknown_weeks:
        raise WiloError(
            f"{', '.join(str(week) for week in sorted(unknown_weeks))}: unknown week"
        )


def format_picks_table(
    rows: Iterable[tuple[str | int, Pick]],
    *,
    label: str,
) -> str:
    table = [(key, pick.winner, pick.loser) for key, pick in rows]
    return format_table(table, headers=[label, "Winner", "Loser"])


def format_picks_by_player(
    pool: dict[str, dict[int, Pick]],
) -> str:
    tables = []
    for player in sorted(pool):
        table = format_picks_table(sorted(pool[player].items()), label="Week")
        tables.append(f"Player: {player}\n{table}")
    return "\n\n".join(tables)


def format_picks_by_week(
    pool: dict[str, dict[int, Pick]],
) -> str:
    weeks = next(iter(pool.values()), {})

    tables = []
    for week in sorted(weeks):
        table = format_picks_table(
            [(player, picks[week]) for player, picks in sorted(pool.items())],
            label="Player",
        )
        tables.append(f"Week: {week}\n{table}")
    return "\n\n".join(tables)
