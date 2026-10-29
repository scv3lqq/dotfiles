"""Check the Ayu Ink Obsidian theme against measured computed styles.

Reads the D3 measure JSON files written by preview.py, verifies palette,
typography and APCA/WCAG contrast expectations, and prints one FAIL line per
failed assertion. Exit 0 when all pass, 1 when any fails, 2 on bad input.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

Rgb = tuple[float, float, float]
Rgba = tuple[float, float, float, float]

KEYS_TEXT: Final = (
    "body root sizer p h1 h2 h3 h4 strong link unresolved external tag "
    "codeInline codeBlock tokKeyword tokString tokFunction tokComment tokNumber "
    "tokOperator tokPunct blockquote calloutTitle calloutContent th td cmSizer "
    "cmLine cmH1 nav navActive tab status"
)
KEYS: Final = tuple(KEYS_TEXT.split())

SANS_KEYS: Final = ("p", "cmLine", "h1")
MONO_KEYS: Final = ("nav", "tab", "status", "codeInline", "codeBlock", "tag")
WIDTH_KEYS: Final = ("sizer", "cmSizer")
LINE_HEIGHT_KEYS: Final = ("p", "cmLine")
SIZE_RATIOS: Final = {
    "h1": 1.75,
    "h2": 1.4,
    "h3": 1.2,
    "h4": 1.05,
    "cmH1": 1.75,
    "codeInline": 0.875,
    "codeBlock": 0.875,
}
BOLD_KEYS: Final = ("h1", "h2", "h3", "h4")
SPACING_RATIOS: Final = {"h1": -0.022, "h2": -0.018}

APCA_MIN: Final = {
    "p": 80.0,
    "cmLine": 80.0,
    "h1": 85.0,
    "h2": 85.0,
    "h3": 85.0,
    "h4": 85.0,
    "strong": 85.0,
    "navActive": 85.0,
    "link": 75.0,
    "external": 75.0,
    "codeInline": 75.0,
    "codeBlock": 75.0,
    "blockquote": 75.0,
    "td": 75.0,
    "th": 75.0,
    "calloutContent": 75.0,
    "nav": 60.0,
    "tag": 60.0,
    "unresolved": 60.0,
    "tab": 60.0,
    "calloutTitle": 45.0,
    "tokKeyword": 55.0,
    "tokString": 55.0,
    "tokFunction": 55.0,
    "tokNumber": 55.0,
    "tokOperator": 55.0,
    "tokPunct": 55.0,
    "tokComment": 40.0,
    "status": 35.0,
}
APCA_P_MAX: Final = 95.0

BG_EXPECTED: Final = (11, 14, 20)
ACCENT_RGB: Final = (230, 180, 80)
LINK_DECORATION: Final[Rgb] = (142.0, 114.0, 56.0)
OBSIDIAN_PURPLE: Final[Rgb] = (138.0, 92.0, 245.0)
COLOR_TOLERANCE: Final = 12.0


class CheckInputError(Exception):
    """Unreadable file or malformed measure JSON."""


@dataclass(frozen=True)
class Measure:
    family: str
    size: float
    line_height: float | None
    weight: int
    letter_spacing: float
    max_width: float | None
    color: Rgba
    bg: tuple[int, int, int]
    decoration: Rgba
    box_shadow: str


def _y(rgb: Rgb) -> float:
    r, g, b = (c / 255 for c in rgb)
    y = 0.2126729 * r**2.4 + 0.7151522 * g**2.4 + 0.0721750 * b**2.4
    return float(y + (0.022 - y) ** 1.414) if y < 0.022 else y


def apca(text: Rgb, bg: Rgb) -> float:
    yt, yb = _y(text), _y(bg)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:
        s = (yb**0.56 - yt**0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (yb**0.65 - yt**0.62) * 1.14
    return 0.0 if s > -0.1 else (s + 0.027) * 100


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def wcag(a: Rgb, b: Rgb) -> float:
    la, lb = sorted(
        (
            0.2126 * _lin(x[0]) + 0.7152 * _lin(x[1]) + 0.0722 * _lin(x[2])
            for x in (a, b)
        ),
        reverse=True,
    )
    return (la + 0.05) / (lb + 0.05)


def _over(c: Rgba, bg: Rgb) -> Rgb:
    a = c[3]
    return (
        a * c[0] + (1 - a) * bg[0],
        a * c[1] + (1 - a) * bg[1],
        a * c[2] + (1 - a) * bg[2],
    )


def _dist(a: Rgb, b: Rgb) -> float:
    return math.dist(a, b)


def _num(raw: object, where: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise CheckInputError(f"{where}: expected a number")
    return float(raw)


def _opt_num(raw: object, where: str) -> float | None:
    return None if raw is None else _num(raw, where)


def _vec(raw: object, n: int, where: str) -> list[float]:
    if not isinstance(raw, list) or len(raw) != n:
        raise CheckInputError(f"{where}: expected a list of {n} numbers")
    return [_num(v, where) for v in raw]


def _field(entry: dict[str, object], name: str, where: str) -> object:
    if name not in entry:
        raise CheckInputError(f"{where}.{name}: missing")
    return entry[name]


def parse_measure(raw: object, where: str) -> Measure:
    if not isinstance(raw, dict):
        raise CheckInputError(f"{where}: expected an object")
    family = _field(raw, "family", where)
    shadow = _field(raw, "boxShadow", where)
    if not isinstance(family, str):
        raise CheckInputError(f"{where}.family: expected a string")
    if not isinstance(shadow, str):
        raise CheckInputError(f"{where}.boxShadow: expected a string")
    c = _vec(_field(raw, "color", where), 4, f"{where}.color")
    d = _vec(_field(raw, "decoration", where), 4, f"{where}.decoration")
    b = _vec(_field(raw, "bg", where), 3, f"{where}.bg")
    return Measure(
        family=family,
        size=_num(_field(raw, "size", where), f"{where}.size"),
        line_height=_opt_num(_field(raw, "lineHeight", where), f"{where}.lineHeight"),
        weight=int(_num(_field(raw, "weight", where), f"{where}.weight")),
        letter_spacing=_num(
            _field(raw, "letterSpacing", where), f"{where}.letterSpacing"
        ),
        max_width=_opt_num(_field(raw, "maxWidth", where), f"{where}.maxWidth"),
        color=(c[0], c[1], c[2], c[3]),
        bg=(int(b[0]), int(b[1]), int(b[2])),
        decoration=(d[0], d[1], d[2], d[3]),
        box_shadow=shadow,
    )


def load(path: Path) -> tuple[float, dict[str, Measure]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckInputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CheckInputError(f"{path}: malformed JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CheckInputError(f"{path}: expected an object")
    meta = data.get("meta")
    el = data.get("el")
    if not isinstance(meta, dict) or "base" not in meta:
        raise CheckInputError(f"{path}: meta.base: missing")
    if not isinstance(el, dict):
        raise CheckInputError(f"{path}: el: missing")
    base = _num(meta["base"], f"{path}: meta.base")
    measures = {
        key: parse_measure(value, f"{path}: el.{key}") for key, value in el.items()
    }
    return base, measures


class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failures: list[str] = []

    def check(
        self, ok: bool, name: str, key: str, what: str, got: object, want: str
    ) -> None:
        self.total += 1
        if not ok:
            self.failures.append(
                f"FAIL {name} {key}.{what}: got {_fmt(got)}, want {want}"
            )


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return str(round(value, 3))
    if isinstance(value, tuple):
        return "(" + ", ".join(_fmt(v) for v in value) + ")"
    return str(value)


def self_test(report: Report) -> None:
    black_on_white = apca((136, 136, 136), (255, 255, 255))
    white_on_black = apca((255, 255, 255), (136, 136, 136))
    report.check(
        abs(black_on_white - 63.1) <= 0.1,
        "apca",
        "selftest",
        "dark-on-light",
        black_on_white,
        "63.1 +-0.1",
    )
    report.check(
        abs(white_on_black + 68.5) <= 0.1,
        "apca",
        "selftest",
        "light-on-dark",
        white_on_black,
        "-68.5 +-0.1",
    )


def check_file(report: Report, name: str, base: float, el: dict[str, Measure]) -> None:
    for key in KEYS:
        report.check(key in el, name, key, "present", "missing", "selector matches")

    size_f = el["p"].size if "p" in el else base

    if "root" in el:
        report.check(
            el["root"].bg == BG_EXPECTED,
            name,
            "root",
            "bg",
            el["root"].bg,
            str(BG_EXPECTED),
        )
    if "p" in el:
        report.check(
            abs(el["p"].size - base) <= 0.01, name, "p", "size", el["p"].size, f"{base}"
        )

    for key in LINE_HEIGHT_KEYS:
        if key in el:
            m = el[key]
            ratio = None if m.line_height is None else m.line_height / m.size
            ok = ratio is not None and abs(ratio - 1.65) <= 0.01
            report.check(ok, name, key, "lineHeight", ratio, "1.65 +-0.01")

    for key in SANS_KEYS:
        if key in el:
            report.check(
                "SF Pro Text" in el[key].family,
                name,
                key,
                "family",
                el[key].family,
                "contains SF Pro Text",
            )
    for key in MONO_KEYS:
        if key in el:
            report.check(
                "JetBrainsMono Nerd Font" in el[key].family,
                name,
                key,
                "family",
                el[key].family,
                "contains JetBrainsMono Nerd Font",
            )

    for key in WIDTH_KEYS:
        if key in el:
            mw = el[key].max_width
            report.check(
                mw is not None and abs(mw - 36 * size_f) <= 1,
                name,
                key,
                "maxWidth",
                mw,
                f"{36 * size_f} +-1",
            )

    for key, ratio in SIZE_RATIOS.items():
        if key in el:
            got = el[key].size / size_f
            report.check(
                abs(got - ratio) <= 0.01, name, key, "size/F", got, f"{ratio} +-0.01"
            )

    for key in BOLD_KEYS:
        if key in el:
            report.check(
                el[key].weight == 600, name, key, "weight", el[key].weight, "600"
            )
    if "nav" in el:
        report.check(
            el["nav"].weight == 500, name, "nav", "weight", el["nav"].weight, "500"
        )

    for key, ratio in SPACING_RATIOS.items():
        if key in el:
            got = el[key].letter_spacing / el[key].size
            report.check(
                abs(got - ratio) <= 0.001,
                name,
                key,
                "letterSpacing/size",
                got,
                f"{ratio} +-0.001",
            )

    for key, minimum in APCA_MIN.items():
        if key not in el:
            continue
        m = el[key]
        text = _over(m.color, (float(m.bg[0]), float(m.bg[1]), float(m.bg[2])))
        bg = (float(m.bg[0]), float(m.bg[1]), float(m.bg[2]))
        lc = abs(apca(text, bg))
        report.check(lc >= minimum, name, key, "apca", lc, f">= {minimum}")
        if key == "p":
            report.check(
                lc <= APCA_P_MAX, name, key, "apca-max", lc, f"<= {APCA_P_MAX}"
            )
        ratio = wcag(text, bg)
        report.check(ratio >= 4.5, name, key, "wcag", ratio, ">= 4.5")
        if key == "p":
            report.check(ratio >= 12, name, key, "wcag-body", ratio, ">= 12")

    if "navActive" in el:
        shadow = el["navActive"].box_shadow
        ok = "rgb(230, 180, 80)" in shadow and "inset" in shadow
        report.check(
            ok, name, "navActive", "boxShadow", shadow, "inset rgb(230, 180, 80)"
        )

    if "link" in el:
        m = el["link"]
        bg = (float(m.bg[0]), float(m.bg[1]), float(m.bg[2]))
        dist = _dist(_over(m.decoration, bg), LINK_DECORATION)
        report.check(
            dist <= COLOR_TOLERANCE,
            name,
            "link",
            "decoration",
            dist,
            f"distance <= {COLOR_TOLERANCE} from (142, 114, 56)",
        )

    for key in KEYS:
        if key not in el:
            continue
        m = el[key]
        bg = (float(m.bg[0]), float(m.bg[1]), float(m.bg[2]))
        for what, value in (
            ("color", _over(m.color, bg)),
            ("decoration", _over(m.decoration, bg)),
            ("bg", bg),
        ):
            dist = _dist(value, OBSIDIAN_PURPLE)
            report.check(
                dist > COLOR_TOLERANCE,
                name,
                key,
                f"{what}-purple",
                dist,
                f"distance > {COLOR_TOLERANCE} from (138, 92, 245)",
            )


def main(argv: list[str]) -> int:
    if not argv:
        print("check: usage: check.py FILE...", file=sys.stderr)
        return 2
    report = Report()
    self_test(report)
    for arg in argv:
        path = Path(arg)
        try:
            base, el = load(path)
        except CheckInputError as exc:
            print(f"check: {exc}", file=sys.stderr)
            return 2
        check_file(report, path.name, base, el)
    for line in report.failures:
        print(line)
    if report.failures:
        print(f"{len(report.failures)} of {report.total} checks failed")
        return 1
    print(f"OK {report.total} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
