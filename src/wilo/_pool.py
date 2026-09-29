from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict

from wilo._json import load_json
from wilo._json import pretty_json
from wilo._picks import Pick
from wilo._player import PlayerPicks


def empty_pool(names: Iterable[str]) -> dict[str, PlayerPicks]:
    return {name: PlayerPicks() for name in names}


def load_pool(path: str) -> dict[str, PlayerPicks]:
    _pool = load_json(path)

    pool: dict[str, dict[int, Pick]] = defaultdict(dict)
    for week, player_picks in _pool.items():
        for player, pick in player_picks.items():
            pool[player][int(week)] = Pick(winner=pick["winner"], loser=pick["loser"])

    return {player: PlayerPicks(pool[player]) for player in pool}


def save_pool(pool: dict[str, PlayerPicks], player: Iterable[str] | None = None) -> str:
    players = list(pool) if player is None else player

    _pool: dict[int, dict[str, dict[str, str | None]]] = defaultdict(dict)
    for player in sorted(players):
        for week in range(1, 18):
            _pool[week][player] = asdict(pool[player].for_week(week))

    return pretty_json(_pool)
