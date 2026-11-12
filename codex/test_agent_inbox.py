"""Agent inbox: report recording in the pane hook, popup list and status script.

The hook runs against a real tmux server on an isolated socket, the inbox script
against a recording tmux stub. Synthetic panes, closed environment.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "fixture_code_cache", Path(__file__).resolve().parent.parent / "claude/hooks/tests/fixture_code_cache.py")
assert _spec and _spec.loader
_cache_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cache_module)
cached_executable = _cache_module.cached_executable

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "claude/hooks/pane-state.sh"
INBOX = ROOT / "tmux/agent-inbox.sh"
NOW = 2_000_000_000
# What the hook asks tmux to learn whether its pane is in front of an attached client
FRONT_FORMAT = "#{pane_active}#{window_active}#{?session_attached,1,0}"
# What the hook asks tmux to learn the process of its pane (G1, origin)
PANE_PID_FORMAT = "#{pane_pid}"
# What a Stop of the pane itself sets: a foreign process must leave all of it unset
STOP_OPTIONS = ("@agent_unseen", "@claude_state", "@claude_since", "@agent_report")
# D5 and V3: the columns of `tmux list-panes -a -F`, in the order of the stub rows
COLUMNS = (
    "#{session_id}", "#{window_id}", "#{pane_id}", "#{pane_active}", "#{window_active}",
    "#{session_attached}", "#{pane_current_command}",
    "#{?#{==:#{pane_title},#{host}},,#{pane_title}}", "#{pane_current_path}",
    "#{@claude_state}", "#{@claude_since}", "#{window_activity}", "#{@agent_unseen}",
    "#{@agent_failed}", "#{@claude_agents}", "#{pane_pid}",
)
# D2: the window marks
ALERT = " #[fg=#F07178]!"
ACCENT = " #[fg=#E6B450]●"

# Hook cases: the front check answers from the file `front` (000 when absent), the pane
# process from the file `pane_pid` when it exists (an empty file is a failed lookup),
# every other call reaches the real server on the isolated socket
HOOK_TMUX = f'''#!/bin/bash
for arg in "$@"; do
  if [ "$arg" = {FRONT_FORMAT!r} ]; then
    if [ -f "$FIXTURE_ROOT/front" ]; then cat "$FIXTURE_ROOT/front"; else printf 000; fi
    printf "\\n"
    exit 0
  fi
done
for arg in "$@"; do
  if [ "$arg" = {PANE_PID_FORMAT!r} ] && [ -f "$FIXTURE_ROOT/pane_pid" ]; then
    [ -s "$FIXTURE_ROOT/pane_pid" ] || exit 1
    cat "$FIXTURE_ROOT/pane_pid"
    printf "\\n"
    exit 0
  fi
done
exec "$FIXTURE_TMUX" "$FIXTURE_TMUX_FLAG" "$FIXTURE_SOCKET" -f /dev/null "$@"
'''

# Hook cases: the `ps` of the origin guard answers from the file `chain`, a JSON object of pid
# to parent pid, right-aligned like BSD ps, and fails for a pid the chain does not name
HOOK_PS = '''
import os
if len(sys.argv) != 5 or sys.argv[1:4] != ["-o", "ppid=", "-p"]:
    sys.exit(2)
chain = Path(os.environ["FIXTURE_ROOT"]) / "chain"
answers = json.loads(chain.read_text()) if chain.exists() else {}
if sys.argv[4] not in answers:
    sys.exit(1)
print(answers[sys.argv[4]].rjust(8))
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

# Inbox cases: the process snapshot of V1. Every call is recorded in `ps.log` (not in
# `calls.log`, which holds tmux alone), any other argv fails, the file `procs` is the
# answer and its absence makes ps fail
INBOX_PS = '''
import os
root = Path(os.environ["FIXTURE_ROOT"])
with open(root / "ps.log", "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:] != ["-A", "-o", "pid=,ppid=,comm="]:
    sys.exit(2)
procs = root / "procs"
if not procs.exists():
    sys.exit(1)
print(procs.read_text(), end="")
'''


def strip(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;:]*[A-Za-z]", "", text)


@dataclass(frozen=True)
class Pane:
    """One `tmux list-panes -a` row.

    `front` holds pane_active, window_active and session_attached as three digits;
    111 is the pane in front of an attached client. `since` None leaves @claude_since
    empty, as on a pane without hook state; `pid` is pane_pid (0 is in no process table).
    """

    pane_id: str
    command: str = "codex"
    state: str = ""
    since: int | None = NOW - 30
    activity: int = NOW - 600
    unseen: str = ""
    failed: str = ""
    title: str = ""
    path: str = "/work/demo"
    window: str = "@1"
    front: str = "000"
    pid: int = 0

    def line(self) -> str:
        since = "" if self.since is None else str(self.since)
        fields = ("$1", self.window, self.pane_id, *self.front, self.command, self.title, self.path,
                  self.state, since, str(self.activity), self.unseen, self.failed, "", str(self.pid))
        return "\t".join(fields)


def mixed() -> tuple[Pane, ...]:
    """Every class and every ignored kind, worst first: only the sort can order them."""
    return (
        Pane("%8", command="zsh", state="waiting"),
        Pane("%7", state=""),
        Pane("%6", state="done"),
        Pane("%5", state="working", activity=NOW - 6),
        Pane("%4", state="working", activity=NOW),
        Pane("%3", state="done", unseen="1"),
        Pane("%2", command="2.1.0", state="done", unseen="1", failed="1"),
        Pane("%1", command="claude", state="waiting"),
    )


class Fixture(unittest.TestCase):
    fixture_code_dir: Path
    fixture_code_lock: threading.Lock

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.fixture_code_dir = Path(temporary.name)
        cls.fixture_code_lock = threading.Lock()

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
            "SHELL": "/bin/sh",
            "ZDOTDIR": str(self.home),
            "XDG_STATE_HOME": str(self.home / "state"),
            # A closed PATH keeps fixtures away from the live tmux; Homebrew supplies jq
            "PATH": f"{self.bin}:/opt/homebrew/bin:/usr/bin:/bin",
            "FIXTURE_ROOT": str(self.root),
            "LC_ALL": "en_US.UTF-8",
        }
        self.set_now(NOW)

    def fixture_file(self, name: str, content: str, *, shared: bool) -> None:
        path = self.bin / name
        if path.is_symlink():
            path.unlink()
        if shared and not path.exists():
            digest = hashlib.sha256(content.encode()).hexdigest()
            template = self.fixture_code_dir / digest
            with self.fixture_code_lock:
                if not template.exists():
                    os.link(cached_executable(content), template)
            path.symlink_to(template)
        else:
            path.write_text(content)
            path.chmod(0o755)

    def stub(self, name: str, source: str) -> None:
        content = f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n{source}\n"
        if source == INBOX_PS:
            non_ascii = shlex.quote("[^ -~]")
            record = shlex.quote('["-A", "-o", "pid=,ppid=,comm="]')
            python = shlex.quote(sys.executable)
            command = (
                'if [ "$#" = 3 ] && [ "$1" = -A ] && [ "$2" = -o ] && '
                '[ "$3" = "pid=,ppid=,comm=" ] && [ -f "$FIXTURE_ROOT/procs" ] && '
                '{ [ ! -e "$FIXTURE_ROOT/ps.log" ] || '
                '{ [ -f "$FIXTURE_ROOT/ps.log" ] && [ -w "$FIXTURE_ROOT/ps.log" ]; }; }; then '
                f'if {{ printf "%s\\n" {record} >> "$FIXTURE_ROOT/ps.log"; }} 2>/dev/null; then '
                'snapshot=$(/usr/bin/mktemp "$FIXTURE_ROOT/.ps.XXXXXXXX") || '
                f'{{ FIXTURE_PS_LOGGED=1 exec {python} "$0" "$@"; }}; '
                "trap '/bin/unlink \"$snapshot\"' EXIT; "
                'if /bin/cat "$FIXTURE_ROOT/procs" > "$snapshot" 2>/dev/null; then '
                f'LC_ALL=C /usr/bin/grep -aq {non_ascii} "$snapshot" 2>/dev/null; '
                'if [ "$?" = 1 ]; then /bin/cat "$snapshot"; exit "$?"; fi; '
                f'FIXTURE_PS_LOGGED=1 FIXTURE_PS_SNAPSHOT="$snapshot" {python} "$0" "$@"; exit "$?"; fi; '
                f'FIXTURE_PS_LOGGED=1 {python} "$0" "$@"; exit "$?"; fi; fi; '
                f'exec {python} "$0" "$@"'
            )
            program = source.replace(
                'with open(root / "ps.log", "a") as log:',
                'with open(os.devnull if os.environ.get("FIXTURE_PS_LOGGED") else root / "ps.log", "a") as log:',
            ).replace('procs = root / "procs"',
                      'procs = Path(os.environ.get("FIXTURE_PS_SNAPSHOT", root / "procs"))')
            content = f'''#!/bin/bash
""":"; {command}; ":"""; import json, sys
from pathlib import Path
{program}
'''
        shared = source in (HOOK_PS, INBOX_PS, INBOX_TMUX, f"print({NOW})")
        self.fixture_file(name, content, shared=shared)

    def set_now(self, epoch: int) -> None:
        self.fixture_file("date", f"#!/bin/bash\nprintf '%s\\n' {epoch}\n", shared=True)

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
        socket_dir = os.environ.get("CODEX_TEST_TMUX_DIR")
        flag, address = ("-S", str(Path(socket_dir) / uuid.uuid4().hex[:16])) if socket_dir else ("-L", socket)
        self.server = [str(binary), flag, address, "-f", "/dev/null"]
        self.socket_path: Path | None = None
        self.addCleanup(self.stop_server)
        self.tmux("new-session", "-d", "-s", "fixture", "-x", "80", "-y", "24", "/bin/sleep 300")
        self.socket_path = Path(self.tmux("display-message", "-p", "-t", "fixture", "#{socket_path}").strip())
        self.pane = self.tmux("display-message", "-p", "-t", "fixture", "#{pane_id}").strip()
        self.digits = self.pane.lstrip("%")
        self.env.update(TMUX_PANE=self.pane, FIXTURE_TMUX=str(binary), FIXTURE_TMUX_FLAG=flag, FIXTURE_SOCKET=address)
        self.fixture_file("tmux", HOOK_TMUX, shared=True)
        self.stub("ps", HOOK_PS)
        # The runner is never below the fixture pane: the first ps answer names the pane's own process
        self.origin = self.tmux("display-message", "-p", "-t", self.pane, PANE_PID_FORMAT).strip()
        self.set_parent(self.origin)

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

    def set_chain(self, *answers: str) -> None:
        """What the `ps` stub answers: the runner, which is the hook's $PPID because this
        process starts it, has the parent answers[0], that one has answers[1], and so on."""
        pids = [str(os.getpid()), *answers[:-1]]
        (self.root / "chain").write_text(json.dumps(dict(zip(pids, answers))))

    def set_parent(self, text: str | None) -> None:
        """What the `ps` stub answers for the runner's own pid: None makes every lookup fail."""
        if text is None:
            (self.root / "chain").unlink(missing_ok=True)
        else:
            self.set_chain(text)

    def link(self, client: str) -> Path:
        """The hook as `client` calls it, through its own link: E1 reads that path."""
        path = self.home / f".{client}/hooks/pane-state.sh"
        if not path.exists():
            path.parent.mkdir(parents=True)
            path.symlink_to(HOOK)
        return path

    def hook(self, event: str, script: Path | None = None, **fields: object) -> None:
        result = self.run_script(script or HOOK, payload={"hook_event_name": event, **fields})
        self.assertEqual(result.stdout, "")

    def assert_ignored(self) -> None:
        """The hook of a foreign process left no option of a finished turn and no report."""
        options = self.options()
        for name in STOP_OPTIONS:
            self.assertNotIn(name, options)
        self.assertEqual(self.stored(), [])

    def test_hook_tmux_stub_overrides_and_forwards(self) -> None:
        def invoke(fmt: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([str(self.bin / "tmux"), "display", "-p", "-t", self.pane, fmt],
                                  text=True, capture_output=True, env=self.env, timeout=10, check=False)

        self.assertEqual(invoke(FRONT_FORMAT).stdout.strip(), "000")
        self.set_front("111")
        self.assertEqual(invoke(FRONT_FORMAT).stdout.strip(), "111")
        self.assertEqual(invoke(PANE_PID_FORMAT).stdout.strip(), self.origin)
        (self.root / "pane_pid").write_text("")
        self.assertNotEqual(invoke(PANE_PID_FORMAT).returncode, 0)
        (self.root / "pane_pid").write_text("41001")
        self.assertEqual(invoke(PANE_PID_FORMAT).stdout.strip(), "41001")

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

    def test_h11_daemon_origin_stop_ignored(self) -> None:
        self.set_parent("1")
        self.hook("Stop", last_assistant_message="final text")
        self.assert_ignored()

    def test_h12_daemon_origin_prompt_ignored(self) -> None:
        self.hook("Stop", last_assistant_message="final text")
        options = self.options()
        stored = self.stored()
        self.assertEqual(options.get("@agent_unseen"), "1")
        self.assertEqual(options.get("@claude_state"), "done")
        self.assertEqual(len(stored), 1)
        self.set_parent("1")
        self.hook("UserPromptSubmit")
        self.assertEqual(self.options(), options)
        self.assertEqual(self.stored(), stored)

    def test_h13_origin_lookup_failure_is_silent(self) -> None:
        pane_pid = self.root / "pane_pid"
        own = self.origin
        # The last case lets ps answer 0 too: a chain ending there would match a pane process of 0,
        # so only the check on pane_pid keeps the hook out
        cases: tuple[tuple[str, str | None, str | None], ...] = (
            ("ps fails", None, None),
            ("ps answers text", "abc", None),
            ("pane_pid lookup fails", own, ""),
            ("pane_pid is 0", "0", "0"),
        )
        for name, parent, answer in cases:
            with self.subTest(case=name):
                self.set_parent(parent)
                pane_pid.unlink(missing_ok=True)
                if answer is not None:
                    pane_pid.write_text(answer)
                self.hook("Stop", last_assistant_message="final text")
                self.assert_ignored()

    def test_h14_origin_walk_three_hops(self) -> None:
        # Every step asks about the process just reached: a guard that asked about its own
        # parent again would never leave the first answer
        self.set_chain("41001", "41002", self.origin)
        self.hook("Stop", last_assistant_message="final text")
        self.assertEqual(self.options().get("@agent_unseen"), "1")

    def test_e1_codex_ignores_inherited_claude_desktop_env(self) -> None:
        # A pane started from a Claude Desktop shell hands Codex its CLAUDE_* env
        self.env["CLAUDE_CODE_ENTRYPOINT"] = "claude-desktop"
        codex = self.link("codex")
        self.hook("UserPromptSubmit", codex)
        self.assertEqual(self.options().get("@claude_state"), "working")
        self.hook("Stop", codex, last_assistant_message="final text")
        options = self.options()
        self.assertEqual(options.get("@claude_state"), "done")
        self.assertEqual(options.get("@agent_unseen"), "1")

    def test_e2_claude_headless_still_ignored(self) -> None:
        self.env["CLAUDE_CODE_ENTRYPOINT"] = "claude-desktop"
        for name, script in (("claude link", self.link("claude")), ("repo path", HOOK)):
            with self.subTest(script=name):
                self.hook("UserPromptSubmit", script)
                self.hook("Stop", script, last_assistant_message="final text")
                self.assert_ignored()

    def test_e3_claude_cli_still_recorded(self) -> None:
        self.env["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        self.hook("Stop", self.link("claude"), last_assistant_message="final text")
        options = self.options()
        self.assertEqual(options.get("@claude_state"), "done")
        self.assertEqual(options.get("@agent_unseen"), "1")


class InboxTests(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.log = self.root / "calls.log"
        self.ps_log = self.root / "ps.log"
        self.rows = self.root / "rows"
        self.windows = self.root / "windows"
        self.rows.write_text("")
        self.windows.write_text("")
        self.stub("tmux", INBOX_TMUX)
        # The closed PATH would reach the live process table; an empty one is the plain command filter
        self.stub("ps", INBOX_PS)
        self.procs()

    def panes(self, *panes: Pane) -> None:
        self.rows.write_text("".join(pane.line() + "\n" for pane in panes))

    def procs(self, *rows: tuple[int, int, str] | None) -> None:
        """The process table `ps` prints, as (pid, ppid, comm) rows padded like BSD ps;
        a None makes ps fail."""
        path = self.root / "procs"
        table = [row for row in rows if row is not None]
        if len(table) < len(rows):
            path.unlink(missing_ok=True)
        else:
            path.write_text("".join(f"{pid:>5} {ppid:>5} {comm}\n" for pid, ppid, comm in table))

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

    def agents(self) -> list[list[str]]:
        """The agent rows of `render`: session, pane, class, display."""
        return [row for row in self.render() if row[1]]

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

    def test_v1_wrapped_codex_with_state_listed(self) -> None:
        cases = (
            ("full path", "/opt/homebrew/bin/codex", "cx"),
            ("blanks in the path", "/Users/x/Library/Application Support/Claude/claude", "cc"),
        )
        for name, comm, tag in cases:
            with self.subTest(case=name):
                self.panes(Pane("%1", command="bash", state="done", unseen="1", pid=500))
                self.procs((500, 1, "sh"), (501, 500, comm))
                agents = self.agents()
                self.assertEqual([row[1:3] for row in agents], [["%1", "ready"]])
                self.assertIn(f" {tag} ", agents[0][3])

    def test_v2_stateless_active_is_working(self) -> None:
        for name, activity in (("active", NOW), ("edge", NOW - 5)):
            with self.subTest(case=name):
                self.panes(Pane("%1", state="", since=None, activity=activity))
                agents = self.agents()
                self.assertEqual([row[1:3] for row in agents], [["%1", "working"]])
                self.assertTrue(agents[0][3].startswith("◌   - cx"), agents[0][3])

    def test_v3_stateless_quiet_is_hidden(self) -> None:
        wrapped = ((500, 1, "sh"), (501, 500, "codex"))
        cases = (
            ("codex, quiet", Pane("%1", state="", since=None, activity=NOW - 6), ()),
            # V2 is Codex only: Claude Code panes run their own hooks, an empty state is idle
            ("claude, active", Pane("%1", command="claude", state="", since=None, activity=NOW), ()),
            ("wrapped codex, quiet",
             Pane("%1", command="bash", state="", since=None, activity=NOW - 6, pid=500), wrapped),
        )
        for name, pane, rows in cases:
            with self.subTest(case=name):
                self.panes(pane)
                self.procs(*rows)
                self.assertEqual(self.agents(), [])
                self.assertEqual(self.status(), "")

    def test_v4_shell_without_agent_not_listed(self) -> None:
        self.panes(Pane("%1", command="zsh", state="waiting", activity=NOW, pid=500),
                   Pane("%2", state="working", activity=NOW, pid=600))
        self.procs((500, 1, "-zsh"), (501, 500, "nvim"), (502, 500, "/x/bin/codex-code-mode-host"),
                   (600, 1, "codex"))
        self.assertEqual([row[1] for row in self.agents()], ["%2"])
        # An agent counts up to 4 hops below the pane process, a 5th hop hides it
        for hops, listed in ((5, []), (4, ["%1"])):
            with self.subTest(hops=hops):
                shells = [(500 + step, 499 + step if step else 1, "sh") for step in range(hops)]
                self.panes(Pane("%1", command="zsh", state="waiting", pid=500))
                self.procs(*shells, (500 + hops, 499 + hops, "codex"))
                self.assertEqual([row[1] for row in self.agents()], listed)

    def test_v5_status_counts_fallback(self) -> None:
        self.panes(Pane("%1", state="", since=None, activity=NOW),
                   Pane("%2", command="bash", state="", since=None, activity=NOW, pid=500),
                   Pane("%3", state="working", activity=NOW))
        self.procs((500, 1, "sh"), (501, 500, "codex"))
        self.assertEqual(self.status().splitlines(), ["#[fg=#7A8290]◌ 3"])
        self.assertEqual(self.mark_calls(), [])
        # One snapshot per status call, not one per pane
        self.assertEqual(len(self.ps_log.read_text().splitlines()), 1)

    def test_v6_ps_failure_falls_back(self) -> None:
        for name, rows in (("ps fails", (None,)), ("empty snapshot", ())):
            with self.subTest(case=name):
                self.panes(Pane("%1", state="working", activity=NOW),
                           Pane("%2", command="bash", state="done", unseen="1", pid=500))
                self.procs(*rows)
                self.assertEqual([row[1:3] for row in self.agents()], [["%1", "working"]])


if __name__ == "__main__":
    unittest.main()
