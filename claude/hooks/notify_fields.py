"""Extract simple notification fields in one Python process."""

from __future__ import annotations

import json
import shlex
import sys


def extract_fields(payload: str) -> tuple[str, str, str, str]:
    try:
        obj = json.loads(payload)
    except (ValueError, RecursionError) as exc:
        raise ValueError("invalid payload") from exc
    if not isinstance(obj, dict):
        raise TypeError("payload is not an object")
    values = [obj.get(key) for key in ("hook_event_name", "message", "cwd", "transcript_path")]
    if any(isinstance(value, (dict, list)) or
           isinstance(value, str) and "\0" in value for value in values):
        raise ValueError("unsupported field")
    return (str(values[0] or ""), str(values[1] or ""),
            str(values[2] or ""), str(values[3] or ""))


def main() -> int:
    try:
        values = extract_fields(sys.stdin.read())
    except (ValueError, TypeError, UnicodeError):
        return 1
    for name, value in zip(("event", "message", "cwd", "transcript"), values):
        print(f"{name}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
