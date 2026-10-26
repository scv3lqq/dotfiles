# /// script
# requires-python = ">=3.11"
# dependencies = ["marionette_driver==3.7.1"]
# ///
"""Render the Zen theme in zen/ headless and dump computed styles.

Creates a throwaway profile, symlinks zen/user.js and zen/chrome/userChrome.css
into it, starts Zen headless with Marionette, builds a small tab set, reads the
computed styles of the probed elements and the reported prefs, writes two PNGs
(plain window, floating URL bar open) and a JSON next to the first one. It never
touches a running Zen or a real profile: it signals only the process it started.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

# marionette_driver has invalid escape sequences in its source, which warn on import.
warnings.filterwarnings("ignore", category=SyntaxWarning)

# The package ships no type information.
from marionette_driver.marionette import Marionette  # type: ignore[import-untyped]

DEFAULT_ZEN: Final = "/Applications/Zen.app/Contents/MacOS/zen"
SRC_DIR: Final = Path(__file__).resolve().parent

# Written to prefs.js; user.js is read after prefs.js and wins.
HARNESS_PREFS: Final[MappingProxyType[str, bool | int | str]] = MappingProxyType(
    {
        "toolkit.legacyUserProfileCustomizations.stylesheets": True,
        "zen.welcome-screen.seen": True,
        "zen.updates.show-update-notification": False,
        "browser.shell.checkDefaultBrowser": False,
        "browser.aboutwelcome.enabled": False,
        "trailhead.firstrun.didSeeAboutWelcome": True,
        "browser.startup.homepage_override.mstone": "ignore",
        "startup.homepage_welcome_url": "",
        "startup.homepage_welcome_url.additional": "",
        "app.update.auto": False,
        "app.update.checkInstallTime": False,
        "app.update.disabledForTesting": True,
        "datareporting.policy.dataSubmissionEnabled": False,
        "datareporting.healthreport.uploadEnabled": False,
        "toolkit.telemetry.reportingpolicy.firstRun": False,
        "browser.tabs.warnOnClose": False,
        "browser.warnOnQuit": False,
        "marionette.port": 0,
    }
)

REPORTED_PREFS: Final = (
    "toolkit.legacyUserProfileCustomizations.stylesheets",
    "zen.view.window.scheme",
    "zen.theme.accent-color",
    "zen.theme.border-radius",
    "zen.theme.content-element-separation",
    "zen.widget.macos.window-vibrancy",
    "zen.theme.essentials-favicon-bg",
)

TAB_URLS: Final = (
    "about:blank",
    "data:text/html,<title>Plain%20tab</title>hello",
    "about:robots",
)


@dataclass(frozen=True)
class Probe:
    name: str
    selector: str
    props: tuple[str, ...]
    pseudo: str | None = None


CHROME_PROBES: Final = (
    Probe(
        "root",
        ":root",
        ("--zen-primary-color", "--toolbox-textcolor", "font-family", "color-scheme"),
    ),
    Probe("browser_bg", "#zen-browser-background", ("--zen-main-browser-background",)),
    Probe(
        "toolbar_bg",
        "#zen-toolbar-background",
        ("--zen-main-browser-background-toolbar",),
    ),
    Probe("grain", ".zen-browser-grain", ("display",)),
    Probe(
        "urlbar_bg",
        "#urlbar > .urlbar-background",
        ("background-color", "border-radius", "box-shadow"),
    ),
    Probe(
        "urlbar_input",
        "#urlbar-input",
        ("color", "caret-color", "font-family", "font-size"),
    ),
    Probe(
        "urlbar_prompt",
        "#urlbar .urlbar-input-container",
        ("content", "color"),
        "::before",
    ),
    Probe(
        "tab_selected_bg",
        "zen-workspace[active] .tabbrowser-tab[selected]:not([zen-essential]) "
        ".tab-background",
        ("background-color", "border-radius", "box-shadow"),
    ),
    Probe(
        "tab_selected_label",
        "zen-workspace[active] .tabbrowser-tab[selected]:not([zen-essential]) "
        ".tab-label",
        ("color", "font-family", "font-size"),
    ),
    Probe(
        "tab_label",
        "zen-workspace[active] .tabbrowser-tab:not([selected], [zen-essential], "
        "[pinned], [multiselected]) .tab-label",
        ("color",),
    ),
    Probe(
        "tab_close",
        "zen-workspace[active] .tabbrowser-tab[selected] .tab-close-button",
        ("color",),
    ),
    Probe(
        "essential_bg",
        ".tabbrowser-tab[zen-essential]:not([selected]) .tab-background",
        ("background-color", "border-radius"),
    ),
    Probe(
        "content_frame",
        ".browserSidebarContainer.deck-selected",
        ("box-shadow", "border-radius"),
    ),
    Probe(
        "content_browser",
        '.browserSidebarContainer.deck-selected browser[type="content"]',
        ("background-color",),
    ),
    Probe(
        "space_name",
        ".zen-current-workspace-indicator-name",
        ("color", "font-weight"),
    ),
    Probe(
        "sidebar_button",
        "#zen-sidebar-foot-buttons > toolbarbutton.toolbarbutton-1",
        ("color",),
    ),
    Probe("panel_font", "panel", ("font-family",)),
    Probe("menupopup_font", "menupopup", ("font-family",)),
)

URLBAR_PROBES: Final = (
    Probe(
        "urlbar_open_bg",
        "#urlbar[breakout-extend] > .urlbar-background",
        ("background-color", "border-radius", "box-shadow"),
    ),
    Probe(
        "urlbar_open_input", "#urlbar[breakout-extend] #urlbar-input", ("font-size",)
    ),
    Probe(
        "row_selected",
        ".urlbarView-row[selected]",
        ("background-color", "box-shadow", "border-radius"),
    ),
    Probe(
        "row_selected_title",
        ".urlbarView-row[selected] .urlbarView-title",
        ("color",),
    ),
)

WAIT_READY_JS: Final = """
const done = arguments[arguments.length - 1];
const deadline = Date.now() + arguments[0];
(function poll() {
  const de = document.documentElement;
  const ok = window.gBrowser && window.gZenWorkspaces && window.gZenThemePicker
    && de.hasAttribute("sessionrestored") && !de.hasAttribute("zen-before-loaded");
  if (ok) return done(true);
  if (Date.now() > deadline) return done(false);
  setTimeout(poll, 100);
})();
"""

BUILD_TABS_JS: Final = """
const done = arguments[arguments.length - 1];
const urls = arguments[0];
(async () => {
  const sp = Services.scriptSecurityManager.getSystemPrincipal();
  const add = url => gBrowser.addTab(url, { triggeringPrincipal: sp, skipAnimation: true });
  const notes = [];
  const opened = urls.map(add);
  try { gZenPinnedTabManager.addToEssentials(add("about:robots")); } catch (e) { notes.push("essential: " + e); }
  try { gBrowser.pinTab(add("about:mozilla")); } catch (e) { notes.push("pin: " + e); }
  try {
    await gZenFolders.createFolder([add("data:text/html,<title>Folder%20child</title>x")],
                                   { renameFolder: false, label: "folder" });
  } catch (e) { notes.push("folder: " + e); }
  if (opened.length) gBrowser.selectedTab = opened[opened.length - 1];
  if (opened.length > 1) gBrowser.addToMultiSelectedTabs(opened[opened.length - 2]);
  await new Promise(r => setTimeout(r, 1000));
  return { tabs: gBrowser.tabs.length, notes };
})().then(done, e => done({ error: String(e) }));
"""

PROBE_JS: Final = """
const out = {};
for (const s of arguments[0]) {
  const el = document.querySelector(s.selector);
  const row = { found: !!el, props: {} };
  if (el) {
    const cs = getComputedStyle(el, s.pseudo || null);
    for (const p of s.props) row.props[p] = cs.getPropertyValue(p).replace(/\\s+/g, " ").trim();
  }
  out[s.name] = row;
}
return out;
"""

USER_SHEETS_JS: Final = """
return InspectorUtils.getAllStyleSheets(document, false)
  .map(sh => sh.href || "").filter(h => /\\/chrome\\/user(Chrome|Content)\\.css$/.test(h));
