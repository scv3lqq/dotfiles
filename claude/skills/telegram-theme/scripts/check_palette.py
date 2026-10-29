"""Check a Telegram for macOS .palette the way the app parses it.

Mirrors importPalette() in Telegram-Mac/ParseAppearanceColors.swift and the
ColorPalette init in packages/ColorPalette/Sources/ColorPalette/ColorPalette.swift
of TelegramOrg/Telegram-macos-Swift at commit 579cebb (2025-07-29). Reports key
diff, value errors, alpha clamping, HSV auto-replacement risk and WCAG contrast.

Usage: python3 -I check_palette.py <file.palette>
"""

from __future__ import annotations

import argparse
import colorsys
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RGB = tuple[float, float, float]

# Single-color keys importPalette() reads (snapshot of commit 579cebb)
COLOR_KEYS: tuple[str, ...] = (
    "basicAccent",
    "background",
    "text",
    "grayText",
    "link",
    "accent",
    "redUI",
    "greenUI",
    "blackTransparent",
    "grayTransparent",
    "grayUI",
    "darkGrayText",
    "accentSelect",
    "selectText",
    "border",
    "grayBackground",
    "grayForeground",
    "grayIcon",
    "accentIcon",
    "badgeMuted",
    "badge",
    "indicatorColor",
    "selectMessage",
    "monospacedPre",
    "monospacedCode",
    "monospacedPreBubble_incoming",
    "monospacedPreBubble_outgoing",
    "monospacedCodeBubble_incoming",
    "monospacedCodeBubble_outgoing",
    "selectTextBubble_incoming",
    "selectTextBubble_outgoing",
    "bubbleBackground_incoming",
    "bubbleBorder_incoming",
    "bubbleBorder_outgoing",
    "grayTextBubble_incoming",
    "grayTextBubble_outgoing",
    "grayIconBubble_incoming",
    "grayIconBubble_outgoing",
    "accentIconBubble_incoming",
    "accentIconBubble_outgoing",
    "linkBubble_incoming",
    "linkBubble_outgoing",
    "textBubble_incoming",
    "textBubble_outgoing",
    "selectMessageBubble",
    "fileActivityBackground",
    "fileActivityForeground",
    "fileActivityBackgroundBubble_incoming",
    "fileActivityBackgroundBubble_outgoing",
    "fileActivityForegroundBubble_incoming",
    "fileActivityForegroundBubble_outgoing",
    "waveformBackground",
    "waveformForeground",
    "waveformBackgroundBubble_incoming",
    "waveformBackgroundBubble_outgoing",
    "waveformForegroundBubble_incoming",
    "waveformForegroundBubble_outgoing",
    "webPreviewActivity",
    "webPreviewActivityBubble_incoming",
    "webPreviewActivityBubble_outgoing",
    "redBubble_incoming",
    "redBubble_outgoing",
    "greenBubble_incoming",
    "greenBubble_outgoing",
    "chatReplyTitle",
    "chatReplyTextEnabled",
    "chatReplyTextDisabled",
    "chatReplyTitleBubble_incoming",
    "chatReplyTitleBubble_outgoing",
    "chatReplyTextEnabledBubble_incoming",
    "chatReplyTextEnabledBubble_outgoing",
    "chatReplyTextDisabledBubble_incoming",
    "chatReplyTextDisabledBubble_outgoing",
    "groupPeerNameRed",
    "groupPeerNameOrange",
    "groupPeerNameViolet",
    "groupPeerNameGreen",
    "groupPeerNameCyan",
    "groupPeerNameLightBlue",
    "groupPeerNameBlue",
    "peerAvatarRedTop",
    "peerAvatarRedBottom",
    "peerAvatarOrangeTop",
    "peerAvatarOrangeBottom",
    "peerAvatarVioletTop",
    "peerAvatarVioletBottom",
    "peerAvatarGreenTop",
    "peerAvatarGreenBottom",
    "peerAvatarCyanTop",
    "peerAvatarCyanBottom",
    "peerAvatarBlueTop",
    "peerAvatarBlueBottom",
    "peerAvatarPinkTop",
    "peerAvatarPinkBottom",
    "bubbleBackgroundHighlight_incoming",
    "bubbleBackgroundHighlight_outgoing",
    "chatDateActive",
    "chatDateText",
    "revealAction_neutral1_background",
    "revealAction_neutral1_foreground",
    "revealAction_neutral2_background",
    "revealAction_neutral2_foreground",
    "revealAction_destructive_background",
    "revealAction_destructive_foreground",
    "revealAction_constructive_background",
    "revealAction_constructive_foreground",
    "revealAction_accent_background",
    "revealAction_accent_foreground",
    "revealAction_warning_background",
    "revealAction_warning_foreground",
    "revealAction_inactive_background",
    "revealAction_inactive_foreground",
    "chatBackground",
    "listBackground",
    "listGrayText",
    "grayHighlight",
    "focusAnimationColor",
    "premium",
    "vibrant",
)
HEADER_KEYS = ("name", "isDark", "tinted", "copyright", "wallpaper", "parent")
LIST_KEY = "bubbleBackground_outgoing"  # comma-separated #rrggbb list
PARENTS = {
    "Day",
    "day",
    "Day Classic",
    "dayClassic",
    "Dark",
    "dark",
    "Tinted Blue",
    "Night Blue",
    "nightAccent",
    "System",
    "system",
}
# Assigned in ColorPalette.init without the max(0.6, alpha) clamp
UNCLAMPED = {
    "listBackground",
    "listGrayText",
    "grayHighlight",
    "focusAnimationColor",
    "premium",
    "vibrant",
}
# ColorPalette.init replaces a color whose H+S+V sum is within 0.005 of its pair
HSV_PAIRS: tuple[tuple[str, str], ...] = (
    *(
        (k, "background")
        for k in (
            "link",
            "text",
            "accent",
            "accentIcon",
            "grayIcon",
            "grayText",
            "accentSelect",
        )
    ),
    ("textBubble_incoming", "bubbleBackground_incoming"),
    *(
        (k, LIST_KEY)
        for k in (
            "textBubble_outgoing",
            "grayTextBubble_incoming",
            "grayTextBubble_outgoing",
            "grayIconBubble_incoming",
            "grayIconBubble_outgoing",
            "accentIconBubble_incoming",
            "accentIconBubble_outgoing",
        )
    ),
)
WHITE = "#ffffff"  # underSelectedColor and the tab bar badge text are white
CONTRAST: tuple[tuple[str, str, float], ...] = (
    ("text", "background", 7),
    ("text", "chatBackground", 7),
    ("text", "listBackground", 7),
    ("text", "grayBackground", 7),
    (WHITE, "accentSelect", 7),
    ("textBubble_incoming", "bubbleBackground_incoming", 7),
    ("textBubble_outgoing", LIST_KEY, 7),
    ("text", "selectText", 4.5),
    ("grayText", "background", 4.5),
    ("grayText", "grayBackground", 4.5),
    ("listGrayText", "listBackground", 4.5),
    ("darkGrayText", "background", 4.5),
    ("accent", "background", 4.5),
    ("link", "chatBackground", 4.5),
    ("redUI", "background", 4.5),
    ("greenUI", "background", 4.5),
    ("background", "badge", 4.5),
    (WHITE, "badgeMuted", 4.5),
    ("chatDateText", "chatDateActive", 4.5),
    ("monospacedCode", "chatBackground", 4.5),
    ("grayTextBubble_incoming", "bubbleBackground_incoming", 4.5),
    ("linkBubble_incoming", "bubbleBackground_incoming", 4.5),
    ("chatReplyTitleBubble_incoming", "bubbleBackground_incoming", 4.5),
    ("grayTextBubble_outgoing", LIST_KEY, 4.5),
    ("linkBubble_outgoing", LIST_KEY, 4.5),
    ("chatReplyTitleBubble_outgoing", LIST_KEY, 4.5),
    ("monospacedCodeBubble_outgoing", LIST_KEY, 4.5),
    ("textBubble_outgoing", "selectTextBubble_outgoing", 4.5),
    *(
        (f"revealAction_{s}_foreground", f"revealAction_{s}_background", 4.5)
        for s in (
            "neutral1",
            "neutral2",
            "destructive",
            "constructive",
            "accent",
            "warning",
            "inactive",
        )
    ),
    ("grayIcon", "background", 3),
)


