"""Compatibility checks for the notification JSON fallback."""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codex.test_activity import ActivityFixture

HOOKS = Path(__file__).resolve().parents[1]
BASELINE = HOOKS / "tests/fixtures/notify-baseline.sh"
CANDIDATE = HOOKS / "notify.sh"
HELPER = HOOKS / "notify_fields.py"


class FieldsTests(unittest.TestCase):
    def test_scalar_fields_and_unsupported_values(self) -> None:
        spec = importlib.util.spec_from_file_location("notify_fields", HELPER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.extract_fields('{"message":"hello", "cwd":null}'),
                         ("", "hello", "", ""))
        for value in ('{"message":{}}', '{"message":"a\\u0000b"}', '{bad', '[]'):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                module.extract_fields(value)


    def test_complete_scalar_edge_matrix_matches_legacy_python(self) -> None:
        spec = importlib.util.spec_from_file_location("notify_fields_matrix", HELPER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for value in (None, "", "a\nb\n", "Unicode: привет", "'\"$(echo x)", r"a\0b", False):
            payload = json.dumps({"message": value, "cwd": "/work/test"})
            legacy = json.loads(payload)
            expected = tuple(str(legacy.get(key) or "").rstrip("\n") for key in
                             ("hook_event_name", "message", "cwd", "transcript_path"))
            with self.subTest(value=value):
                self.assertEqual(tuple(field.rstrip("\n") for field in module.extract_fields(payload)),
                                 expected)
        for unsupported in ("a\0b", {"complex": "value"}, [1, 2]):
            with self.subTest(value=unsupported), self.assertRaises(ValueError):
                module.extract_fields(json.dumps({"message": unsupported, "cwd": "/work/test"}))
        for payload in ("{}", '{"message": null}'):
            with self.subTest(payload=payload):
                self.assertEqual(module.extract_fields(payload), ("", "", "", ""))
        for payload in ("{bad", "[]"):
            with self.subTest(payload=payload), self.assertRaises((ValueError, TypeError)):
                module.extract_fields(payload)


    def test_helper_cli_preserves_scalar_transport(self) -> None:
        payload = {"hook_event_name": "Stop", "message": "line one\nUnicode: привет ' \"",
                   "cwd": "/work/demo", "transcript_path": ""}
        result = subprocess.run([sys.executable, str(HELPER)], input=json.dumps(payload),
                                text=True, capture_output=True, check=False)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        fields = dict(token.split("=", 1) for token in shlex.split(result.stdout))
        self.assertEqual(fields, {"event": payload["hook_event_name"],
                                  "message": payload["message"], "cwd": payload["cwd"],
                                  "transcript": payload["transcript_path"]})


class CliDifferentialTests(ActivityFixture):
    def setUp(self) -> None:
        super().setUp()
        self.env.pop("TMUX", None)
        self.env.pop("TMUX_PANE", None)
        self.shell_stub("lsappinfo", "exit 1")
        # These stubs are test fixtures; avoiding Python startup keeps each
        # differential CLI invocation focused on the hook itself.
        self.shell_stub("python3", f'exec {shlex.quote(sys.executable)} "$@"')
        jq = shutil.which("jq")
        assert jq is not None
        for name in ("terminal-notifier", "osascript"):
            exit_code = '${FIXTURE_NOTIFIER_EXIT:-0}' if name == "terminal-notifier" else "0"
            self.shell_stub(name, f"""
{shlex.quote(jq)} -cn --args '$ARGS.positional' -- {shlex.quote(name)} "$@" >> "$FIXTURE_LOG"
exit {exit_code}
""")

    def compare(self, payload: str, candidate: Path = CANDIDATE) -> None:
        def invoke(script: Path, label: str) -> tuple[int, str, str, str]:
            log = self.root / f"{label}-commands.jsonl"
            log.write_text("")
            result = subprocess.run(["/bin/bash", str(script), "--agent", "codex"],
                                    input=payload, text=True, capture_output=True,
                                    env=dict(self.env, FIXTURE_LOG=str(log)), cwd=self.home,
                                    timeout=15, check=False)
            return result.returncode, result.stdout, result.stderr, log.read_text()

        # The two hooks have private logs and only read the shared fixture.
        with ThreadPoolExecutor(max_workers=2) as pool:
            baseline = pool.submit(invoke, BASELINE, "baseline")
            actual = pool.submit(invoke, candidate, "candidate")
            self.assertEqual(baseline.result(), actual.result())

    def test_notification_fixtures_record_arguments_and_exit_codes(self) -> None:
        args = ["", "line one\nline two", "'\"$(echo x)", "Unicode: привет"]
        self.env["FIXTURE_NOTIFIER_EXIT"] = "3"
        for name, expected_code in (("terminal-notifier", 3), ("osascript", 0)):
            with self.subTest(name=name):
                self.reset_calls()
                result = subprocess.run([str(self.bin / name), *args], text=True,
                                        capture_output=True, env=self.env, check=False)
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (expected_code, "", ""))
                self.assertEqual(self.calls(name), [args])

    def test_symlink_and_missing_helper_fall_back_safely(self) -> None:
        (self.bin / "jq").unlink()
        for command in ("cat", "basename", "sed", "readlink"):
            target = shutil.which(command)
            assert target is not None
            (self.bin / command).symlink_to(target)
        self.env["PATH"] = str(self.bin)
        payload = json.dumps({"message": "linked ✓", "cwd": "/work/demo"})
        link = self.root / "notify-link.sh"
        link.symlink_to(CANDIDATE)
        self.compare(payload, link)
        (self.bin / "readlink").unlink()
        (self.bin / "python3").unlink()
        self.env.update(CLAUDE_NOTIFY_DEBUG="1", FIXTURE_NOTIFIER_EXIT="3")
        self.compare(payload, link)



if __name__ == "__main__":
    unittest.main()
