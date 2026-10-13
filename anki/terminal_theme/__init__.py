"""Terminal Theme: makes Anki look like Ghostty + tmux.

Styling is done purely through aqt.gui_hooks and webview CSS/JS injection, so
nothing here depends on Anki internals beyond the public hook API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aqt import gui_hooks, mw
from aqt.webview import WebContent

ADDON = mw.addonManager.addonFromModule(__name__)
WEB_ROOT = f"/_addons/{ADDON}/web"
ADDON_DIR = Path(__file__).parent

DEFAULTS: dict[str, Any] = {
    "status_bar": True,
    "font_family": "JetBrainsMono Nerd Font",
    "font_size": 15,
    "qt_styling": False,
}

FONT_FALLBACKS = ('"JetBrains Mono"', "Menlo", "monospace")

# Context classes whose webviews get the theme. Matched by class name so that
# private Anki classes never have to be imported.
STYLED_CONTEXTS = frozenset(
    {
        "TopToolbar",
        "BottomBar",
        "DeckBrowser",
        "DeckBrowserBottomBar",
        "Overview",
        "OverviewBottomBar",
        "Reviewer",
        "ReviewerBottomBar",
    }
)

# card.queue values, see anki/consts.py: NEW, LRN, REV, DAY_LEARN_RELEARN.
QUEUE_LABELS = {0: "new", 1: "learn", 2: "review", 3: "learn", 4: "learn"}

QSS_MARKER = "/* terminal-theme */"

# Tokens substituted into web/qt.qss. Kept in sync with the :root block of
# web/theme.css by hand: Qt stylesheets cannot read CSS custom properties.
QSS_TOKENS = {
    "bg": "#0b0e14",
    "fg": "#bfbdb6",
    "black": "#11151c",
    "border": "#475266",
    "subtle": "#565b66",
    "accent": "#95e6cb",
    "cursor": "#e6b450",
    "sel-bg": "#409fff",
    "sel-fg": "#0b0e14",
}


def config() -> dict[str, Any]:
    merged = dict(DEFAULTS)
    user = mw.addonManager.getConfig(__name__) or {}
    merged.update(user)
    return merged


def _font_stack(family: str) -> str:
    return ", ".join((json.dumps(family), *FONT_FALLBACKS))


def _vars_style(conf: dict[str, Any]) -> str:
    """Inline <style> carrying the config-driven part of the palette."""
    return (
        "<style>:root,:root.night-mode{"
        f"--tt-font-family:{_font_stack(str(conf['font_family']))};"
        f"--tt-font-size:{int(conf['font_size'])}px;"
        "}</style>"
    )


def on_webview_will_set_content(web_content: WebContent, context: Any) -> None:
    name = type(context).__name__
    if name not in STYLED_CONTEXTS:
        return

    conf = config()
    web_content.css.append(f"{WEB_ROOT}/theme.css")
    web_content.head += _vars_style(conf)

    if name == "Reviewer" and conf["status_bar"]:
        web_content.js.append(f"{WEB_ROOT}/statusbar.js")


def _current_deck_name() -> str:
    try:
        return mw.col.decks.current()["name"].replace("::", "/")
    except Exception:
        return ""


def _active_queue() -> str | None:
    card = getattr(mw.reviewer, "card", None)
    if card is None:
        return None
    return QUEUE_LABELS.get(card.queue) or QUEUE_LABELS.get(card.type)


def push_status(*_args: Any) -> None:
    """Send deck, queue counts and the active queue to statusbar.js."""
    conf = config()
    if not conf["status_bar"] or mw.col is None:
        return

    counts = mw.col.sched.counts()
    payload = {
        "deck": _current_deck_name(),
        "counts": {
            "new": counts[0],
            "learn": counts[1],
            "review": counts[2],
        },
        "active": _active_queue(),
    }
    mw.reviewer.web.eval(
        "window.terminalTheme && window.terminalTheme.update("
        f"{json.dumps(payload)});"
    )


def _qss() -> str:
    qss = (ADDON_DIR / "web" / "qt.qss").read_text(encoding="utf-8")
    for token, value in QSS_TOKENS.items():
        qss = qss.replace("{{%s}}" % token, value)
    conf = config()
    qss = qss.replace("{{font-family}}", str(conf["font_family"]))
    qss = qss.replace("{{font-size}}", f"{int(conf['font_size'])}px")
    return f"{QSS_MARKER}\n{qss}"


def apply_qt_style(*_args: Any) -> None:
    """Append our QSS to Anki's, replacing any copy from an earlier call."""
    current = mw.app.styleSheet() or ""
    marker = current.find(QSS_MARKER)
    if marker != -1:
        current = current[:marker]

    if not config()["qt_styling"]:
        if marker != -1:
            mw.app.setStyleSheet(current)
        return

    mw.app.setStyleSheet(current + _qss())


mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js)")

gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
gui_hooks.reviewer_did_show_question.append(push_status)
gui_hooks.reviewer_did_show_answer.append(push_status)
gui_hooks.main_window_did_init.append(apply_qt_style)
gui_hooks.theme_did_change.append(apply_qt_style)
