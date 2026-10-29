"""Render the Ayu Ink Obsidian theme headless and dump computed styles.

Reads app.css from the installed Obsidian asar, copies it with the fixture and
the theme into the output dir, and runs plain headless Chrome twice per render:
once for a screenshot, once for the D3 measure JSON. It touches no Obsidian
vault and no running Chrome (each run gets a throwaway profile).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

DEFAULT_CHROME: Final = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC_DIR: Final = Path(__file__).resolve().parent
SYSTEM_ASAR: Final = Path("/Applications/Obsidian.app/Contents/Resources/obsidian.asar")
ASAR_RE: Final = re.compile(r"^obsidian-(\d+(?:\.\d+)*)\.asar$")
OUT_RE: Final = re.compile(r'<pre id="out">(.*?)</pre>', re.DOTALL)


@dataclass(frozen=True)
class Render:
    name: str
    base: int
    width: int
    height: int
    scale: float
    minimal_settings: bool


RENDERS: Final = (
    Render("1440", 16, 1440, 1600, 1.0, False),
    Render("zoom3", 10, 713, 503, 1.728, True),
)


class SetupError(Exception):
    pass


class ChromeError(Exception):
    pass


def asar_read(asar: Path, inner: str) -> bytes:
    with asar.open("rb") as f:
        _, hsize = struct.unpack("<II", f.read(8))
        hdr = f.read(hsize)
        jlen = struct.unpack("<I", hdr[4:8])[0]
        node = cast("dict[str, object]", json.loads(hdr[8 : 8 + jlen]))
        for part in inner.strip("/").split("/"):
            files = node["files"]
            if not isinstance(files, dict):
                raise KeyError(part)
            node = cast("dict[str, object]", files[part])
        if node.get("unpacked"):
            return Path(f"{asar}.unpacked", inner).read_bytes()
        f.seek(8 + hsize + int(cast("str | int", node["offset"])))
        return f.read(int(cast("str | int", node["size"])))


def find_asar() -> Path | None:
    support = Path.home() / "Library" / "Application Support" / "obsidian"
    found: list[tuple[tuple[int, ...], Path]] = []
    if support.is_dir():
        for p in support.iterdir():
            m = ASAR_RE.match(p.name)
            if m:
                found.append((tuple(int(x) for x in m.group(1).split(".")), p))
    if found:
        return max(found)[1]
    return SYSTEM_ASAR if SYSTEM_ASAR.is_file() else None


def chrome_run(chrome: Path, r: Render, extra: list[str], url: str) -> str:
    with tempfile.TemporaryDirectory() as prof:
        cmd = [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--allow-file-access-from-files",
            "--virtual-time-budget=3000",
            f"--user-data-dir={prof}",
            f"--window-size={r.width},{r.height}",
            f"--force-device-scale-factor={r.scale}",
            *extra,
            url,
        ]
        res = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=90
        )
    if res.returncode != 0:
        err = res.stderr.strip().splitlines()
        raise ChromeError(err[0] if err else "no output")
    return res.stdout


def render_one(chrome: Path, out: Path, r: Render) -> list[Path]:
    query = f"base={r.base}&css=theme.css"
    if r.minimal_settings:
        query += "&plugins=minimal-settings"
    base_url = f"file://{out}/fixture.html?{query}"
    png = out / f"shot-{r.name}.png"
    chrome_run(chrome, r, [f"--screenshot={png}"], base_url)
    if not png.is_file():
        raise ChromeError("no output")
    dom = chrome_run(chrome, r, ["--dump-dom"], base_url + "&measure=1")
    m = OUT_RE.search(dom)
    if not m:
        raise ChromeError("no output")
    data = json.loads(html.unescape(m.group(1)))
    js = out / f"computed-{r.name}.json"
    js.write_text(json.dumps(data, indent=1))
    return [png, js]


def run(args: argparse.Namespace) -> int:
    chrome = Path(args.chrome)
    if not chrome.is_file():
        raise SetupError(f"Chrome not found: {chrome} (pass --chrome)")
    asar = Path(args.asar) if args.asar else find_asar()
    if asar is None or not asar.is_file():
        raise SetupError("no Obsidian asar found (pass --asar)")
    theme, fixture = Path(args.theme), Path(args.fixture)
    for p in (theme, fixture):
        if not p.is_file():
            raise SetupError(f"missing {p}")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "app.css").write_bytes(asar_read(asar, "app.css"))
    shutil.copyfile(fixture, out / "fixture.html")
    shutil.copyfile(theme, out / "theme.css")
    for r in RENDERS:
        try:
            paths = render_one(chrome, out, r)
        except (ChromeError, subprocess.TimeoutExpired, ValueError) as e:
            first = str(e).splitlines()[0] if str(e) else "no output"
            raise ChromeError(f"chrome failed for {r.name}: {first}") from e
        for p in paths:
            print(p)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--asar", help="obsidian.asar (default: newest installed)")
    ap.add_argument("--theme", default=str(SRC_DIR / "Ayu Ink" / "theme.css"))
    ap.add_argument("--fixture", default=str(SRC_DIR / "fixture.html"))
    ap.add_argument("--chrome", default=DEFAULT_CHROME)
    args = ap.parse_args()
    try:
        return run(args)
    except SetupError as e:
        print(f"preview: {e}", file=sys.stderr)
        return 2
    except ChromeError as e:
        print(f"preview: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
