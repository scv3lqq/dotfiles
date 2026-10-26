---
name: refactor-proof
description: Prove a Python change is behavior-preserving at the AST level — comment-only / docstring-only edits, "no code token changed" claims, rename-free refactors — by diffing ASTs between a git ref and the working tree (optionally ignoring docstrings), plus a lint/type/coverage-pragma baseline check. Use before committing or approving any refactor that claims zero behavior change, and give the commands to implementer/reviewer agents as a gate.
---

# refactor-proof

Comments never reach the AST; docstrings do. So:
- comment-only change ⇒ `ast_equiv.py <base>` prints `SAME` for every file;
- comment + docstring change ⇒ `ast_equiv.py <base> --strip-docstrings` prints `SAME`
  (and the test suite is the proof for docstrings — check nothing introspects `__doc__`).
Either result also proves log events, metric names, exception messages, string literals and
config keys are untouched.

## Commands

```
SK=~/.claude/skills/refactor-proof
python3 $SK/ast_equiv.py <base_ref> [<head_ref>] [--strip-docstrings] [files...]
#   no files → every *.py in `git diff --name-only <base>[..<head>]`; exit 1 on any DIFF/NEW/GONE
```

Pragma baseline (lint/type/coverage pragmas must stay byte-identical, line numbers may move):

```
PR='#\s*(noqa(:\s*[A-Z0-9, ]+)?|type:\s*ignore(\[[^]]*\])?|pragma:\s*no cover)'
grep -rnoE "$PR" app/ tests/ | sed -E 's/^([^:]+):[0-9]+:/\1:/' | sort > /tmp/pragmas-base.txt   # run on the base first
grep -rnoE "$PR" app/ tests/ | sed -E 's/^([^:]+):[0-9]+:/\1:/' | sort | diff - /tmp/pragmas-base.txt   # empty ⇒ OK
```

## Procedure

1. Snapshot the base ref (`git rev-parse HEAD` before edits, or the branch base).
2. After edits: `ast_equiv.py <base> [--strip-docstrings]` → all `SAME`; pragma diff empty;
   project gate (lint + types + tests, coverage not below baseline).
3. Put both commands verbatim into implementer/reviewer prompts as the gate; state the proof in
   the commit body ("AST identical modulo docstrings, pragmas unchanged, tests green").
4. A `DIFF` on a file that should be comment-only means a code token changed — inspect
   `git diff -- <file>` before doing anything else.

Limits: AST equality ignores whitespace/blank-line layout inside code; if that matters, add a
tokenize-level comparison (drop COMMENT tokens, blank STRING docstring tokens).
