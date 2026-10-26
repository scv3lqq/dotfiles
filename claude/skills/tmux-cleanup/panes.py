"""List tmux panes by real last activity; optionally kill the stale ones.

Claude panes redraw their TUI constantly, so window_activity is always fresh,
and transcript mtime moves on metadata appends. The last user/assistant/system
timestamp in the transcript is the only honest signal.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime

HOME = os.path.expanduser("~")
FMT = "\t".join(
    [
        "#{pane_id}",
        "#{session_name}:#{window_index}.#{pane_index}",
        "#{session_name}",
        "#{pane_pid}",
        "#{pane_current_command}",
        "#{window_activity}",
        "#{@claude_state}",
        "#{pane_current_path}",
    ]
)


@dataclass
class Pane:
    pane_id: str
    target: str
    session: str
    kind: str
    last: float | None
    mem_mb: int
    claude_pids: list[int]
    session_id: str
    status: str
    path: str
    note: str


def process_tree() -> tuple[dict[int, list[int]], dict[int, int]]:
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
    children: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    for line in out.splitlines():
        pid, ppid, r = (int(x) for x in line.split()[:3])
        children.setdefault(ppid, []).append(pid)
        rss[pid] = r
    return children, rss


def descendants(pid: int, children: dict[int, list[int]]) -> list[int]:
    out = [pid]
    for c in children.get(pid, []):
        out += descendants(c, children)
    return out


def load_sessions() -> dict[int, dict[str, object]]:
    sessions: dict[int, dict[str, object]] = {}
    for f in glob.glob(f"{HOME}/.claude/sessions/*.json"):
        try:
            with open(f) as fh:
                d = json.load(fh)
            sessions[int(d["pid"])] = d
        except (OSError, ValueError, KeyError):
            continue
    return sessions


def last_message(session_id: str) -> float | None:
    stamps: list[float] = []
    for t in glob.glob(f"{HOME}/.claude/projects/*/{session_id}.jsonl"):
        with open(t, "rb") as fh:
            fh.seek(max(0, os.path.getsize(t) - 2_000_000))
            tail = fh.read().decode("utf-8", "replace").splitlines()
        for line in tail:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if e.get("type") in ("user", "assistant", "system") and isinstance(ts, str):
                stamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
    return max(stamps) if stamps else None


def unsaved_editor(pane_id: str) -> bool:
    screen = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", pane_id], capture_output=True, text=True
    ).stdout.splitlines()
    return any("[+]" in line for line in screen[-3:])


def collect() -> list[Pane]:
    children, rss = process_tree()
    sessions = load_sessions()
    out = subprocess.run(["tmux", "list-panes", "-a", "-F", FMT], capture_output=True, text=True).stdout
    panes: list[Pane] = []
    for line in out.splitlines():
        pane_id, target, session, ppid, cmd, wact, state, path = line.split("\t")
        procs = descendants(int(ppid), children)
        mem = sum(rss.get(p, 0) for p in procs) // 1024
        claude = [p for p in procs if p in sessions]
        note = state
        if claude:
            sess = sessions[claude[0]]
            sid = str(sess["sessionId"])
            last = last_message(sid)
            su = sess.get("statusUpdatedAt")
            if isinstance(su, (int, float)):
                last = max(last or 0.0, su / 1000)
            kind, status = "claude", str(sess.get("status", ""))
        else:
            sid, status = "-", ""
            last = float(wact) if wact else None
            kind = cmd
            if cmd in ("nvim", "vim") and unsaved_editor(pane_id):
                note = "UNSAVED?"
        panes.append(Pane(pane_id, target, session, kind, last, mem, claude, sid, status, path, note))
    return panes


def age(now: float, ts: float | None) -> str:
    if ts is None:
        return "?"
    m = int((now - ts) / 60)
    return f"{m // 60}h{m % 60:02d}m"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--kill", metavar="TSV", help="kill stale panes, record them to TSV")
    args = ap.parse_args()

    now = time.time()
    me = os.environ.get("TMUX_PANE", "")
    panes = collect()
    stale = [
        p for p in panes if p.pane_id != me and p.last is not None and now - p.last > args.hours * 3600
    ]
    stale_ids = {p.pane_id for p in stale}

    if not args.kill:
        for p in panes:
            mark = "KILL" if p.pane_id in stale_ids else "keep"
            print(
                f"{mark} {p.pane_id:>5} {p.target:<26} {p.kind:<8} {p.mem_mb:>5}M "
                f"last={age(now, p.last):>8} {p.status or '-':<8} {p.note or '-':<8} "
                f"{p.path.replace(HOME, '~')}"
            )
        by_session: dict[str, list[bool]] = {}
        for p in panes:
            by_session.setdefault(p.session, []).append(p.pane_id in stale_ids)
        whole = [s for s, flags in by_session.items() if all(flags)]
        unsaved = [p.target for p in stale if p.note == "UNSAVED?"]
        unknown = [p.target for p in panes if p.last is None]
        print(f"\nstale {len(stale)} of {len(panes)} panes, {sum(p.mem_mb for p in stale)}M RSS")
        print(f"sessions closed whole: {', '.join(whole) or '-'}")
        print(f"unsaved editors among stale: {', '.join(unsaved) or '-'}")
        print(f"unknown activity (never killed): {', '.join(unknown) or '-'}")
        return 0

    with open(args.kill, "w") as fh:
        for p in stale:
            fh.write(f"{p.pane_id}\t{p.target}\t{p.session_id}\t{p.path}\n")
    failed = [
        p.pane_id
        for p in stale
        if subprocess.run(["tmux", "kill-pane", "-t", p.pane_id], capture_output=True).returncode
    ]
    time.sleep(1)
    alive = []
    for p in stale:
        for pid in p.claude_pids:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except ProcessLookupError:
                pass
    print(f"killed {len(stale) - len(failed)} of {len(stale)}; failed: {failed or '-'}; claude alive: {alive or '-'}")
    print(f"resume list: {args.kill}")
    return 1 if failed or alive else 0


if __name__ == "__main__":
    sys.exit(main())