@dataclass
class Palette:
    header: dict[str, str]
    colors: dict[str, tuple[int, float]]
    errors: list[str]


def parse(text: str) -> Palette:
    pal = Palette({}, {}, [])
    seen: set[str] = set()
    for raw in (ln for ln in text.split("\n") if ln):
        if raw.strip().startswith("//"):
            continue
        parts = raw.split("=")
        if len(parts) > 2:
            parts = [parts[0], "=".join(parts[1:])]
        if len(parts) != 2:
            pal.errors.append(f"ignored line: {raw!r}")
            continue
        name, value = parts[0].strip(), parts[1].strip()
        if name in seen:
            pal.errors.append(f"duplicate key {name}")
        seen.add(name)
        if name in HEADER_KEYS or name == LIST_KEY:
            pal.header[name] = value
            continue
        hexpart, _, alpha = value.partition(":")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", hexpart.strip()):
            pal.errors.append(f"{name}: want #rrggbb[:alpha], got {value!r}")
            continue
        try:
            a = float(alpha) if alpha else 1.0
        except ValueError:
            pal.errors.append(f"{name}: bad alpha {alpha!r}")
            continue
        pal.colors[name] = (int(hexpart.strip()[1:], 16), max(0.0, min(1.0, a)))
    return pal


def rgb(v: int) -> RGB:
    return ((v >> 16 & 255) / 255, (v >> 8 & 255) / 255, (v & 255) / 255)


