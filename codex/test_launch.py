"""Codex shell launch isolation with a synthetic executable and argv recorder."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALIASES = ROOT / "zsh/aliases.zsh"


class LaunchTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "argv.json"
        executable = self.bin / "codex"
        executable.write_text(f'''#!{sys.executable}
import json
import os
import sys
from pathlib import Path

Path(os.environ["FIXTURE_ARGV"]).write_text(json.dumps(sys.argv[1:]))
sys.exit(int(os.environ["FIXTURE_EXIT"]))
''')
        executable.chmod(0o755)

    def launch(self, *args: str, exit_code: int = 0) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        result = subprocess.run(
            ["/bin/zsh", "-f", "-c", 'source "$1"; shift; codex "$@"',
             "fixture", str(ALIASES), *args],
            env={"HOME": str(self.root), "PATH": str(self.bin),
                 "FIXTURE_ARGV": str(self.log), "FIXTURE_EXIT": str(exit_code)},
            cwd=self.root, text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertTrue(self.log.exists(), result.stderr)
        recorded: list[str] = json.loads(self.log.read_text())
        return result, recorded

    def test_normal_launch_uses_embedded_execution(self) -> None:
        result, recorded = self.launch("--yolo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(recorded, ["--no-daemon", "--yolo"])

    def test_resume_and_fork_preserve_subcommands_and_session(self) -> None:
        for command in ("resume", "fork"):
            with self.subTest(command=command):
                result, recorded = self.launch(command, "fixture-session")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(recorded, ["--no-daemon", command, "fixture-session"])

    def test_explicit_embedded_flag_passes_through_unchanged(self) -> None:
        result, recorded = self.launch("--no-daemon", "resume", "fixture-session")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(recorded, ["--no-daemon", "resume", "fixture-session"])

    def test_spaces_empty_strings_and_globs_preserve_argument_boundaries(self) -> None:
        result, recorded = self.launch("--cd", "fixture directory", "", "literal * [text]", "say 'hello'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(recorded, ["--no-daemon", "--cd", "fixture directory", "", "literal * [text]", "say 'hello'"])

    def test_explicit_remote_forms_pass_through_unchanged(self) -> None:
        cases = (
            ["--remote", "fixture-endpoint", "--yolo"],
            ["--remote=fixture-endpoint", "resume", "fixture-session"],
            ["fork", "fixture-session", "--remote", "fixture endpoint", ""],
            ["--yolo", "--remote=fixture-endpoint", "--", "literal prompt"],
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result, recorded = self.launch(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(recorded, arguments)

    def test_end_of_options_stops_remote_detection(self) -> None:
        for remote in ("--remote", "--remote=fixture-endpoint"):
            with self.subTest(remote=remote):
                result, recorded = self.launch("--", remote, "")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(recorded, ["--no-daemon", "--", remote, ""])

    def test_remote_like_prompt_does_not_disable_embedded_execution(self) -> None:
        result, recorded = self.launch("--remote-fixture", "prefix --remote=fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(recorded, ["--no-daemon", "--remote-fixture", "prefix --remote=fixture"])

    def test_nonzero_exit_status_is_preserved(self) -> None:
        for arguments in (("--yolo",), ("--remote", "fixture-endpoint"), ("--remote=fixture-endpoint",)):
            with self.subTest(arguments=arguments):
                result, _ = self.launch(*arguments, exit_code=37)
                self.assertEqual(result.returncode, 37, result.stderr)


if __name__ == "__main__":
    unittest.main()
