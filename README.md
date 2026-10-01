# WILO — NFL winner/loser pool

> Each week, players pick one NFL team to win and another to lose. Each team
  can be used only once during the pool, across both types of picks. Players
  also have one "BYE" for each pick type, which earns no points. Correct picks
  earn the points assigned to that week and ties earn half credit. The pool covers
  weeks 1–17, excluding the final week of the regular season. The player with
  the most total points wins.

`wilo` imports NFL schedules and ratings, tracks a pool's picks, calculates
standings, and optimizes future picks. The pool covers weeks 1–17; the final
regular-season week is excluded.

## Installation

Requires Python 3.14 or later. From this repository, install with optimization
and table support:

```sh
python -m pip install -e '.[optimize,tables]'
```

The extras are independent:

- `optimize` installs SciPy and enables `wilo optimize`, for both JSON and table
  output.
- `tables` installs tabulate and enables `--table` output.

Use `python -m pip install -e .` for the base package, which has no third-party
runtime dependencies. It supports all commands except `optimize`, with JSON
output. Install just one extra with `'.[optimize]'` or `'.[tables]'` as needed.

## Pool data

Use `--data` **before the command** to select the pool's data directory. It defaults
to the current directory.

```text
data/2026/
    config.json
    games.json
    ratings.json
    picks.json
```

Start a new pool with `init`, specifying the season and each player:

```sh
wilo --data=data/2026 init --season 2026 --player "John Cleese" --player "Michael Palin"
```

Both `--season` and at least one `--player` are required. Repeat `--player` to add
more participants. Player names must be unique and nonempty.

`init` creates the directory if needed and writes:

- `config.json`, with the season, player names, and one point per correct pick
  for each of weeks 1–17.
- `picks.json`, with empty selections for every player and week.

It refuses to overwrite an existing `config.json` or `picks.json`. Edit the
`points` mapping in `config.json` to customize weekly scoring; all 17 weeks must
have a positive, finite point value. Download the schedule and ratings with the
commands below to create `games.json` and `ratings.json`.

Picks are grouped by week, then player. Edit `picks.json` to record each player's
`winner` and `loser` as team abbreviations or `"BYE"`; unfilled selections are
`null`. Each team can be selected only once per player across both roles, with
one BYE allowance for each role.

## Download or import schedules and ratings

Download the schedule and scores for the configured season, and the current
injury-adjusted ELWAY ratings:

```sh
wilo --data=data/2026 season --download --update
wilo --data=data/2026 ratings --download --update
```

`--update` writes `games.json` or `ratings.json` in the data directory. If the
file already exists, its previous contents are copied to a `.bak` file, replacing
any earlier backup. The ratings download provides current ratings, not historical
ratings selected by the configured season.

To import local source files instead:

```sh
wilo --data=data/2026 season schedule.csv --update
wilo --data=data/2026 ratings elway.tsv --update
```

Season input uses the nflverse games CSV format. Ratings input uses ELWAY TSV,
with one team per row and the team abbreviation, net rating, and Elo rating in
the first three columns. Source paths are relative to the current directory,
not to `--data`. The CLI currently imports ELWAY ratings only.

Omit `--update` to print the converted JSON to stdout:

```sh
wilo --data=data/2026 season schedule.csv
wilo ratings elway.tsv
wilo ratings --download
```

With neither a source file nor `--download`, these commands read the existing
JSON files in the data directory:

```sh
wilo --data=data/2026 season --table
wilo --data=data/2026 ratings --table
```

A source file and `--download` are mutually exclusive. So are `--table` and
`--update`. The `season` command also requires `config.json`.

## View picks and standings

Commands print JSON by default. Add `--table` for a GitHub-style Markdown table:

```sh
wilo --data=data/2026 picks
wilo --data=data/2026 picks --table
wilo --data=data/2026 picks --week 3 --week 4 --table
wilo --data=data/2026 picks --player "John Cleese" --player "Michael Palin" --table
wilo --data=data/2026 picks --player "John Cleese" --week 3 --table
wilo --data=data/2026 picks --player "John Cleese" --week 3
wilo --data=data/2026 standings --table
```

For `picks`, use `--player` to select players and `--week` to select weeks (1–17).
Repeat either option to select multiple values, or combine them to show only the
selected players' picks for the selected weeks. Omit a filter to include all
players or all weeks. Both filters apply to JSON and table output.

JSON output is grouped by week, then player. Table output shows one table per
week, with a row for each player. When `--player` is supplied, it instead shows
one table per selected player, with a row for each selected week, including when
`--week` is also supplied.

Standings use the saved scores and configured weekly points; ties earn half
credit.

## Predict games and optimize picks

Print win probabilities by week and team using the saved schedule and ratings:

```sh
wilo --data=data/2026 predict
```

Optimize a player's remaining picks using the saved schedule, ratings, pool
configuration, and existing picks. This requires the `optimize` extra; add the
`tables` extra to use `--table`:

```sh
wilo --data=data/2026 optimize --player "Michael Palin" --table
wilo --data=data/2026 optimize --player "Michael Palin"
```

Optimization starts at the player's first completely empty week and runs through
week 17. It prints proposed picks without changing `picks.json`.

## Help

```sh
wilo --help
wilo init --help
wilo ratings --help
wilo season --help
wilo --version
```
