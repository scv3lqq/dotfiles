"""Assistant activity and desktop alerts with synthetic, isolated fixtures."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PICKER = ROOT / "tmux/session-picker.sh"
NOTIFY = ROOT / "claude/hooks/notify.sh"
STATE = ROOT / "claude/hooks/pane-state.sh"
NOW = 2_000_000_000


class ActivityFixture(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.log = self.root / "commands.jsonl"
        self.rows = self.root / "rows"
        self.rows.write_text("")
        # A closed PATH prevents fixtures from reaching real desktop commands.
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "FIXTURE_LOG": str(self.log),
            "FIXTURE_ROWS": str(self.rows),
            "TMUX": "fixture,1,0",
            "TMUX_PANE": "%7",
            "LC_ALL": "en_US.UTF-8",
        }
        self.stub("date", f"print({NOW})")
        self.stub("uname", 'print("Linux" if __import__("os").environ.get("FIXTURE_LINUX") else "Darwin")')
        self.stub("python3", f"import os; os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[1:])")
        jq = shutil.which("jq")
        self.assertIsNotNone(jq, "jq is required for pane-state fixtures")
        (self.bin / "jq").symlink_to(str(jq))
        self.stub("tmux", '''
import os
args = sys.argv[1:]
with open(os.environ["FIXTURE_LOG"], "a") as log:
    log.write(json.dumps(["tmux", *args]) + "\\n")
if args[0] == "list-panes":
    print(Path(os.environ["FIXTURE_ROWS"]).read_text(), end="")
elif args[0] == "list-clients":
    print("fixture-client")
elif args[0] == "display-message":
    fmt = args[-1]
    if fmt == "#{session_name}":
        print("fixture")
    elif "pane_active" in fmt:
        print(os.environ.get("FIXTURE_PANE_VISIBILITY", "1 1 1"))
    else:
        print("fixture:2")
''')

    def stub(self, name: str, source: str) -> None:
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n{source}\n")
        path.chmod(0o755)

    def run_script(self, script: Path, *args: str, payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["/bin/bash", str(script), *args],
            input=json.dumps(payload or {}), text=True, capture_output=True, check=False,
            env=self.env, cwd=self.home, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def calls(self, name: str) -> list[list[str]]:
        if not self.log.exists():
            return []
        records: list[list[str]] = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [record[1:] for record in records if record[0] == name]

    def reset_calls(self) -> None:
        self.log.write_text("")

    @staticmethod
    def row(pane: str, command: str, state: str, *, since: int = NOW - 30,
            activity: int = NOW, title: str = "Fixture task", path: str = "/work/demo",
            window: int = 1) -> str:
        fields = ("$1", f"@{window}", pane, "1", "fixture", "1", str(window),
                  "0", "demo", command, title, path, state, str(since), str(activity))
        return "\t".join(fields) + "\n"

    def render(self, rows: str, *, search: str = "") -> list[list[str]]:
        self.rows.write_text(rows)
        picker_state = self.root / "picker"
        picker_state.mkdir(exist_ok=True)
        (picker_state / "expanded").write_text("$1\n")
        self.env.update(PICKER_STATE=str(picker_state), PICKER_CURRENT="$1", FZF_QUERY=search)
        result = self.run_script(PICKER, "list")
        plain = re.sub(r"\x1b\[[0-9;:]*[A-Za-z]", "", result.stdout)
        return [line.split("\t", 3) for line in plain.splitlines()]

    @staticmethod
    def activity_rows(rows: list[list[str]]) -> list[list[str]]:
        return [row for row in rows if row[1].startswith("%")]


class PickerTests(ActivityFixture):
    def test_mixed_working_waiting_and_completed_identities(self) -> None:
        fixtures = (("%7", "codex", "working", "Codex"),
                    ("%8", "codex", "waiting", "Codex"),
                    ("%9", "codex", "done", "Codex"),
                    ("%10", "claude", "working", "Claude Code"),
                    ("%11", "2.1.3", "waiting", "Claude Code"),
                    ("%12", "claude", "done", "Claude Code"))
        rows = self.render("".join(self.row(pane, cmd, state) for pane, cmd, state, _ in fixtures))
        activity = self.activity_rows(rows)
        self.assertEqual({row[1] for row in activity}, {item[0] for item in fixtures})
        for pane, _, _, identity in fixtures:
            with self.subTest(pane=pane):
                row = next(row for row in activity if row[1] == pane)
                self.assertEqual(row[:3], ["$1", pane, ""])
                self.assertTrue(row[3].endswith(f"{identity} · Fixture task"), row)
        self.assertEqual(sum(row[3] == "  ── assistants ──" for row in rows), 1)

    def test_freshness_retention_and_leftover_shell_guards(self) -> None:
        rows = self.render(
            self.row("%7", "codex", "working", activity=NOW - 6)
            + self.row("%8", "claude", "working", activity=NOW - 6)
            + self.row("%9", "codex", "done", since=NOW - 600)
            + self.row("%10", "claude", "done", since=NOW - 600)
            + self.row("%11", "zsh", "waiting")
            + self.row("%12", "bash", "done")
        )
        self.assertEqual(self.activity_rows(rows), [])
        self.assertFalse(any("──" in row[3] for row in rows))

    def test_five_second_and_599_second_boundaries_are_included(self) -> None:
        rows = self.render(self.row("%7", "codex", "working", activity=NOW - 5)
                           + self.row("%8", "codex", "done", since=NOW - 599))
        self.assertEqual([row[1] for row in self.activity_rows(rows)], ["%7", "%8"])

    def test_completed_rows_are_newest_first_and_stable_on_ties(self) -> None:
        rows = self.render(self.row("%7", "codex", "done", since=NOW - 40)
                           + self.row("%8", "claude", "done", since=NOW - 10)
                           + self.row("%9", "codex", "done", since=NOW - 10))
        self.assertEqual([row[1] for row in self.activity_rows(rows)], ["%8", "%9", "%7"])

    def test_search_keeps_activity_without_separator_and_uses_path_fallback(self) -> None:
        rows = self.render(self.row("%7", "codex", "waiting", title="", path=str(self.home / "demo")), search="demo")
        activity = self.activity_rows(rows)
        self.assertEqual(len(activity), 1)
        self.assertTrue(activity[0][3].endswith("Codex · ~/demo"), activity)
        self.assertFalse(any("──" in row[3] for row in rows))
        self.assertTrue(any(row[1].startswith("@") for row in rows))

    def test_codex_window_uses_existing_assistant_glyph(self) -> None:
        rows = self.render(self.row("%7", "codex", "") + self.row("%8", "claude", "", window=2))
        windows = [row[3] for row in rows if row[1].startswith("@")]
        self.assertEqual(len(windows), 2)
        for window in windows:
            self.assertIn("\U000f06a9", window)

    def test_synthetic_hook_lifecycle_renders_each_codex_state(self) -> None:
        tmux = shutil.which("tmux")
        self.assertIsNotNone(tmux, "tmux is required for lifecycle fixtures")
        socket = f"activity-fixture-{uuid.uuid4().hex}"
        command = [str(tmux), "-L", socket, "-f", "/dev/null"]

        def isolated_tmux(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([*command, *args], text=True, capture_output=True,
                                  env=self.env, timeout=10, check=True)

        def cleanup_server() -> None:
            subprocess.run([*command, "kill-server"], env=self.env, capture_output=True, timeout=10, check=False)

        self.addCleanup(cleanup_server)
        isolated_tmux("new-session", "-d", "-s", "fixture", "-x", "80", "-y", "24", "/bin/sleep 120")
        pane = isolated_tmux("display-message", "-p", "-t", "fixture", "#{pane_id}").stdout.strip()
        self.env["TMUX_PANE"] = pane
        fake_tmux = (self.bin / "tmux").read_text()
        self.stub("tmux", f"import os; os.execv({str(tmux)!r}, {command!r} + sys.argv[1:])")
        observations: list[tuple[str, str]] = []
        for event, expected in (("UserPromptSubmit", "working"), ("PermissionRequest", "waiting"), ("Stop", "done")):
            result = self.run_script(STATE, payload={"hook_event_name": event})
            self.assertEqual(result.stdout, "")
            state = isolated_tmux("show-options", "-p", "-v", "-t", pane, "@claude_state").stdout.strip()
            since = isolated_tmux("show-options", "-p", "-v", "-t", pane, "@claude_since").stdout.strip()
            self.assertEqual(state, expected)
            self.assertEqual(since, str(NOW))
            observations.append((state, since))
        (self.bin / "tmux").write_text(fake_tmux)
        for state, since in observations:
            with self.subTest(state=state):
                rows = self.render(self.row(pane, "codex", state, since=int(since)))
                activity = self.activity_rows(rows)
                self.assertEqual(len(activity), 1)
                self.assertTrue(activity[0][3].endswith("Codex · Fixture task"))


class NotificationTests(ActivityFixture):
    def setUp(self) -> None:
        super().setUp()
        for name in ("terminal-notifier", "osascript", "open"):
            self.stub(name, f'''
import os
with open(os.environ["FIXTURE_LOG"], "a") as log:
    log.write(json.dumps([{name!r}, *sys.argv[1:]]) + "\\n")
sys.exit(int(os.environ.get("FIXTURE_NOTIFIER_EXIT", "0")) if {name!r} == "terminal-notifier" else 0)
''')
        self.stub("lsappinfo", '''
import os
if sys.argv[1] == "front":
    print("fixture-asn")
else:
    bundle = "com.mitchellh.ghostty" if os.environ.get("FIXTURE_VISIBLE") else "fixture.other"
    print('"CFBundleIdentifier"="' + bundle + '"')
''')
        for client in ("codex", "claude"):
            link = self.home / f".{client}/hooks/notify.sh"
            link.parent.mkdir(parents=True)
            link.symlink_to(NOTIFY)

    def notify(self, *args: str, script: Path = NOTIFY, event: str = "Stop",
               transcript: Path | None = None) -> None:
        payload: dict[str, object] = {"hook_event_name": event, "cwd": "/work/demo", "message": "Fixture answer"}
        if transcript:
            payload["transcript_path"] = str(transcript)
        result = self.run_script(script, *args, payload=payload)
        self.assertEqual(result.stdout, "")

    def assert_notification(self, title: str, group: str) -> None:
        calls = self.calls("terminal-notifier")
        self.assertEqual(len(calls), 1, calls)
        args = calls[0]
        self.assertEqual(args[args.index("-title") + 1], title)
        self.assertEqual(args[args.index("-group") + 1], group)
        self.assertEqual(args[args.index("-message") + 1], "Fixture answer")
        self.assertEqual(args[args.index("-subtitle") + 1], "demo · fixture:2")

    def test_explicit_agent_identity_and_groups(self) -> None:
        for agent, title, group in (("codex", "Codex: готово", "codex-%7"),
                                    ("claude", "Claude Code: готово", "claude-code-%7")):
            with self.subTest(agent=agent):
                self.reset_calls()
                self.notify("--agent", agent)
                self.assert_notification(title, group)

    def test_symlink_invocation_identity_before_resolution(self) -> None:
        for agent, title, group in (("codex", "Codex: готово", "codex-%7"),
                                    ("claude", "Claude Code: готово", "claude-code-%7")):
            with self.subTest(agent=agent):
                self.reset_calls()
                self.notify(script=self.home / f".{agent}/hooks/notify.sh")
                self.assert_notification(title, group)

    def test_default_identity_preserves_claude(self) -> None:
        self.notify()
        self.assert_notification("Claude Code: готово", "claude-code-%7")

    def test_unknown_agent_is_silent_success(self) -> None:
        self.notify("--agent", "unknown")
        self.assertEqual(self.calls("terminal-notifier"), [])
        self.assertEqual(self.calls("osascript"), [])

    def test_visible_pane_is_suppressed_for_both_agents(self) -> None:
        self.env["FIXTURE_VISIBLE"] = "1"
        for agent in ("codex", "claude"):
            with self.subTest(agent=agent):
                self.notify("--agent", agent)
        self.assertEqual(self.calls("terminal-notifier"), [])
        self.assertEqual(self.calls("osascript"), [])

    def test_inactive_or_detached_pane_is_not_suppressed(self) -> None:
        self.env["FIXTURE_VISIBLE"] = "1"
        for visibility in ("0 1 1", "1 0 1", "1 1 0"):
            with self.subTest(visibility=visibility):
                self.reset_calls()
                self.env["FIXTURE_PANE_VISIBILITY"] = visibility
                self.notify("--agent", "codex")
                self.assert_notification("Codex: готово", "codex-%7")

    def test_force_overrides_visibility(self) -> None:
        self.env.update(FIXTURE_VISIBLE="1", CLAUDE_NOTIFY_FORCE="1")
        self.notify("--agent", "codex")
        self.assert_notification("Codex: готово", "codex-%7")

    def test_linux_and_notification_events_are_silent(self) -> None:
        for agent in ("codex", "claude"):
            with self.subTest(agent=agent):
                self.notify("--agent", agent, event="Notification")
                self.env["FIXTURE_LINUX"] = "1"
                self.notify("--agent", agent)
                self.env.pop("FIXTURE_LINUX")
        self.assertEqual(self.calls("terminal-notifier"), [])
        self.assertEqual(self.calls("osascript"), [])

    def test_osascript_fallback_retains_agent_title(self) -> None:
        self.env["FIXTURE_NOTIFIER_EXIT"] = "3"
        for agent, title in (("codex", "Codex: готово"), ("claude", "Claude Code: готово")):
            with self.subTest(agent=agent):
                self.reset_calls()
                self.notify("--agent", agent)
                calls = self.calls("osascript")
                self.assertEqual(len(calls), 1)
                self.assertIn(f'with title "{title}"', calls[0][1])
                self.assertIn('display notification "Fixture answer"', calls[0][1])

    def test_headless_guard_only_applies_to_claude(self) -> None:
        self.env["CLAUDE_CODE_ENTRYPOINT"] = "sdk"
        self.notify("--agent", "claude")
        self.assertEqual(self.calls("terminal-notifier"), [])
        self.notify("--agent", "codex")
        self.assert_notification("Codex: готово", "codex-%7")

    def test_pending_task_guard_only_applies_to_claude(self) -> None:
        transcript = self.root / "transcript.jsonl"
        transcript.write_text(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "fixture-task", "content": "Async agent launched"}
        ]}}) + "\n")
        self.notify("--agent", "claude", transcript=transcript)
        self.assertEqual(self.calls("terminal-notifier"), [])
        self.notify("--agent", "codex", transcript=transcript)
        self.assert_notification("Codex: готово", "codex-%7")

    def test_no_pane_uses_agent_group_and_activation(self) -> None:
        self.env.pop("TMUX")
        self.env.pop("TMUX_PANE")
        self.notify("--agent", "codex")
        args = self.calls("terminal-notifier")[0]
        self.assertEqual(args[args.index("-group") + 1], "codex-nopane")
        self.assertEqual(args[args.index("-activate") + 1], "com.mitchellh.ghostty")
        self.assertNotIn("-execute", args)

    def test_notification_click_focuses_origin_without_agent_argument(self) -> None:
        script = self.home / ".codex/hooks/notify.sh"
        self.notify(script=script)
        args = self.calls("terminal-notifier")[0]
        execute = shlex.split(args[args.index("-execute") + 1])
        self.assertEqual(execute, [str(script), "--focus", "%7"])
        self.reset_calls()
        result = self.run_script(Path(execute[0]), *execute[1:])
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.calls("open"), [["-b", "com.mitchellh.ghostty"]])
        calls = self.calls("tmux")
        self.assertIn(["switch-client", "-c", "fixture-client", "-t", "fixture"], calls)
        self.assertIn(["select-window", "-t", "%7"], calls)
        self.assertIn(["select-pane", "-t", "%7"], calls)


if __name__ == "__main__":
    unittest.main()
