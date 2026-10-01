from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterable
from collections.abc import Sequence
from typing import Any

from wilo._errors import WiloError
from wilo._errors import WiloIOError


def print_error(msg):
    print(msg, file=sys.stderr)


def update_path(path: str, text: str, backup: str | None = None) -> None:
    if os.path.isfile(path) and backup:
        try:
            shutil.copyfile(path, path + backup)
        except OSError as error:
            raise WiloIOError(str(error)) from error

    try:
        with open(path, "w") as stream:
            print(text, file=stream)
    except OSError as error:
        raise WiloIOError(str(error)) from error


def format_table(rows: Iterable[Iterable[Any]], headers: Sequence[str]) -> str:
    try:
        from tabulate import tabulate
    except ImportError as error:
        raise WiloError("Table output requires installing 'wilo[tables]'.") from error

    return tabulate(rows, headers=headers, tablefmt="github")
