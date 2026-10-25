---
paths:
  - "**/*.sh"
---

# Shell scripts

`#!/bin/bash` is bash 3.2 on macOS (Claude hooks, the status line), and
`#!/usr/bin/env bash` is too whenever PATH lacks Homebrew. Write for 3.2:

- No `mapfile`/`readarray`, `${var,,}`/`${var^^}`, associative arrays, `|&`.
- Brace a variable before a multibyte literal: `"${fill}━"`. In `"$fill━"`
  bash 3.2 reads the lead byte into the name and the glyph vanishes
  (2026-10-26, status line bar).
- `${var:0:n}` and `${#var}` on non-ASCII text depend on the caller's locale:
  build multibyte runs with loops.
- Check with `/bin/bash -n <file>` and run fixtures with `/bin/bash`, not the
  Homebrew bash.