"""

PREFS_JS: Final = """
const out = {};
for (const n of arguments[0]) {
  const t = Services.prefs.getPrefType(n);
  try {
    out[n] = t === 32 ? Services.prefs.getStringPref(n) : t === 64 ? Services.prefs.getIntPref(n)
      : t === 128 ? Services.prefs.getBoolPref(n) : null;
  } catch (e) { out[n] = "error: " + e; }
}
return out;
"""

OPEN_URLBAR_JS: Final = """
const done = arguments[arguments.length - 1];
gURLBar.focus();
gURLBar.search(arguments[0]);
setTimeout(() => done({ open: gURLBar.view.isOpen,
  floating: gURLBar.getAttribute("zen-floating-urlbar") === "true" }), 1200);
"""

CLOSE_URLBAR_JS: Final = "gURLBar.view.close(); gURLBar.blur();"


@dataclass(frozen=True)
class Args:
    out: Path
    width: int
    height: int
    zen: str
    timeout: float
    keep_profile: bool


def parse_args(argv: list[str] | None = None) -> Args:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="PNG of the chrome window")
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--zen", default=DEFAULT_ZEN, help="Zen binary")
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="startup and script timeout, seconds",
    )
    p.add_argument("--keep-profile", action="store_true", help="keep the temp profile")
    a = p.parse_args(argv)
    return Args(
        out=a.out.resolve(),
        width=a.width,
        height=a.height,
        zen=a.zen,
        timeout=a.timeout,
        keep_profile=a.keep_profile,
    )


def pref_line(name: str, value: bool | int | str) -> str:
    return f"user_pref({json.dumps(name)}, {json.dumps(value)});\n"


def make_profile() -> Path:
    prof = Path(tempfile.mkdtemp(prefix="zen-preview-"))
    (prof / "chrome").mkdir()
    for rel in ("user.js", "chrome/userChrome.css"):
        src = SRC_DIR / rel
        if src.is_file():
            (prof / rel).symlink_to(src)
    (prof / "prefs.js").write_text(
        "".join(pref_line(k, v) for k, v in HARNESS_PREFS.items())
    )
    return prof


def zen_pids() -> set[int]:
    r = subprocess.run(
        ["pgrep", "-x", "zen"], capture_output=True, text=True, check=False
    )
    return {int(x) for x in r.stdout.split()}


def wait_port(prof: Path, proc: subprocess.Popen[bytes], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    active = prof / "MarionetteActivePort"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"zen exited early with code {proc.returncode}")
        if active.is_file():
            txt = active.read_text().strip()
            port = int(txt) if txt.isdigit() else 0
            if port:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        return port
                except OSError:
                    pass
        time.sleep(0.2)
    raise TimeoutError("marionette port did not open")


def shoot(m: Any, path: Path) -> None:  # Marionette client is untyped
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(m.screenshot(format="base64")))


def probe(m: Any, probes: tuple[Probe, ...]) -> Any:  # Marionette client is untyped
    return m.execute_script(PROBE_JS, script_args=[[asdict(p) for p in probes]])


def shutdown(m: Any, proc: subprocess.Popen[bytes]) -> None:  # untyped client
    if m is not None and m.session is not None:
        with contextlib.suppress(Exception):  # fall through to wait/terminate/kill
            m._send_message("Marionette:Quit", {"flags": ["eAttemptQuit"]})
        m.delete_session(send_request=False)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run(args: Args) -> int:
    t0 = time.monotonic()
    before = zen_pids()
    prof = make_profile()
    logpath = prof.parent / f"{prof.name}.log"
    log = logpath.open("wb")
    env = dict(os.environ, MOZ_HEADLESS="1", MOZ_CRASHREPORTER_DISABLE="1")
    cmd = [
        args.zen,
        "--headless",
        "--marionette",
        "-remote-allow-system-access",
        "--no-remote",
        "--profile",
        str(prof),
    ]
    meta: dict[str, Any] = {"size": [args.width, args.height]}
    report: dict[str, Any] = {"meta": meta}
    json_out = args.out.with_suffix(".json")
    m: Any = None  # Marionette client, untyped
    proc = subprocess.Popen(
        cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    try:
        port = wait_port(prof, proc, args.timeout)
        m = Marionette(host="127.0.0.1", port=port)
        m.start_session()
        m.set_context("chrome")
        m.timeout.script = args.timeout
        ready = m.execute_async_script(
            WAIT_READY_JS, script_args=[int(args.timeout * 1000)]
        )
        if not ready:
            raise TimeoutError("browser window not ready")
        m.set_window_rect(width=args.width, height=args.height)
        meta["zen_version"] = m.execute_script("return Services.appinfo.version")
        meta["startup_s"] = round(time.monotonic() - t0, 2)
        m.execute_async_script(BUILD_TABS_JS, script_args=[list(TAB_URLS)])
        time.sleep(1)

        report["prefs"] = m.execute_script(PREFS_JS, script_args=[list(REPORTED_PREFS)])
        report["user_sheets"] = m.execute_script(USER_SHEETS_JS)
        report["chrome"] = probe(m, CHROME_PROBES)
        shoot(m, args.out)
        screenshots = [str(args.out)]

        m.execute_async_script(OPEN_URLBAR_JS, script_args=["about:"])
        report["urlbar"] = probe(m, URLBAR_PROBES)
        urlbar_png = args.out.with_name(f"{args.out.stem}.urlbar.png")
        shoot(m, urlbar_png)
        screenshots.append(str(urlbar_png))
        m.execute_script(CLOSE_URLBAR_JS)
        report["screenshots"] = screenshots
        rc = 0
    except Exception as e:  # noqa: BLE001 - always fall through to shutdown
        report["error"] = f"{type(e).__name__}: {e}"
        print(report["error"], file=sys.stderr)
        rc = 1
    finally:
        shutdown(m, proc)
        log.close()
        after = zen_pids()
        meta["exit_code"] = proc.returncode
        meta["foreign_zen_pids_before"] = sorted(before)
        meta["foreign_zen_pids_after"] = sorted(after - {proc.pid})
        meta["own_pid_gone"] = proc.pid not in after
        meta["total_s"] = round(time.monotonic() - t0, 2)
        if not args.keep_profile:
            shutil.rmtree(prof, ignore_errors=True)
            logpath.unlink(missing_ok=True)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=1, default=str))
    if rc == 0:
        print(f"zen {meta['zen_version']}: {args.out} ({meta['total_s']} s)")
    return rc


if __name__ == "__main__":
    sys.exit(run(parse_args()))
