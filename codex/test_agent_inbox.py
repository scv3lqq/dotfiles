"""Agent inbox: report recording in the pane hook, popup list and status script.

The hook runs against a real tmux server on an isolated socket, the inbox script
against a recording tmux stub. Synthetic panes, closed environment.
"""

from __future__ import annotations

import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "claude/hooks/pane-state.sh"
INBOX = ROOT / "tmux/agent-inbox.sh"
NOW = 2_000_000_000
# What the hook asks tmux to learn whether its pane is in front of an attached client
FRONT_FORMAT = "#{pane_active}#{window_active}#{?session_attached,1,0}"
# D5: the columns of `tmux list-panes -a -F`, in the order of the stub rows
COLUMNS = (
    "#{session_id}", "#{window_id}", "#{pane_id}", "#{pane_active}", "#{window_active}",
    "#{session_attached}", "#{pane_current_command}",
    "#{?#{==:#{pane_title},#{host}},,#{pane_title}}", "#{pane_current_path}",
    "#{@claude_state}", "#{@claude_since}", "#{window_activity}", "#{@agent_unseen}",
    "#{@agent_failed}", "#{@claude_agents}",
)
# D2: the window marks
ALERT = " #[fg=#F07178]!"
ACCENT = " #[fg=#E6B450]●"

# Hook cases: the front check answers from the file `front` (000 when absent), every
# other call reaches the real server on the isolated socket
HOOK_TMUX = f'''
import os
args = sys.argv[1:]
if {FRONT_FORMAT!r} in args:
    front = Path(os.environ["FIXTURE_ROOT"]) / "front"
    print(front.read_text() if front.exists() else "000")
else:
    real = os.environ["FIXTURE_TMUX"]
    os.execv(real, [real, "-L", os.environ["FIXTURE_SOCKET"], "-f", "/dev/null", *args])
'''

# Inbox cases: serves the files `rows` and `windows`, records every call as JSON
INBOX_TMUX = '''
import os
args = sys.argv[1:]
root = Path(os.environ["FIXTURE_ROOT"])
with open(root / "calls.log", "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[0] == "list-panes":
    print((root / "rows").read_text(), end="")
elif args[0] == "list-windows":
    print((root / "windows").read_text(), end="")
elif args[0] in ("display-message", "display"):
    print("fixture:0.0  /work/demo")
'''


def strip(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;:]*[A-Za-z]", "", text)


@dataclass(frozen=True)
class Pane:
    """One `tmux list-panes -a` row.

    `front` holds pane_active, window_active and session_attached as three digits;
    111 is the pane in front of an attached client.
    """

    pane_id: str
    command: str = "codex"
    state: str = ""
    since: int = NOW - 30
    activity: int = NOW - 600
    unseen: str = ""
    failed: str = ""
    title: str = ""
    path: str = "/work/demo"
    window: str = "@1"
    front: str = "000"

    def line(self) -> str:
        fields = ("$1", self.window, self.pane_id, *self.front, self.command, self.title, self.path,
                  self.state, str(self.since), str(self.activity), self.unseen, self.failed, "")
        return "\t".join(fields)


