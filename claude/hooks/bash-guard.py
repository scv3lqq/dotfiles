#!/usr/bin/env python3
"""PreToolUse(Bash): block the two Bash habits CLAUDE.md forbids.

- `cd` at the top level of a command: the working directory persists across
  calls, so it silently changes the cwd for the rest of the session.
  A subshell form `(cd x && y)` is fine and is allowed.
- in-place rewrites of existing files (`sed -i`, `perl -i`): the harness
  re-dumps the whole file into context. Use Edit instead.
"""

from __future__ import annotations

import json
import re
import sys

SPLIT = re.compile(r"(?:\|\||&&|[;\n|])")
CD = re.compile(r"^cd(\s|$)")
INPLACE = re.compile(r"(?:^|\s)(sed\s+(?:-\S+\s+)*-i|perl\s+(?:-\S+\s+)*-p?i)(?:\b|\s)")
# Quoted spans are data, not commands: a grep pattern like "cd /x\|sed -i" must not
# be split on its \| and read as a command. Blank them out before scanning.
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    scan = QUOTED.sub(" ", command)

    for segment in SPLIT.split(scan):
        if CD.match(segment.strip()):
            print(
                "Blocked: `cd` changes the working directory for every later "
                "Bash call. Use absolute paths, or a subshell: (cd dir && cmd).",
                file=sys.stderr,
            )
            return 2

    if INPLACE.search(scan):
        print(
            "Blocked: in-place rewrite of an existing file. Use the Edit tool; "
            "an out-of-band write makes the harness re-dump the file into context.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
