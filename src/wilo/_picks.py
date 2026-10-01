from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from wilo._errors import WiloValidationError
from wilo._teams import Team


class PickKind(StrEnum):
    WINNER = "winner"
    LOSER = "loser"


class Bye(StrEnum):
    WINNER = "BYE_WINNER"
    LOSER = "BYE_LOSER"


type PickOption = Team | Bye
type Selection = Team | Literal["BYE"]


@dataclass(frozen=True)
class Pick:
    winner: Selection | None
    loser: Selection | None

    def __post_init__(self):
        if self.winner is None and self.loser is None:
            return

        if self.winner not in (None, "BYE"):
            object.__setattr__(self, "winner", Team(self.winner))
        if self.loser not in (None, "BYE"):
            object.__setattr__(self, "loser", Team(self.loser))

        if self.winner != "BYE" and self.winner == self.loser:
            raise WiloValidationError("invalid pick")
