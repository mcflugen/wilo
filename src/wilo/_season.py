from __future__ import annotations

import csv
import io
import urllib.request
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from dataclasses import dataclass
from http.client import HTTPException

from wilo._errors import WiloIOError
from wilo._errors import WiloValidationError
from wilo._json import load_json
from wilo._output import format_table
from wilo._teams import Team
from wilo._teams import norm_team

URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"


@dataclass(frozen=True)
class Game:
    away: Team
    home: Team
    score: None | tuple[int, int] = None

    def __post_init__(self):
        if self.away == self.home:
            raise WiloValidationError(f"{self.away} vs. {self.home}: invalid game")
        if self.score is not None:
            if len(self.score) != 2:
                raise WiloValidationError(f"{self.score!r}: invalid score")
            for points in self.score:
                if points < 0:
                    raise WiloValidationError(f"{points}: invalid score")


@dataclass
class Slate:
    week: int
    games: tuple[Game, ...]
    byes: frozenset[Team] = frozenset()

    def __post_init__(self):
        if self.week < 1 or self.week > 18:
            raise WiloValidationError(f"{self.week}: week must be between 1 and 18")

        home_teams = {game.home for game in self.games}
        away_teams = {game.away for game in self.games}

        if len(home_teams) != len(self.games):
            raise WiloValidationError("repeated home team")
        if len(away_teams) != len(self.games):
            raise WiloValidationError("repeated away team")

        missing_teams = set(Team) - (home_teams | away_teams | self.byes)
        if missing_teams:
            raise WiloValidationError(
                f"{', '.join(sorted(missing_teams))}: missing teams"
            )

        repeated_teams = (home_teams & away_teams) | (
            (home_teams | away_teams) & self.byes
        )
        if repeated_teams:
            raise WiloValidationError(
                f"{', '.join(sorted(repeated_teams))}: repeated teams"
            )

    def __iter__(self):
        yield from self.games

    def __len__(self) -> int:
        return len(self.games)

    def playing(self) -> frozenset[Team]:
        return frozenset(set(Team) - self.byes)

    def winners(self) -> frozenset[Team]:
        return frozenset(
            game.away if game.score[0] > game.score[1] else game.home
            for game in self
            if game.score is not None and game.score[0] != game.score[1]
        )

    def losers(self) -> frozenset[Team]:
        return frozenset(
            game.away if game.score[0] < game.score[1] else game.home
            for game in self
            if game.score is not None and game.score[0] != game.score[1]
        )

    def ties(self) -> frozenset[Team]:
        ties: set[Team] = set()
        for game in self:
            if game.score is not None and game.score[0] == game.score[1]:
                ties.add(game.away)
                ties.add(game.home)
        return frozenset(ties)

    def as_dict(self):
        return {
            "byes": sorted(self.byes),
            "games": [asdict(game) for game in self.games],
        }

    def tabulate(self) -> str:
        def _norm_score(score: tuple[int, int] | None):
            if score is None:
                return ("", "")
            return score

        headers = ["Away", "Score", "Home", "Score"]
        rows = [
            (
                game.away,
                _norm_score(game.score)[0],
                game.home,
                _norm_score(game.score)[1],
            )
            for game in self
        ]
        return format_table(rows, headers=headers)


@dataclass
class Season:
    year: int
    games: dict[int, Slate]

    @classmethod
    def from_file(cls, path: str, *, season: int = 2026):
        games = load_season(path)
        return cls(games=games, year=season)

    @classmethod
    def import_file(cls, path: str, *, season: int = 2026):
        try:
            with open(path, encoding="utf-8", newline="") as stream:
                games = import_season(stream, year=season)
        except OSError as error:
            raise WiloIOError(str(error)) from error

        return cls(season, games)

    @classmethod
    def download(cls, *, season: int = 2026):
        games = import_season(io.StringIO(download_season()), year=season)
        return cls(games=games, year=season)

    def as_dict(self):
        return {str(week): slate.as_dict() for week, slate in self.games.items()}

    def tabulate(self) -> str:
        return "\n\n".join(
            slate.tabulate() for week, slate in sorted(self.games.items())
        )

    def for_weeks(self, weeks: Iterable[int]) -> Season:
        return Season(year=self.year, games={week: self.games[week] for week in weeks})


def download_season() -> str:
    try:
        with urllib.request.urlopen(URL) as response:
            text = response.read().decode()
    except (OSError, HTTPException) as error:
        raise WiloIOError(f"{URL}: {error}") from error
    except UnicodeDecodeError as error:
        raise WiloValidationError(
            f"{URL}: downloaded schedule is not valid UTF-8"
        ) from error

    return text


def import_season(
    lines: Iterable[str],
    *,
    year: int,
) -> dict[int, Slate]:
    reader = csv.DictReader(lines, delimiter=",")

    season: dict[int, list[Game]] = defaultdict(list)
    for row in reader:
        if int(row["season"]) != year or row["game_type"] != "REG":
            continue

        score = (
            (int(row["away_score"]), int(row["home_score"]))
            if row["away_score"] != ""
            else None
        )

        week = int(row["week"])

        season[week].append(
            Game(
                away=Team(norm_team(row["away_team"])),
                home=Team(norm_team(row["home_team"])),
                score=score,
            )
        )

    return validate_season(
        {
            week: Slate(
                week=week,
                games=tuple(games),
                byes=frozenset(Team)
                - ({game.home for game in games} | {game.away for game in games}),
            )
            for week, games in season.items()
        }
    )


def load_season(path: str) -> dict[int, Slate]:
    season_as_dict = load_json(path)

    season = {}
    for week in season_as_dict:
        season[int(week)] = Slate(
            week=int(week),
            games=tuple(
                Game(
                    away=Team(game["away"]),
                    home=Team(game["home"]),
                    score=tuple(game["score"]) if game["score"] is not None else None,
                )
                for game in season_as_dict[week]["games"]
            ),
            byes=frozenset(season_as_dict[week]["byes"]),
        )

    return validate_season(season)


def validate_season(season: dict[int, Slate]) -> dict[int, Slate]:
    if len(season) != 18:
        raise WiloValidationError(f"{len(season)}: invalid number of weeks")

    for week in season:
        if week < 1 or week > 18:
            raise WiloValidationError(f"{week}: week must be between 1 and 18")

    opponents: dict[Team, list[Team | str]] = defaultdict(list)
    for slate in season.values():
        for game in slate:
            opponents[game.home].append(game.away)
            opponents[game.away].append(game.home)

        for bye in slate.byes:
            opponents[bye].append("BYE")

    for team in opponents:
        if len(opponents[team]) != 18:
            raise WiloValidationError(f"{team}: must play all 18 games")
        if opponents[team].count("BYE") != 1:
            raise WiloValidationError(f"{team}: team must have one, and only one, bye")

    return season