def mixed() -> tuple[Pane, ...]:
    """Every class and every ignored kind, worst first: only the sort can order them."""
    return (
        Pane("%8", command="zsh", state="waiting"),
        Pane("%7", state="", activity=NOW),
        Pane("%6", state="done"),
        Pane("%5", state="working", activity=NOW - 6),
        Pane("%4", state="working", activity=NOW),
        Pane("%3", state="done", unseen="1"),
        Pane("%2", command="2.1.0", state="done", unseen="1", failed="1"),
        Pane("%1", command="claude", state="waiting"),
    )


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.reports = self.home / "state" / "agent-inbox"
        self.env = {
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.home / "state"),
            # A closed PATH keeps fixtures away from the live tmux; Homebrew supplies jq
            "PATH": f"{self.bin}:/opt/homebrew/bin:/usr/bin:/bin",
            "FIXTURE_ROOT": str(self.root),
            "LC_ALL": "en_US.UTF-8",
        }
        self.set_now(NOW)

    def stub(self, name: str, source: str) -> None:
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n{source}\n")
        path.chmod(0o755)

    def set_now(self, epoch: int) -> None:
        self.stub("date", f"print({epoch})")

    def run_script(self, script: Path, *args: str,
                   payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["/bin/bash", str(script), *args],
            input=json.dumps(payload) if payload is not None else "", text=True, encoding="utf-8",
            capture_output=True, check=False, env=self.env, cwd=self.home, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result


class HookTests(Fixture):
    def setUp(self) -> None:
        super().setUp()
        binary = shutil.which("tmux")
        jq = shutil.which("jq")
        self.assertIsNotNone(binary, "tmux is required for hook fixtures")
        self.assertIsNotNone(jq, "jq is required for hook fixtures")
        (self.bin / "jq").symlink_to(str(jq))
        socket = f"inbox-fixture-{uuid.uuid4().hex}"
        self.server = [str(binary), "-L", socket, "-f", "/dev/null"]
        self.socket_path: Path | None = None
        self.addCleanup(self.stop_server)
        self.tmux("new-session", "-d", "-s", "fixture", "-x", "80", "-y", "24", "/bin/sleep 300")
        self.socket_path = Path(self.tmux("display-message", "-p", "-t", "fixture", "#{socket_path}").strip())
        self.pane = self.tmux("display-message", "-p", "-t", "fixture", "#{pane_id}").strip()
        self.digits = self.pane.lstrip("%")
        self.env.update(TMUX_PANE=self.pane, FIXTURE_TMUX=str(binary), FIXTURE_SOCKET=socket)
        self.stub("tmux", HOOK_TMUX)

    def stop_server(self) -> None:
        subprocess.run([*self.server, "kill-server"], env=self.env, capture_output=True, timeout=10, check=False)
        # kill-server leaves the socket file behind
        if self.socket_path is not None:
            self.socket_path.unlink(missing_ok=True)

    def tmux(self, *args: str) -> str:
        return subprocess.run([*self.server, *args], text=True, encoding="utf-8", capture_output=True,
                              env=self.env, timeout=10, check=True).stdout

    def options(self) -> dict[str, str]:
        """Options set on the pane right now: a name missing from the map is unset."""
        listing = self.tmux("show-options", "-p", "-t", self.pane)
        names = [line.split(" ", 1)[0] for line in listing.splitlines()]
        return {name: self.tmux("show-options", "-p", "-v", "-t", self.pane, name).rstrip("\n") for name in names}

    def stored(self) -> list[str]:
        """Names of the files in the D3 report directory."""
        return sorted(path.name for path in self.reports.glob("*"))

    def set_front(self, flags: str) -> None:
        (self.root / "front").write_text(flags)

    def hook(self, event: str, **fields: object) -> None:
        result = self.run_script(HOOK, payload={"hook_event_name": event, **fields})
        self.assertEqual(result.stdout, "")

    def test_h1_stop_unseen(self) -> None:
        self.hook("Stop", last_assistant_message="final text")
        options = self.options()
        self.assertEqual(options.get("@agent_unseen"), "1")
        self.assertNotIn("@agent_failed", options)
        self.assertIn("@agent_report", options)
        report = Path(options["@agent_report"])
        self.assertEqual(report, self.reports / f"{self.digits}-2000000000.txt")
        self.assertEqual(report.read_text(), "final text")
        self.assertEqual(self.stored(), [f"{self.digits}-2000000000.txt"])
        # D3: umask 077, the text of a turn can hold anything
        self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.reports.stat().st_mode), 0o700)

    def test_h2_stop_front(self) -> None:
        self.set_front("111")
        self.hook("Stop", last_assistant_message="final text")
        options = self.options()
        self.assertNotIn("@agent_unseen", options)
        self.assertIn("@agent_report", options)
        self.assertEqual(Path(options["@agent_report"]).read_text(), "final text")

    def test_h3_failure(self) -> None:
        self.hook("StopFailure", error="rate_limit")
        options = self.options()
        self.assertEqual(options.get("@agent_failed"), "1")
        self.assertEqual(options.get("@agent_unseen"), "1")
        self.assertIn("@agent_report", options)
        self.assertEqual(Path(options["@agent_report"]).read_text(), "rate_limit")

    def test_h4_prompt_clears(self) -> None:
        self.hook("Stop", last_assistant_message="final text")
        self.assertEqual(self.options().get("@agent_unseen"), "1")
        self.hook("UserPromptSubmit")
        options = self.options()
        self.assertNotIn("@agent_unseen", options)
        self.assertEqual(options.get("@claude_state"), "working")

    def test_h5_background(self) -> None:
        self.hook("Stop", background_tasks=[{"type": "subagent"}], last_assistant_message="final text")
        options = self.options()
        self.assertEqual(options.get("@claude_state"), "agents")
        self.assertNotIn("@agent_unseen", options)
        self.assertEqual(self.stored(), [])

    def test_h6_session_end(self) -> None:
        self.hook("Stop", last_assistant_message="final text")
        self.assertEqual(self.stored(), [f"{self.digits}-2000000000.txt"])
        self.hook("SessionEnd", reason="other")
        self.assertNotIn("@agent_report", self.options())
        self.assertEqual(self.stored(), [])

    def test_h7_replace(self) -> None:
        self.hook("Stop", last_assistant_message="first text")
        self.assertEqual(self.stored(), [f"{self.digits}-2000000000.txt"])
        self.set_now(NOW + 1)
        self.hook("Stop", last_assistant_message="second text")
        self.assertEqual(self.stored(), [f"{self.digits}-2000000001.txt"])
        options = self.options()
        self.assertEqual(options.get("@agent_report"), str(self.reports / f"{self.digits}-2000000001.txt"))
        self.assertEqual(Path(options["@agent_report"]).read_text(), "second text")

    def test_h8_empty_message(self) -> None:
        self.hook("Stop")
        options = self.options()
        self.assertEqual(options.get("@agent_unseen"), "1")
        self.assertNotIn("@agent_report", options)
        self.assertEqual(self.stored(), [])

    def test_h9_empty_stop_drops_old_report(self) -> None:
        self.hook("Stop", last_assistant_message="final text")
        self.assertEqual(self.stored(), [f"{self.digits}-2000000000.txt"])
        # Another second: with the same name the empty write would truncate the old file by itself
        self.set_now(NOW + 1)
        self.hook("Stop")
        self.assertNotIn("@agent_report", self.options())
        self.assertEqual(self.stored(), [])

    def test_h10_stop_subagent(self) -> None:
        self.hook("Stop", agent_id="agent-1", last_assistant_message="final text")
        self.assertNotIn("@agent_unseen", self.options())
        self.assertEqual(self.stored(), [])