def lum(c: RGB) -> float:
    def ch(x: float) -> float:
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a: RGB, b: RGB) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check(pal: Palette) -> list[str]:
    fail = list(pal.errors)
    h = pal.header
    for k in (*HEADER_KEYS, LIST_KEY):
        if k not in h:
            fail.append(f"missing header {k}")
    if "name" not in h:
        fail.append("no name: the app rejects the file")
    if h.get("isDark") != "1":
        fail.append(f"isDark = {h.get('isDark')!r}: want 1 for a dark theme")
    if h.get("parent") not in PARENTS:
        fail.append(f"parent {h.get('parent')!r} is not a builtin theme")
    wp = h.get("wallpaper", "")
    if not (
        wp in ("none", "builtin")
        or re.fullmatch(r"#[0-9a-fA-F]{6}", wp)
        or "t.me/bg/" in wp
    ):
        fail.append(f"wallpaper {wp!r}: none, builtin, #rrggbb or t.me/bg/<slug>")
    outs = h.get(LIST_KEY, "").split(",")
    # NSColor(hexString:) lowercases before its charset check (Colors.swift:37) but
    # does not trim, so a space after a comma drops that color
    if not all(re.fullmatch(r"#[0-9a-fA-F]{6}", o) for o in outs):
        fail.append(f"{LIST_KEY}: want #rrggbb[,#rrggbb], no spaces")
    missing = [k for k in COLOR_KEYS if k not in pal.colors]
    unknown = [k for k in pal.colors if k not in COLOR_KEYS]
    print(
        f"keys: {len(COLOR_KEYS)} color + {LIST_KEY}; missing={missing} unknown={unknown}"
    )
    fail += [f"missing {k}" for k in missing] + [f"unknown {k}" for k in unknown]
    for k, (_, a) in pal.colors.items():
        if a < 0.6 and k not in UNCLAMPED:
            fail.append(f"{k}: alpha {a} is clamped to 0.6 by the app")
    # Wallpaper none or a color != background makes chatServiceItemTextColor pure
    # white (Appearance.swift:2436-2460, :2149): date pills outshine message text
    if (
        "background" in pal.colors
        and pal.colors.get("chatBackground") != pal.colors["background"]
    ):
        fail.append("chatBackground != background: service text turns pure white")
    if missing or fail:
        return fail

    c = {k: rgb(v) for k, (v, _) in pal.colors.items()}
    c[LIST_KEY] = rgb(int(outs[0][1:], 16))
    c[WHITE] = (1.0, 1.0, 1.0)
    for a_key, b_key in HSV_PAIRS:
        d = abs(
            sum(colorsys.rgb_to_hsv(*c[a_key])) - sum(colorsys.rgb_to_hsv(*c[b_key]))
        )
        if d < 0.02:
            fail.append(
                f"{a_key} vs {b_key}: HSV sums {d:.4f} apart, the app may replace it"
            )
    worst: dict[float, float] = {}
    for fg, bg, need in CONTRAST:
        r = contrast(c[fg], c[bg])
        worst[need] = min(worst.get(need, 99.0), r)
        if r < need:
            fail.append(f"contrast {fg} on {bg}: {r:.2f} < {need}")
    print("contrast minimums:", {k: round(v, 2) for k, v in sorted(worst.items())})
    badge = contrast(c[WHITE], c["redUI"])
    print(f"info: tab bar badge (hardcoded white on redUI) {badge:.2f}")
    return fail


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("palette", type=Path)
    args = ap.parse_args()
    try:
        text = args.palette.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"FAIL: cannot read {args.palette}: {err}")
        return 1
    fail = check(parse(text))
    if chr(0x2014) in text:
        fail.append("em dash in file")
    if fail:
        print("FAIL\n  " + "\n  ".join(fail))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
