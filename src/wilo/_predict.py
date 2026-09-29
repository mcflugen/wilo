from __future__ import annotations

from collections import defaultdict

from wilo._errors import WiloValidationError
from wilo._season import Season
from wilo._teams import Team


def predict_games(
    season: Season,
    ratings,
    *,
    home_field: float = 45.0,
) -> dict[int, dict[Team, float]]:
    predictions: dict[int, dict[Team, float]] = defaultdict(dict)
    for week, _games in sorted(season.games.items()):
        for game in _games:
            win_prob = calc_win_probability(
                ratings[game.home], ratings[game.away], home_field=home_field
            )

            if win_prob > 1.0 or win_prob < 0.0:
                raise WiloValidationError(f"invalid win probability: {win_prob}")

            predictions[week][game.home] = win_prob
            predictions[week][game.away] = 1.0 - win_prob

        predictions[week] = dict(sorted(predictions[week].items()))

    return predictions


def calc_win_probability(
    rating: float,
    opponent_rating: float,
    *,
    home_field: float = 0.0,
) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(rating - opponent_rating + home_field) / 400.0))


def regress_probability(
    probability: float,
    weeks_ahead: int,
    *,
    decay: float = 0.05,
) -> float:
    if weeks_ahead < 0:
        raise WiloValidationError("weeks_ahead must be non-negative")

    weight = (1.0 - decay) ** weeks_ahead
    return 0.5 + weight * (probability - 0.5)
