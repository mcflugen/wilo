from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from wilo._errors import WiloValidationError
from wilo._json import load_json


@dataclass(frozen=True)
class PoolConfig:
    players: tuple[str, ...]
    points: dict[int, float]
    season: int

    def __post_init__(self):
        invalid_players = {player for player in self.players if not player}
        if invalid_players:
            raise WiloValidationError(
                f"{', '.join(sorted(invalid_players))}: player name must not be empty"
            )
        if len(self.players) != len(set(self.players)):
            raise WiloValidationError("player names must be unique")

        for week, points in self.points.items():
            if week < 1 or week > 17:
                raise WiloValidationError(f"{week}: week must be between 1 and 17")
            if points <= 0.0 or not math.isfinite(points) or math.isnan(points):
                raise WiloValidationError(f"{points}: points must finite and >= 0")

        if len(self.points) != 17:
            raise WiloValidationError(
                f"{len(self.points)}: points must be specified for each week"
            )

    @classmethod
    def from_file(cls, path: str) -> PoolConfig:
        config = load_json(path)

        players = tuple(config["players"])
        points = {int(week): points for week, points in config["points"].items()}
        season = config["season"]
        return cls(players=players, points=points, season=season)

    def as_dict(self) -> dict[str, Any]:
        return {
            "players": sorted(self.players),
            "points": dict(sorted(self.points.items())),
            "season": self.season,
        }
