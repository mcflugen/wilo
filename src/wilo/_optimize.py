from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Collection

from scipy.optimize import Bounds
from scipy.optimize import LinearConstraint
from scipy.optimize import milp

from wilo._errors import WiloOptimizationError
from wilo._errors import WiloValidationError
from wilo._picks import Bye
from wilo._picks import Pick
from wilo._picks import PickKind
from wilo._picks import PickOption
from wilo._picks import Selection
from wilo._player import PlayerPicks
from wilo._predict import predict_games
from wilo._ratings import Ratings
from wilo._season import Season
from wilo._teams import Team


def plan_picks(
    schedule: Season,
    ratings: Ratings,
    *,
    points: dict[int, float],
    available: Collection[PickOption],
) -> PlayerPicks:
    _validate_remaining_picks(schedule, choices=available)

    if not schedule.games:
        return PlayerPicks()

    predictions = predict_games(schedule, ratings)
    predictions.pop(18, None)

    picks = optimize_picks(
        predictions,
        points,
        available=available,
    )

    return PlayerPicks(
        {
            week: Pick(winner=pick[PickKind.WINNER], loser=pick[PickKind.LOSER])
            for week, pick in picks.items()
        }
    )


def _validate_remaining_picks(
    schedule: Season,
    *,
    choices: Collection[PickOption],
) -> None:
    choices = set(choices)

    n_weeks = len(schedule.games)
    n_slots = 2 * n_weeks
    if len(choices) != n_slots:
        raise WiloValidationError(
            f"{n_weeks} remaining weeks require {n_slots} picks, "
            f"but {len(choices)} unused teams/BYE allowances remain"
        )

    playing: set[Team] = set()
    for slate in schedule.games.values():
        playing |= slate.playing()

    choices = choices - set(Bye)
    if choices - playing:
        raise WiloValidationError(
            f"teams have no remaining game: {', '.join(sorted(choices - playing))}"
        )


def optimize_picks(
    probabilities: dict[int, dict[Team, float]],
    points: dict[int, float],
    available: Collection[PickOption],
) -> dict[int, dict[PickKind, Selection]]:
    available = frozenset(available)

    variables: list[tuple[int, PickOption, PickKind]] = []
    for week, teams in probabilities.items():
        for team in set(teams) & available:
            variables += [
                (week, team, PickKind.WINNER),
                (week, team, PickKind.LOSER),
            ]

        byes = set(Team) - set(teams)
        if byes and Bye.WINNER in available:
            variables += [(week, Bye.WINNER, PickKind.WINNER)]
        if byes and Bye.LOSER in available:
            variables += [(week, Bye.LOSER, PickKind.LOSER)]

    n_vars = len(variables)

    # scipy.optimize.milp minimizes, so negate expected points.
    c = [math.nan] * n_vars
    pick_probabilities = [0.0] * n_vars

    for i, (week, pick_option, kind) in enumerate(variables):
        # A BYE earns zero points in its designated slot.
        if isinstance(pick_option, Bye):
            c[i] = 0.0
            continue
        p_win = probabilities[week][pick_option]
        pick_probabilities[i] = p_win if kind == PickKind.WINNER else 1.0 - p_win
        c[i] = -points[week] * pick_probabilities[i]

    constraints = []

    # Exactly one winner and one loser per week.
    for week in probabilities:
        for kind in PickKind:
            row = [0.0] * n_vars

            for i, (w, _, k) in enumerate(variables):
                if w == week and k == kind:
                    row[i] = 1.0

            constraints.append(LinearConstraint(row, 1.0, 1.0))

    # Each team and each kind of BYE can be used at most once.
    pick_options = {pick_option for _, pick_option, _ in variables}
    for pick_option in pick_options:
        row = [0.0] * n_vars

        for i, (_, t, _) in enumerate(variables):
            if t == pick_option:
                row[i] = 1.0

        constraints.append(LinearConstraint(row, 0.0, 1.0))

    result = milp(
        c,
        integrality=[1] * n_vars,
        bounds=Bounds(0.0, 1.0),
        constraints=constraints,
    )

    if not result.success:
        raise WiloOptimizationError(result.message)

    picks: dict[int, dict[PickKind, Selection]] = defaultdict(dict)

    for x, (week, pick_option, kind), _probability in zip(
        result.x, variables, pick_probabilities
    ):
        if x > 0.5:
            picks[week][kind] = "BYE" if isinstance(pick_option, Bye) else pick_option

    return picks
