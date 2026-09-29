from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from wilo._errors import WiloError
from wilo._errors import WiloIOError
from wilo._errors import WiloValidationError


def load_json(path: str) -> Any:
    try:
        with open(path) as stream:
            return json.load(stream, object_pairs_hook=reject_duplicate_keys)
    except OSError as error:
        raise WiloIOError(str(error)) from error
    except json.JSONDecodeError as error:
        raise WiloValidationError(str(error)) from error


def reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise WiloError(f"{key!r}: JSON keys must be unique")
        result[key] = value
    return result


def pretty_json(value: object, *, inline_depth: int = 2, indent: int = 2) -> str:
    def render(value: object, depth: int) -> str:
        if depth >= inline_depth or not isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, allow_nan=False)

        if not value:
            return "{}" if isinstance(value, dict) else "[]"

        padding = " " * (indent * (depth + 1))
        closing = " " * (indent * depth)

        if isinstance(value, dict):
            entries = [
                f"{json.dumps(str(key), ensure_ascii=False)}: {render(item, depth + 1)}"
                for key, item in value.items()
            ]
            opening, ending = "{", "}"
        else:
            entries = [render(item, depth + 1) for item in value]
            opening, ending = "[", "]"

        return (
            opening
            + "\n"
            + ",\n".join(padding + entry for entry in entries)
            + "\n"
            + closing
            + ending
        )

    return render(value, 0)