class InboxTests(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.log = self.root / "calls.log"
        self.rows = self.root / "rows"
        self.windows = self.root / "windows"
        self.rows.write_text("")
        self.windows.write_text("")
        self.stub("tmux", INBOX_TMUX)

    def panes(self, *panes: Pane) -> None:
        self.rows.write_text("".join(pane.line() + "\n" for pane in panes))

    def set_windows(self, marks: dict[str, str]) -> None:
        self.windows.write_text("".join(f"{window}\t{mark}\n" for window, mark in marks.items()))

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        records: list[list[str]] = [json.loads(line) for line in self.log.read_text().splitlines()]
        return records

    def reset_calls(self) -> None:
        self.log.write_text("")

    def commands(self) -> list[list[str]]:
        """Recorded tmux commands in order: one call can chain several with `;`."""
        commands: list[list[str]] = []
        for call in self.calls():
            command: list[str] = []
            for word in call:
                if word == ";":
                    commands.append(command)
                    command = []
                else:
                    command.append(word)
            commands.append(command)
        return commands

    def position(self, command: list[str]) -> int:
        """Index of `command` among the recorded commands."""
        commands = self.commands()
        if command not in commands:
            self.fail(f"no command {command}: {commands}")
        return commands.index(command)

    def mark_calls(self) -> list[list[str]]:
        return [command for command in self.commands() if command[:2] in (["set", "-w"], ["set", "-wu"])]

    def render(self) -> list[list[str]]:
        """Rows of `render` as session, pane, class (up:down for a header), display; colors stripped."""
        output = strip(self.run_script(INBOX, "render").stdout)
        return [line.split("\t", 3) for line in output.splitlines()]

    def status(self) -> str:
        return self.run_script(INBOX, "status").stdout

    def test_r1_order(self) -> None:
        self.panes(*mixed())
        rows = self.render()
        agents = [row for row in rows if row[1]]
        self.assertEqual([row[1] for row in agents], ["%1", "%2", "%3", "%4"])
        self.assertEqual([row[2] for row in agents], ["blocked", "failed", "ready", "working"])
        self.assertEqual(rows[0][3], "needs you 3")
        self.assertEqual(rows[4][2:], ["4:6", "working 1"])
        # The last line starts with two tabs: no session, no pane
        self.assertEqual(rows[-1][:2], ["", ""])
        self.assertEqual(rows[-1][3], "show seen 1")
        # The stub rows follow D5, so the script has to ask for the same columns
        asked = [call for call in self.calls() if call[:1] == ["list-panes"]]
        self.assertEqual(len(asked), 1)
        self.assertEqual(asked[0][:3], ["list-panes", "-a", "-F"])
        self.assertEqual(asked[0][3].rstrip("\t").split("\t"), list(COLUMNS))

    def test_r2_seen_shown(self) -> None:
        popup = self.root / "popup"
        popup.mkdir()
        (popup / "show-seen").write_text("")
        self.env["AGENT_INBOX_STATE"] = str(popup)
        self.panes(*mixed())
        rows = self.render()
        self.assertEqual(rows[-1][1:3], ["%6", "seen"])
        self.assertEqual(rows[-2][3], "hide seen 1")

    def test_r3_empty_needs(self) -> None:
        self.panes(Pane("%1", state="working", activity=NOW))
        rows = self.render()
        self.assertEqual(rows[1][3], "nothing to open")
        self.assertEqual(rows[0][2], "4:4")

    def test_r4_display(self) -> None:
        self.panes(Pane("%1", command="2.1.0", state="done", unseen="1", since=NOW - 120,
                        title="Fix bar", path="/x/dotfiles"))
        agents = [row for row in self.render() if row[1] == "%1"]
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0][3], "●  2m cc dotfiles       Fix bar")

    def test_r5_tie(self) -> None:
        self.panes(Pane("%1", state="done", unseen="1", since=NOW - 20),
                   Pane("%2", state="done", unseen="1", since=NOW - 10))
        self.assertEqual([row[1] for row in self.render() if row[1]], ["%2", "%1"])

    def test_r6_agents(self) -> None:
        self.panes(Pane("%1", state="agents", activity=NOW))
        self.assertEqual([row[1:3] for row in self.render() if row[1]], [["%1", "working"]])

    def test_s1_segment(self) -> None:
        self.panes(
            Pane("%1", state="waiting", window="@1"),
            Pane("%2", state="done", unseen="1", failed="1", window="@2"),
            Pane("%3", state="done", unseen="1", window="@3"),
            Pane("%4", state="working", activity=NOW, window="@4"),
        )
        self.assertEqual(
            self.status().splitlines(),
            ["#[fg=#F07178,bold]! 2#[nobold]  #[fg=#E6B450,bold]● 1#[nobold]  #[fg=#7A8290]◌ 1"],
        )

    def test_s2_zero(self) -> None:
        cases = (
            ("no panes", ()),
            ("only seen, idle and foreign", (Pane("%1", state="done"), Pane("%2", state=""),
                                              Pane("%3", command="zsh", state="waiting"))),
        )
        for name, panes in cases:
            with self.subTest(panes=name):
                self.panes(*panes)
                self.assertEqual(self.status(), "")

    def test_s3_front(self) -> None:
        self.panes(Pane("%3", state="done", unseen="1", front="111"))
        self.assertEqual(self.status(), "")
        self.assertIn(["set", "-pu", "-t", "%3", "@agent_unseen"], self.commands())

    def test_s4_mark_priority(self) -> None:
        self.panes(Pane("%1", state="done", unseen="1"), Pane("%2", state="waiting"))
        self.set_windows({"@1": ""})
        self.status()
        self.assertEqual(self.mark_calls(), [["set", "-w", "-t", "@1", "@agent_mark", " #[fg=#F07178]!"]])

    def test_s5_mark_same(self) -> None:
        self.panes(Pane("%1", state="done", unseen="1"))
        self.set_windows({"@1": ACCENT})
        # The segment shows the pane was seen as ready: no call is not a crash
        self.assertEqual(self.status().splitlines(), ["#[fg=#E6B450,bold]● 1#[nobold]"])
        self.assertEqual(self.mark_calls(), [])

    def test_s6_mark_clear(self) -> None:
        self.set_windows({"@1": ACCENT})
        self.assertEqual(self.status(), "")
        self.assertEqual(self.mark_calls(), [["set", "-wu", "-t", "@1", "@agent_mark"]])

    def test_s7_front_partial(self) -> None:
        for zero, front in (("pane_active", "011"), ("window_active", "101"), ("session_attached", "110")):
            with self.subTest(zero=zero):
                self.reset_calls()
                self.panes(Pane("%3", state="done", unseen="1", front=front))
                self.assertEqual(self.status().splitlines(), ["#[fg=#E6B450,bold]● 1#[nobold]"])
                self.assertEqual([command for command in self.commands() if command[:2] == ["set", "-pu"]], [])

    def test_s8_front_failed(self) -> None:
        self.panes(Pane("%3", state="done", unseen="1", failed="1", front="111"))
        self.assertEqual(self.status(), "")
        self.assertIn(["set", "-pu", "-t", "%3", "@agent_unseen"], self.commands())

    def test_s9_mark_failed(self) -> None:
        self.panes(Pane("%1", state="done", unseen="1", failed="1"))
        self.set_windows({"@1": ""})
        self.status()
        self.assertEqual(self.mark_calls(), [["set", "-w", "-t", "@1", "@agent_mark", " #[fg=#F07178]!"]])

    def test_s10_front_silent_working(self) -> None:
        # Once cleared the pane is idle and leaves the list; the clear must not leave with it
        self.panes(Pane("%3", state="working", unseen="1", activity=NOW - 100, front="111"))
        self.assertEqual(self.status(), "")
        self.assertIn(["set", "-pu", "-t", "%3", "@agent_unseen"], self.commands())

    def test_o1_open(self) -> None:
        self.run_script(INBOX, "open", "$1", "%3")
        seen = self.position(["set", "-pu", "-t", "%3", "@agent_unseen"])
        jump = self.position(["select-window", "-t", "%3"])
        self.assertLess(seen, jump)

    def test_o2_seen_guard(self) -> None:
        self.run_script(INBOX, "seen", "abc")
        self.assertEqual(self.calls(), [])

    def test_o3_open_jump(self) -> None:
        self.run_script(INBOX, "open", "$1", "%3")
        commands = self.commands()
        self.assertIn(["select-pane", "-t", "%3"], commands)
        self.assertIn(["switch-client", "-t", "$1"], commands)


if __name__ == "__main__":
    unittest.main()
