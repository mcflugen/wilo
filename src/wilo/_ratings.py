from __future__ import annotations

import csv
import io
import urllib.request
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from http.client import HTTPException

from wilo._errors import WiloError
from wilo._errors import WiloIOError
from wilo._errors import WiloValidationError
from wilo._json import load_json
from wilo._output import format_table
from wilo._teams import NICKNAMES
from wilo._teams import Team

# https://neilpaine.substack.com/p/2026-nfl-odds-tracker-and-elo-ratings
# https://www.natesilver.net/p/2026-elway-nfl-ratings-projections-playoff-odds

ELWAY_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1cn8hoTWnefXFp5uuXylviIxyLuQ8i3U3HuenZlQ1jbc/"
    "gviz/tq?tqx=out:csv&headers=1&sheet=Data"
)


class Ratings(Mapping[Team, int]):
    def __init__(self, ratings: dict[Team, int]) -> None:
        self._ratings = {Team(team): rating for team, rating in ratings.items()}

        if len(self._ratings) != len(Team):
            raise WiloValidationError("ratings must contain all teams")

        for rating in self._ratings.values():
            if not isinstance(rating, int) or isinstance(rating, bool):
                raise WiloValidationError("ratings must be integer")
            if rating < 0:
                raise WiloValidationError("ratings must be positive")

    def __getitem__(self, team: Team) -> int:
        return self._ratings[team]

    def __iter__(self) -> Iterator[Team]:
        return iter(self._ratings)

    def __len__(self) -> int:
        return len(self._ratings)

    @classmethod
    def from_file(cls, path: str) -> Ratings:
        ratings = load_json(path)
        return cls(ratings)

    @classmethod
    def import_file(cls, path: str, source: str = "elway") -> Ratings:
        try:
            loader = _LOADERS[source]
        except KeyError as error:
            loaders = ", ".join(sorted(repr(name) for name in _LOADERS))
            raise WiloError(f"{source}: loader must be one of {loaders}") from error

        try:
            with open(path, encoding="utf-8", newline="") as stream:
                ratings = loader(stream)
        except OSError as error:
            raise WiloIOError(str(error)) from error

        return cls(ratings)

    @classmethod
    def download(cls) -> Ratings:
        try:
            text = download_elway()
        except (OSError, HTTPException) as error:
            raise WiloIOError(f"{ELWAY_URL}: {error}") from error
        except UnicodeDecodeError as error:
            raise WiloValidationError(
                f"{ELWAY_URL}: downloaded ratings is not valid UTF-8"
            ) from error

        ratings = import_elway_ratings(io.StringIO(text))
        return cls(ratings)

    def tabulate(self) -> str:
        return format_table(self.items(), headers=["Team", "Ratings"])


def import_elway_ratings(lines: Iterable[str]) -> dict[Team, int]:
    reader = csv.reader(lines, delimiter="\t")

    items = []
    for row in reader:
        try:
            items.append((row[0], row[2]))
        except IndexError as error:
            raise WiloValidationError(
                f"{reader.line_num}: row must contain at least 3 columns"
            ) from error

    return normalize_ratings(items)


def import_elo_ratings(lines: Iterable[str]) -> dict[Team, int]:
    reader = csv.reader(lines, delimiter="\t")

    items = []
    for row in reader:
        try:
            items.append((row[1], row[3]))
        except IndexError as error:
            raise WiloValidationError(
                f"{reader.line_num}: row must contain at least 4 columns"
            ) from error

    for team, _ in items:
        if team not in NICKNAMES:
            raise WiloValidationError(f"{team}: unknown team")

    return normalize_ratings([(NICKNAMES[item[0]], item[1]) for item in items])


def normalize_ratings(items: Sequence[tuple[str, str]]) -> dict[Team, int]:
    if len(items) != len(Team):
        raise WiloValidationError(f"expected {len(Team)} teams, found {len(items)}")

    ratings = {}
    for item in items:
        try:
            team = Team(item[0])
        except ValueError as error:
            raise WiloValidationError(str(error)) from error
        try:
            rating = int(item[1])
        except ValueError as error:
            raise WiloValidationError("rating must be an integer") from error

        ratings[team] = rating

    return dict(sorted(ratings.items()))


_LOADERS: dict[str, Callable[[Iterable[str]], dict[Team, int]]] = {
    "elway": import_elway_ratings,
    "elo": import_elo_ratings,
}


REQUIRED_ELWAY_FIELDS = {
    "nickname",
    "net_rating",
    "elo",
    "off_rating",
    "off_rank",
    "def_rating",
    "def_rank",
    "qb_rating",
}


def download_elway() -> str:
    with urllib.request.urlopen(ELWAY_URL, timeout=30) as response:
        text = response.read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))

    missing_fields = REQUIRED_ELWAY_FIELDS - set(reader.fieldnames or [])
    if missing_fields:
        raise WiloValidationError(
            f"{', '.join(sorted(missing_fields))}: missing fields"
        )

    rows = [parse_elway_row(row, line_num=reader.line_num) for row in reader]

    ratings_csv = io.StringIO()
    csv.writer(ratings_csv, delimiter="\t").writerows(rows)

    return ratings_csv.getvalue()


def parse_elway_row(
    row: dict[str, str | None],
    *,
    line_num: int,
) -> tuple[str | int, ...]:
    def _require_field(field: str) -> str:
        value = row[field]
        if value is None:
            raise WiloValidationError(f"{line_num}: row must contain {field}")
        return value

    fields = {field: _require_field(field) for field in REQUIRED_ELWAY_FIELDS}

    try:
        team = NICKNAMES[fields["nickname"]]
    except KeyError as error:
        raise WiloValidationError(
            f"{line_num}: team must be a valid NFL team ({fields['nickname']})"
        ) from error

    try:
        elo = round(float(fields["elo"]))
    except (OverflowError, ValueError) as error:
        raise WiloValidationError(
            f"{line_num}: elo must be a number ({fields['elo']})"
        ) from error

    return (
        team,
        fields["net_rating"],
        elo,
        fields["off_rating"],
        fields["off_rank"],
        fields["def_rating"],
        fields["def_rank"],
        fields["qb_rating"],
    )
