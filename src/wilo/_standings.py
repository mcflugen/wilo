from __future__ import annotations

from collections import defaultdict

from wilo._config import PoolConfig
from wilo._errors import WiloValidationError
from wilo._player import PlayerPicks
from wilo._season import Season


def calculate_standings(
    results: Season,
    pool: dict[str, PlayerPicks],
    config: PoolConfig,
) -> dict[str, float]:
    missing_players = set(config.players) - set(pool)
    if missing_players:
        raise WiloValidationError("missing players")

    unknown_players = set(pool) - set(config.players)
    if unknown_players:
        raise WiloValidationError("unknown players")

    standings: dict[str, float] = defaultdict(float)
    for week, slate in results.games.items():
        if week >= 18:
            continue

        points = config.points[week]

        winners = slate.winners()
        losers = slate.losers()
        ties = slate.ties()
        for player in pool:
            picks = pool[player].for_week(week)

            standings[player] += points if picks.winner in winners else 0
            standings[player] += points if picks.loser in losers else 0
            standings[player] += points / 2 if picks.winner in ties else 0
            standings[player] += points / 2 if picks.loser in ties else 0

    return dict(standings)
