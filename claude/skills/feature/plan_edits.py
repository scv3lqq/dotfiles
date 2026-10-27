"""Verbatim prose edits carried in a plan as ```md E<n>-old / ```md E<n>-new fences.

Run from the repo (or worktree) root; <base> is the commit the old blocks were taken from.

  plan_edits.py stub <file> <base> <line|from-to>...   print E-blocks for those lines (new = old, to edit)
  plan_edits.py apply <plan> <file> <base>             write <file> = <base> version + all edits
  plan_edits.py check <plan> <file> <base>             compare <file> with that, byte for byte
"""

import difflib
import re
import subprocess
import sys
from pathlib import Path

BLOCK = re.compile(r"^```md E(\d+)-(old|new)\n(.*?)\n```$", re.MULTILINE | re.DOTALL)


def at_base(path: str, base: str) -> str:
    return subprocess.run(["git", "show", f"{base}:{path}"], capture_output=True, text=True, check=True).stdout


def stub(path: str, base: str, ranges: list[str]) -> None:
    lines = at_base(path, base).split("\n")
    spans = sorted((int(a), int(b or a)) for a, _, b in (r.partition("-") for r in ranges))
    for n, (first, last) in enumerate(spans, 1):
        old = "\n".join(lines[first - 1 : last])
        print(f"**E{n}.** (lines {first}-{last})\n\n```md E{n}-old\n{old}\n```\n\n```md E{n}-new\n{old}\n```\n")


def expected(plan: str, path: str, base: str) -> tuple[str, int]:
    blocks: dict[int, dict[str, str]] = {}
    for num, kind, body in BLOCK.findall(Path(plan).read_text()):
        blocks.setdefault(int(num), {})[kind] = body
    if sorted(blocks) != list(range(1, len(blocks) + 1)) or any(len(b) != 2 for b in blocks.values()):
        sys.exit(f"FAIL: need E1..En, each with an old and a new block; got {sorted(blocks)}")
    text = at_base(path, base)
    for num in sorted(blocks):
        old, new = blocks[num]["old"], blocks[num]["new"]
        hits = text.count(old)
        if hits != 1:
            sys.exit(f"FAIL: E{num} old block matches {hits} times")
        text = text.replace(old, new)
    return text, len(blocks)


def main(argv: list[str]) -> None:
    if len(argv) >= 4 and argv[0] == "stub":
        stub(argv[1], argv[2], argv[3:])
        return
    if len(argv) != 4 or argv[0] not in ("apply", "check"):
        sys.exit(__doc__)
    mode, plan, path, base = argv
    text, count = expected(plan, path, base)
    if mode == "apply":
        Path(path).write_text(text)
        print(f"APPLIED: {count} edits")
        return
    actual = Path(path).read_text()
    if actual == text:
        print(f"EDITS OK: {count} edits")
        return
    sys.stdout.writelines(difflib.unified_diff(text.splitlines(True), actual.splitlines(True), "expected", path))
    sys.exit("FAIL: file differs from base + plan edits")


if __name__ == "__main__":
    main(sys.argv[1:])
