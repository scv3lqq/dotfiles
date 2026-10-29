"""Check a Telegram for iOS .tgios-theme the way the app decodes it.

Mirrors makePresentationTheme(data:) in PresentationThemeCoder.swift and the
Codable inits in PresentationThemeCodable.swift
(submodules/TelegramPresentationData/Sources) plus UIColor(hexString:) in
submodules/Display/Source/UIKitUtils.swift of TelegramMessenger/Telegram-iOS at
commit fb0e62b (2026-10-22). Reports key diff, value errors, the keys the app
drops when it re-encodes the theme on Apply, and WCAG contrast.

Usage: python3 -I check_ios_theme.py <file.tgios-theme>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TypeAlias

Node: TypeAlias = "str | dict[str, Node]"
RGBA = tuple[float, float, float, float]

# Leaf kinds: c color, L color list, b bool, n name, w wallpaper, d decimal,
# e:<a|b> enum (lowercased match)
BW = "e:black|white"
LD = "e:light|dark"


def cs(names: str) -> dict[str, Node]:
    return {n: "c" for n in names.split()}


def var() -> dict[str, Node]:
    return cs("withWp withoutWp")


def grad() -> dict[str, Node]:
    return cs("top bottom")


def field() -> dict[str, Node]:
    return cs("bg stroke placeholder primary control")


def fg() -> dict[str, Node]:
    return cs("bg fg")


def bubble() -> dict[str, Node]:
    return {
        "bgList": "L",
        **cs(
            "bg gradientBg highlightedBg stroke reactionInactiveBg reactionInactiveFg"
            " reactionActiveBg reactionActiveFg reactionInactiveMediaPlaceholder"
            " reactionActiveMediaPlaceholder"
        ),
        "shadow": {"color": "c", "radius": "d", "verticalOffset": "d"},
    }


def bubble_pair() -> dict[str, Node]:
    return {"withWp": bubble(), "withoutWp": bubble()}


def parted() -> dict[str, Node]:
    return {
        "bubble": bubble_pair(),
        **cs(
            "accentControl primaryText secondaryText linkText linkHighlight scam"
            " textHighlight accentText accentControlDisabled mediaActiveControl"
            " mediaInactiveControl mediaControlInnerBg pendingActivity fileTitle"
            " fileDescription fileDuration mediaPlaceholder textSelection"
            " textSelectionKnob"
        ),
        "polls": cs(
            "bar radioButton radioProgress highlight separator barIconForeground"
            " barPositive barNegative"
        ),
        "actionButtonsBg": var(),
        "actionButtonsStroke": var(),
        "actionButtonsText": var(),
    }


def service() -> dict[str, Node]:
    return cs("bg primaryText linkHighlight scam dateFillStatic dateFillFloat")


# Key tree the decoder reads (snapshot of commit fb0e62b)
TREE: dict[str, Node] = {
    "basedOn": "e:day|classic|nighttinted|night",
    "name": "n",
    "dark": "b",
    "intro": {
        "statusBar": BW,
        **cs("primaryText accentText disabledText startButton dot"),
    },
    "passcode": {"bg": grad(), "button": "c"},
    "root": {
        "statusBar": BW,
        "keyboard": LD,
        "tabBar": cs(
            "background separator icon selectedIcon text selectedText"
            " badgeBackground badgeStroke badgeText"
        ),
        "navBar": cs(
            "background opaqueBackground button disabledButton primaryText"
            " secondaryText control accentText separator badgeFill badgeStroke"
            " badgeText segmentedBg segmentedFg segmentedText segmentedDivider"
            " clearButtonBackground clearButtonForeground"
        ),
        "searchBar": cs(
            "background accent inputFill inputText inputPlaceholderText inputIcon"
            " inputClearButton separator"
        ),
    },
    "list": {
        **cs(
            "blocksBg modalBlocksBg plainBg modalPlainBg primaryText secondaryText"
            " disabledText accent highlighted destructive placeholderText"
            " itemBlocksBg itemModalBlocksBg itemHighlightedBg blocksSeparator"
            " plainSeparator disclosureArrow sectionHeaderText freeText"
            " freeTextError freeTextSuccess freeMonoIcon controlSecondary"
            " mediaPlaceholder scrollIndicator pageIndicatorInactive"
            " inputClearButton"
        ),
        "switch": cs("frame handle content positive negative"),
        "disclosureActions": {
            k: fg()
            for k in [
                "neutral1",
                "neutral2",
                "destructive",
                "constructive",
                "accent",
                "warning",
                "inactive",
            ]
        },
        "check": cs("bg stroke fg"),
        "freeInputField": field(),
        "freePlainInputField": field(),
        "itemInputField": field(),
        "itemBarChart": cs("color1 color2 color3"),
        "paymentOption": cs(
            "inactiveFill inactiveForeground activeFill activeForeground"
        ),
    },
    "chatList": {
        **cs(
            "bg itemSeparator itemBg pinnedItemBg itemHighlightedBg"
            " pinnedItemHighlightedBg itemSelectedBg title secretTitle dateText"
            " authorName messageText messageHighlightedText messageDraftText"
            " checkmark pendingIndicator failedFill failedFg muteIcon"
            " unreadBadgeActiveBg unreadBadgeActiveText unreadBadgeInactiveBg"
            " unreadBadgeInactiveText reactionBadgeActiveBg pinnedBadge"
            " pinnedSearchBar regularSearchBar sectionHeaderBg sectionHeaderText"
            " verifiedIconBg verifiedIconFg secretIcon onlineDot"
        ),
        "pinnedArchiveAvatar": {"background": grad(), "foreground": "c"},
        "unpinnedArchiveAvatar": {"background": grad(), "foreground": "c"},
        "storyUnseen": grad(),
        "storyUnseenPrivate": grad(),
        "storySeen": grad(),
    },
    "chat": {
        "defaultWallpaper": "w",
        "animateMessageColors": "b",
        "message": {
            "incoming": parted(),
            "outgoing": parted(),
            "freeform": bubble_pair(),
            **cs(
                "infoPrimaryText infoLinkText outgoingCheck mediaDateAndStatusBg"
                " mediaDateAndStatusText mediaHighlightOverlay"
            ),
            "shareButtonBg": var(),
            "shareButtonStroke": var(),
            "shareButtonFg": var(),
            "mediaOverlayControl": fg(),
            "selectionControl": cs("bg stroke fg"),
            "deliveryFailed": fg(),
            "stickerPlaceholder": var(),
            "stickerPlaceholderShimmer": var(),
        },
        "serviceMessage": {
            "components": {"withDefaultWp": service(), "withCustomWp": service()},
            **cs("unreadBarBg unreadBarStroke unreadBarText"),
            "dateText": var(),
        },
        "inputPanel": {
            **cs(
                "panelBg panelSeparator panelControlAccent panelControl_v2"
                " panelControlDisabled panelControlDestructive inputBg inputStroke"
                " inputPlaceholder_v2 inputText_v2 inputControl_v2 actionControlBg"
                " actionControlFg primaryText secondaryText mediaRecordDot"
            ),
            "mediaRecordControl": cs("button micLevel activeIcon"),
        },
        "inputMediaPanel": cs(
            "bg gifsBg panelHighlightedIcon panelIcon panelSeparator"
            " panelHighlightedIconBg panelContentVibrantOverlay"
            " panelContentControlVibrantOverlay panelContentControlVibrantSelection"
            " panelContentControlOpaqueOverlay panelContentControlOpaqueSelection"
            " panelContentVibrantSearchOverlay panelContentVibrantSearchOverlaySelected"
            " panelContentVibrantSearchOverlayHighlight panelContentOpaqueSearchOverlay"
            " panelContentOpaqueSearchOverlaySelected"
            " panelContentOpaqueSearchOverlayHighlight stickersBg stickersSectionText"
            " stickersSearchBg stickersSearchPlaceholder stickersSearchPrimary"
            " stickersSearchControl"
        ),
        "inputButtonPanel": cs(
            "panelSeparator panelBg buttonBg buttonHighlight buttonStroke"
            " buttonHighlightedBg buttonHighlightedStroke buttonText"
        ),
        "historyNav": cs("bg stroke fg badgeBg badgeStroke badgeText"),
    },
    "actionSheet": {
        "bgType": LD,
        **cs(
            "dim opaqueItemBg itemBg opaqueItemHighlightedBg itemHighlightedBg"
            " opaqueItemSeparator standardActionText destructiveActionText"
            " disabledActionText primaryText secondaryText controlAccent inputBg"
            " inputHollowBg inputBorder inputPlaceholder inputText inputClearButton"
            " checkContent"
        ),
    },
    "contextMenu": cs(
        "dim background itemSeparator sectionSeparator itemBg itemHighlightedBg"
        " primary secondary destructive badgeFill badgeForeground badgeInactiveFill"
        " badgeInactiveForeground extractedTint"
    ),
    "notification": {
        **cs("bg primaryText"),
        "expanded": {
            "bgType": LD,
            "navBar": cs("background primaryText control separator"),
        },
    },
    "chart": cs(
        "labels helperLines strongLines barStrongLines detailsText detailsArrow"
        " detailsView rangeViewFrame rangeViewMarker"
    ),
}


def optional(path: str) -> bool:
    """bgList replaces bg+gradientBg; a missing shadow means no shadow."""
    return path.endswith(".bgList") or ".shadow." in path


# Not written back by encodePresentationTheme(): Apply re-encodes the theme, so
# on reload these become the fallback (key, alpha) the decoder uses instead.
WRITE_BACK: dict[str, tuple[str, float]] = {
    "list.modalBlocksBg": ("list.blocksBg", 1),
    "list.modalPlainBg": ("list.plainBg", 1),
    "list.itemModalBlocksBg": ("list.itemBlocksBg", 1),
    "root.navBar.clearButtonBackground": ("list.freeInputField.bg", 1),
    "root.navBar.clearButtonForeground": ("list.freeInputField.primary", 1),
    **{
        f"list.freePlainInputField.{k}": (f"list.freeInputField.{k}", 1)
        for k in ("bg", "stroke", "placeholder", "primary", "control")
    },
    **{
        f"chat.message.{s}.accentControlDisabled": (
            f"chat.message.{s}.accentControl",
            0.5,
        )
        for s in ("incoming", "outgoing")
    },
    "contextMenu.badgeFill": ("contextMenu.destructive", 1),
    "contextMenu.badgeForeground": ("contextMenu.background", 1),
    "contextMenu.badgeInactiveFill": ("contextMenu.destructive", 1),
    "contextMenu.badgeInactiveForeground": ("contextMenu.background", 1),
    "contextMenu.extractedTint": ("contextMenu.background", 1),
    "list.paymentOption.inactiveFill": ("list.freeTextSuccess", 0.3),
    "list.paymentOption.inactiveForeground": ("list.freeTextSuccess", 1),
    "list.paymentOption.activeFill": ("list.freeTextSuccess", 1),
    "list.paymentOption.activeForeground": ("#ffffff", 1),
}

BG = "list.blocksBg"
IN = "chat.message.incoming.bubble.withoutWp.bg"
OUT = "chat.message.outgoing.bubble.withoutWp.bg"
# (text key, background key, background drawn over, minimum ratio)
CONTRAST: tuple[tuple[str, str, str, float], ...] = (
    ("list.primaryText", "list.itemBlocksBg", BG, 7),
    ("list.primaryText", BG, BG, 7),
    ("chatList.title", "chatList.bg", BG, 7),
    ("chatList.title", "chatList.pinnedItemBg", BG, 7),
    ("chat.message.incoming.primaryText", IN, BG, 7),
    ("chat.message.outgoing.primaryText", OUT, BG, 7),
    ("root.navBar.primaryText", "root.navBar.background", BG, 7),
    ("chat.inputPanel.inputText_v2", "chat.inputPanel.inputBg", BG, 7),
    ("actionSheet.primaryText", "actionSheet.opaqueItemBg", BG, 7),
    ("contextMenu.primary", "contextMenu.background", BG, 7),
    ("list.secondaryText", "list.itemBlocksBg", BG, 4.5),
    ("list.sectionHeaderText", BG, BG, 4.5),
    ("list.freeText", BG, BG, 4.5),
    ("list.accent", "list.itemBlocksBg", BG, 4.5),
    ("list.destructive", "list.itemBlocksBg", BG, 4.5),
    ("list.itemInputField.placeholder", "list.itemInputField.bg", BG, 4.5),
    ("chatList.messageText", "chatList.bg", BG, 4.5),
    ("chatList.dateText", "chatList.pinnedItemBg", BG, 4.5),
    ("chatList.unreadBadgeActiveText", "chatList.unreadBadgeActiveBg", BG, 4.5),
    ("chatList.unreadBadgeInactiveText", "chatList.unreadBadgeInactiveBg", BG, 4.5),
    ("chat.message.incoming.secondaryText", IN, BG, 4.5),
    ("chat.message.incoming.linkText", IN, BG, 4.5),
    ("chat.message.outgoing.secondaryText", OUT, BG, 4.5),
    ("chat.message.outgoing.linkText", OUT, BG, 4.5),
    (
        "chat.message.incoming.primaryText",
        "chat.message.incoming.textSelection",
        IN,
        4.5,
    ),
    (
        "chat.message.outgoing.primaryText",
        "chat.message.outgoing.textSelection",
        OUT,
        4.5,
    ),
    (
        "chat.message.incoming.primaryText",
        "chat.message.incoming.textHighlight",
        IN,
        4.5,
    ),
    (
        "chat.serviceMessage.components.withDefaultWp.primaryText",
        "chat.serviceMessage.components.withDefaultWp.bg",
        BG,
        4.5,
    ),
    (
        "chat.serviceMessage.dateText.withoutWp",
        "chat.serviceMessage.components.withDefaultWp.dateFillStatic",
        BG,
        4.5,
    ),
    ("chat.serviceMessage.unreadBarText", "chat.serviceMessage.unreadBarBg", BG, 4.5),
    ("chat.inputPanel.inputPlaceholder_v2", "chat.inputPanel.inputBg", BG, 4.5),
    ("chat.inputPanel.actionControlFg", "chat.inputPanel.actionControlBg", BG, 4.5),
    ("root.tabBar.text", "root.tabBar.background", BG, 4.5),
    ("root.tabBar.selectedText", "root.tabBar.background", BG, 4.5),
    ("root.tabBar.badgeText", "root.tabBar.badgeBackground", BG, 4.5),
    ("root.navBar.button", "root.navBar.background", BG, 4.5),
    ("root.navBar.secondaryText", "root.navBar.background", BG, 4.5),
    ("root.searchBar.inputPlaceholderText", "root.searchBar.inputFill", BG, 4.5),
    ("actionSheet.standardActionText", "actionSheet.opaqueItemBg", BG, 4.5),
    ("actionSheet.destructiveActionText", "actionSheet.opaqueItemBg", BG, 4.5),
    ("actionSheet.secondaryText", "actionSheet.opaqueItemBg", BG, 4.5),
    ("contextMenu.secondary", "contextMenu.background", BG, 4.5),
    ("contextMenu.destructive", "contextMenu.background", BG, 4.5),
    ("chat.historyNav.badgeText", "chat.historyNav.badgeBg", BG, 4.5),
    ("chat.inputButtonPanel.buttonText", "chat.inputButtonPanel.buttonBg", BG, 4.5),
    *(
        (f"list.disclosureActions.{s}.fg", f"list.disclosureActions.{s}.bg", BG, 4.5)
        for s in [
            "neutral1",
            "neutral2",
            "destructive",
            "constructive",
            "accent",
            "warning",
            "inactive",
        ]
    ),
)


def leaves(node: dict[str, Node], prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in node.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(leaves(v, path))
        else:
            out[path] = v
    return out


def parse(text: str) -> dict[str, Node] | None:
    """makePresentationTheme(data:): None where the Swift code returns nil."""
    top: dict[str, Node] = {}
    stack: list[tuple[dict[str, Node], int]] = [(top, 0)]
    for line in (ln for ln in re.split(r"[\n\r\v\f\x85\u2028\u2029]+", text) if ln):
        trimmed = line.strip(" \t")
        if trimmed.startswith(("#", "//")) or ":" not in line:
            continue
        key, _, rest = line.partition(":")
        spaces = len(key) - len(key.lstrip(" "))
        if spaces % 2 or spaces // 2 > stack[-1][1]:
            return None
        while spaces // 2 < stack[-1][1] and len(stack) > 1:
            stack.pop()
        value = rest.strip()
        if value:
            stack[-1][0][key.strip()] = value
        else:
            child: dict[str, Node] = {}
            stack[-1][0][key.strip()] = child
            stack.append((child, stack[-1][1] + 1))
    return top


def color(value: str) -> RGBA | None:
    if value.lower() == "clear":
        return (0.0, 0.0, 0.0, 0.0)
    clean = value.removeprefix("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", clean):
        return None
    n = int(clean, 16)
    alpha = (n >> 24 & 255) / 255 if len(value) > 7 else 1.0
    return ((n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, alpha)


def over(top: RGBA, base: RGBA) -> RGBA:
    a = top[3]

    def mix(t: float, b: float) -> float:
        return t * a + b * (1 - a)

    return (mix(top[0], base[0]), mix(top[1], base[1]), mix(top[2], base[2]), 1.0)


def lum(c: RGBA) -> float:
    def ch(x: float) -> float:
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a: RGBA, b: RGBA) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def valid(kind: str, v: str) -> bool:
    if kind == "c":
        return color(v) is not None
    if kind == "L":
        return True  # a nested 0:, 1: ... list, checked as its own leaves
    if kind == "b":
        return v.lower() in ("true", "false")
    if kind == "d":
        return re.fullmatch(r"-?\d+(\.\d+)?", v) is not None
    if kind == "w":
        return v.lower() == "builtin" or (len(v) in (6, 8) and color(v) is not None)
    if kind.startswith("e:"):
        return v.lower() in kind[2:].split("|")
    return True


def check(text: str) -> list[str]:
    tree = parse(text)
    if tree is None:
        return ["indentation: the app rejects the whole file (odd or skipped level)"]
    got = leaves(tree)
    spec = leaves(TREE)
    missing = [k for k in spec if k not in got and not optional(k)]
    unknown = [k for k in got if k not in spec and not re.search(r"\.bgList\.\d+$", k)]
    omitted = sorted(
        {k.rsplit(".", 1)[0] for k in spec if k not in got and optional(k)}
    )
    print(f"keys: {len(spec)} read by the decoder, {len(got)} in file")
    print(f"missing={missing} unknown={unknown}")
    print(f"optional omitted: {len(omitted)} groups (bgList, shadow)")
    fail = [f"missing {k}" for k in missing] + [f"unknown {k}" for k in unknown]
    for k, v in got.items():
        kind = spec.get(k, "c")
        if not valid(kind, v):
            fail.append(f"{k}: bad value {v!r} for kind {kind}")
    if got.get("dark", "").lower() != "true":
        fail.append("dark is not true: dark status bar and keyboard are not used")
    if fail:
        return fail

    cols = {k: c for k, v in got.items() if (c := color(v)) is not None}
    for key, (src, alpha) in WRITE_BACK.items():
        base = color(src) if src.startswith("#") else cols[src]
        if base is None:
            continue
        want = (*base[:3], base[3] * alpha)
        if any(abs(x - y) > 1 / 255 for x, y in zip(cols[key], want)):
            print(f"info: {key} reverts to {src} x{alpha} after Apply")
    bg = cols[BG]
    worst: dict[float, float] = {}
    for text_key, bg_key, under, need in CONTRAST:
        base = over(cols[bg_key], over(cols[under], bg))
        r = contrast(over(cols[text_key], base), base)
        worst[need] = min(worst.get(need, 99.0), r)
        if r < need:
            fail.append(f"contrast {text_key} on {bg_key}: {r:.2f} < {need}")
    print("contrast minimums:", {k: round(v, 2) for k, v in sorted(worst.items())})
    return fail


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("theme", type=Path)
    args = ap.parse_args()
    try:
        text = args.theme.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"FAIL: cannot read {args.theme}: {err}")
        return 1
    fail = check(text)
    if chr(0x2014) in text:
        fail.append("em dash in file")
    if fail:
        print("FAIL\n  " + "\n  ".join(fail))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
