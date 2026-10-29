"""Accent-derived tints of the Telegram themes: mix, list, recolor.

A tint is N% of the accent mixed over a base role color. Both theme files
(.palette and .tgios-theme) carry the same tints, so an accent change must
recompute every tint, not only the accent itself.

  mix ACCENT BASE PCT        print the mixed color, e.g. mix d2a6ff 0b0e14 14
  show ACCENT FILE...        per tint: pct, base, value, the keys using it
  recolor OLD NEW FILE...    replace the accent and every tint OLD -> NEW in place

Hex tokens match with or without '#', keep an iOS alpha prefix (4dd2a6ff), and
match case-insensitively. BASES are role colors: if one changes, edit it here
first, then recolor.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASES: dict[str, str] = {
    "bg": "0b0e14",  # Ghostty bg: macOS canvas, iOS chat and list background
    "chip": "3a3f4b",  # muted badge, unplayed waveform in incoming bubbles
    "gray": "8f8e89",  # secondary text
    "icon": "6c7380",  # gray icons
}
# name: (accent percent, base: a BASES key or an earlier tint, role)
TINTS: dict[str, tuple[int, str, str]] = {
    "out": (14, "bg", "outgoing bubble"),
    "out_border": (22, "bg", "outgoing bubble border, iOS reaction chips"),
    "out_high": (24, "bg", "outgoing bubble highlight"),
    "out_select": (25, "out", "text selection in outgoing bubbles (macOS)"),
    "out_gray": (27, "gray", "secondary text in outgoing bubbles"),
    "out_icon": (29, "icon", "gray icons in outgoing bubbles"),
    "out_wave": (17, "chip", "unplayed waveform in outgoing bubbles"),
    "selected": (16, "bg", "selected chat row, pressed bot button"),
    "select_text": (28, "bg", "text selection (macOS)"),
    "focus": (30, "bg", "focus flash (macOS focusAnimationColor)"),
    "select_msg": (7, "bg", "selected messages (macOS)"),
}
HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def norm(value: str) -> str:
    m = HEX.match(value)
    if not m:
        raise argparse.ArgumentTypeError(f"not a #rrggbb color: {value!r}")
    return m.group(1).lower()


def mix(fg: str, bg: str, pct: int) -> str:
    f = [int(fg[i : i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg[i : i + 2], 16) for i in (0, 2, 4)]
    return "".join(
        f"{round(x * pct / 100 + y * (100 - pct) / 100):02x}" for x, y in zip(f, b)
    )


def tint_values(accent: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, (pct, base, _) in TINTS.items():
        base_hex = out[base] if base in out else BASES[base]
        out[name] = mix(accent, base_hex, pct)
    return out


def token(hexes: list[str]) -> re.Pattern[str]:
    alts = "|".join(sorted(hexes, key=len, reverse=True))
    return re.compile(
        rf"(?<![0-9a-fA-F])(#|[0-9a-fA-F]{{2}})?({alts})(?![0-9a-fA-F])", re.IGNORECASE
    )


def show(accent: str, files: list[Path]) -> None:
    values = tint_values(accent)
    texts = {p: p.read_text(encoding="utf-8").splitlines() for p in files}
    for name, (pct, base, role) in TINTS.items():
        pat = token([values[name]])
        used: list[str] = []
        for path, lines in texts.items():
            keys = sorted(
                {
                    ln.split("=" if path.suffix == ".palette" else ":")[0].strip()
                    for ln in lines
                    if pat.search(ln) and not ln.lstrip().startswith(("//", "#"))
                }
            )
            if keys:
                used.append(f"{path.suffix}: {' '.join(keys)}")
        print(f"{name:12} {pct:3}% over {base:6} = {values[name]}  {role}")
        for line in used:
            print(f"    {line}")


def recolor(old: str, new: str, files: list[Path]) -> int:
    before = {"accent": old, **tint_values(old)}
    after = {"accent": new, **tint_values(new)}
    mapping = {before[k]: after[k] for k in before}
    if len(mapping) != len(before):
        print("FAIL: two tints share a value, recolor would be ambiguous")
        return 1
    pat = token(list(mapping))
    fresh = [v for v in mapping.values() if v not in mapping]
    clash = token(fresh) if fresh else None
    for path in files:
        lines = path.read_text(encoding="utf-8").split("\n")
        n = 0

        def swap(m: re.Match[str]) -> str:
            nonlocal n
            n += 1
            return (m.group(1) or "") + mapping[m.group(2).lower()]

        for i, line in enumerate(lines):
            if line.lstrip().startswith(("//", "#")):
                continue  # header comments name the old accent: edit them by hand
            if clash and clash.search(line):
                print(
                    f"warn: {path.name}:{i + 1} already uses a new value: {line.strip()}"
                )
            lines[i] = pat.sub(swap, line)
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{path}: {n} replacements")
    for k, old_hex in before.items():
        print(f"  {k:12} {old_hex} -> {after[k]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_mix = sub.add_parser("mix")
    p_mix.add_argument("accent", type=norm)
    p_mix.add_argument("base", type=norm)
    p_mix.add_argument("pct", type=int)
    p_show = sub.add_parser("show")
    p_show.add_argument("accent", type=norm)
    p_show.add_argument("files", type=Path, nargs="*")
    p_re = sub.add_parser("recolor")
    p_re.add_argument("old", type=norm)
    p_re.add_argument("new", type=norm)
    p_re.add_argument("files", type=Path, nargs="+")
    args = ap.parse_args()
    try:
        if args.cmd == "mix":
            print(mix(args.accent, args.base, args.pct))
            return 0
        if args.cmd == "show":
            show(args.accent, args.files)
            return 0
        return recolor(args.old, args.new, args.files)
    except (OSError, UnicodeDecodeError) as err:
        print(f"FAIL: cannot read {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
