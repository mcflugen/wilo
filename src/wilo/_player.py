from __future__ import annotations

from collections.abc import Mapping

from wilo._errors import WiloValidationError
from wilo._output import format_table
from wilo._picks import Bye
from wilo._picks import Pick
from wilo._picks import PickOption
from wilo._picks import Selection
from wilo._teams import Team


def first_empty_week(picks: PlayerPicks) -> int:
    for week in picks.weeks:
        pick = picks.for_week(week)
        if pick.winner is None and pick.loser is None:
            return week
    else:
        return -1


class PlayerPicks:
    def __init__(
        self,
        picks: Mapping[int, Pick] | None = None,
        n_weeks: int | None = None,
    ) -> None:
        picks = {} if picks is None else dict(picks)
        n_weeks = 17 if n_weeks is None else n_weeks

        for week in picks:
            if week < 1 or week > n_weeks:
                raise WiloValidationError(
                    f"{week}: week must be between 1 and {n_weeks}"
                )

        self._picks = {
            **{week: Pick(winner=None, loser=None) for week in range(1, n_weeks + 1)},
            **picks,
        }
        self._used = self._validate_picks()
        self._available = frozenset((set(Team) | set(Bye)) - self.used)

    @property
    def used(self) -> frozenset[PickOption]:
        return self._used

    @property
    def available(self) -> frozenset[PickOption]:
        return self._available

    @property
    def weeks(self) -> tuple[int, ...]:
        return tuple(sorted(self._picks))

    def for_week(self, week: int) -> Pick:
        return self._picks[week]

    def with_pick(self, week: int, pick: Pick) -> PlayerPicks:
        if week < 1 or week > 17:
            raise WiloValidationError(f"{week}: week must be between 1 and 17")
        return PlayerPicks({**self._picks, week: pick})

    def tabulate(self) -> str:
        headers = ("week", "winner", "loser")
        rows = [
            (week, pick.winner, pick.loser)
            for week, pick in sorted(self._picks.items())
        ]
        return format_table(rows, headers=headers)

    def as_dict(self) -> dict[int, dict[str, Selection | None]]:
        return {
            week: {"winner": pick.winner, "loser": pick.loser}
            for week, pick in self._picks.items()
        }

    def _validate_picks(self) -> frozenset[PickOption]:
        picked: set[PickOption] = set()
        for pick in self._picks.values():
            for kind, team in (("winner", pick.winner), ("loser", pick.loser)):
                if team is None:
                    continue
                selection = Bye(f"BYE_{kind.upper()}") if team == "BYE" else Team(team)
                if selection in picked:
                    raise WiloValidationError(f"{selection}: already picked")

                picked.add(selection)

        return frozenset(picked)
