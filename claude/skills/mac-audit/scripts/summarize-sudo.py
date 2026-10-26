"""Compact summary of sudo-checks.zsh output. Usage: summarize-sudo.py <out_dir>"""

import re
import sys
from collections import Counter
from pathlib import Path

SMALL = (
    "root_crontab",
    "cron_tabs",
    "profiles",
    "remote",
    "root_loginwindow",
    "root_home",
    "root_rc",
    "helpers_sig",
)
# Files every process maps or that macOS rotates on its own; deleted copies are noise.
DELETED_NOISE = re.compile(
    r"plist-cache|\.csstore|iconservices|/Caches/|/T/|/Trial/|/Biome/|CoreSpotlight|Suggestions|analyticsd"
)


def btm(path: Path) -> None:
    print("## Background items (sfltool dumpbtm), non-Apple")
    items = re.split(r"\n\s*#\d+:\n", path.read_text(errors="replace"))
    seen: set[tuple[str, str, str]] = set()
    for item in items[1:]:
        d: dict[str, str] = {}
        for line in item.splitlines():
            m = re.match(r"\s*([A-Za-z. ]+):\s(.*)$", line)
            if m:
                d.setdefault(m.group(1).strip(), m.group(2).strip())
        typ = d.get("Type", "").split(" (")[0]
        if typ == "developer":
            continue
        target = d.get("Executable Path") or d.get("URL", "")
        key = (d.get("Name", ""), typ, target)
        if key in seen:
            continue
        seen.add(key)
        disp = d.get("Disposition", "").split("]")[0].strip("[ ")
        ident = d.get("Identifier", "")
        print(
            f"{typ:13} | {key[0][:34]:34} | {d.get('Team Identifier', '')[:10]:10} | {disp[:26]:26} | {ident[:40]:40} | {target[:90]}"
        )


def powermetrics(path: Path) -> None:
    print("\n## powermetrics: top tasks per sample (CPU ms/s, GPU ms/s)")
    sample = 0
    rows: list[str] = []
    row = re.compile(
        r"^(\S.*?)\s+(-?\d+)\s+([\d.]+)\s+[\d.]+\s.*?([\d.]+)\s+([\d.]+)\s*$"
    )
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("Name ") and " ID " in line:
            sample += 1
            rows = []
            continue
        if (
            sample
            and (m := row.match(line))
            and m.group(1) not in ("ALL_TASKS", "DEAD_TASKS")
        ):
            rows.append(
                f"  {m.group(1)[:30]:30} pid {m.group(2):>6} cpu {float(m.group(3)):8.1f} gpu {float(m.group(4)):7.1f}"
            )
            if len(rows) == 10:
                print(f"sample {sample}:", *rows, sep="\n")
        if re.match(r"GPU (HW )?active residency|^CPU Power|^GPU Power", line):
            print(" ", line.strip())


def sockets(path: Path) -> None:
    print("\n## sockets, all users")
    listen: set[str] = set()
    est: Counter[str] = Counter()
    remotes: Counter[str] = Counter()
    for line in path.read_text(errors="replace").splitlines()[1:]:
        f = line.split()
        if len(f) < 9:
            continue
        if "(LISTEN)" in line:
            listen.add(f"{f[0]} {f[2]} {f[8]}")
        elif "(ESTABLISHED)" in line and "->" in f[8]:
            remote = f[8].split("->")[1]
            host, _, port = remote.rpartition(":")
            est[f"{f[0]} {f[2]} :{port}"] += 1
            if not re.match(r"(127\.|\[::1\]|\[fe80|localhost)", host):
                remotes[f"{host} ({f[0]})"] += 1
    print("LISTEN:", *sorted(listen), sep="\n  ")
    print(
        "ESTABLISHED (proc user :remote_port):",
        *(f"{n:4} {k}" for k, n in est.most_common(25)),
        sep="\n  ",
    )
    print(
        "non-loopback remotes:",
        *(f"{n:4} {k}" for k, n in remotes.most_common(25)),
        sep="\n  ",
    )


def deleted(path: Path) -> None:
    print("\n## deleted-but-running executables (lsof +L1, FD txt)")
    seen: set[str] = set()
    for line in path.read_text(errors="replace").splitlines()[1:]:
        f = line.split(None, 9)
        if len(f) == 10 and f[3] == "txt" and not DELETED_NOISE.search(f[9]):
            key = f"{f[0]} {f[2]} {f[9]}"
            if key not in seen:
                seen.add(key)
                print(" ", key)


def main() -> int:
    out = Path(sys.argv[1])
    for name, fn in (
        ("btm", btm),
        ("powermetrics", powermetrics),
        ("lsof_all", sockets),
        ("lsof_deleted", deleted),
    ):
        p = out / f"{name}.txt"
        if p.exists():
            fn(p)
    sudoers = out / "sudoers.txt"
    if sudoers.exists():
        rules = [
            line
            for line in sudoers.read_text().splitlines()
            if line.strip()
            and not line.startswith("#")
            and not line.startswith("Defaults")
        ]
        print("\n## sudoers rules:", *rules, sep="\n  ")
    for name in SMALL:
        p = out / f"{name}.txt"
        if p.exists():
            print(f"\n## {name}\n{p.read_text(errors='replace').strip()[:2000]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
