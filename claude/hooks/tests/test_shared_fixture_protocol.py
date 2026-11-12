"""Compare direct and shared-inode fixture scripts under isolated state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codex.test_agent_inbox import HOOK_PS, INBOX_PS, INBOX_TMUX


class SharedFixtureProtocolTests(unittest.TestCase):
    def test_recorders_and_failures_match(self) -> None:
        cases = [
            (INBOX_TMUX, ["list-panes", "", "雪", "line\nnext", "'\"", r"a\0b"], {"rows": "rows\n"}),
            (INBOX_TMUX, ["list-windows"], {}),
            (INBOX_TMUX, [], {}),
            (INBOX_PS, ["-A", "-o", "pid=,ppid=,comm="], {"procs": "1 0 shell\n"}),
            (INBOX_PS, ["-A", "-o", "pid=,ppid=,comm="], {}),
            (INBOX_PS, ["invalid"], {}),
            (HOOK_PS, ["-o", "ppid=", "-p", "42"], {"chain": '{"42": "123"}'}),
            (HOOK_PS, ["-o", "ppid=", "-p", "missing"], {}),
            (HOOK_PS, ["invalid"], {}),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable, shared = root / "tool", root / "shared"
            for source, args, files in cases:
                with self.subTest(args=args, files=files):
                    content = f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n{source}\n"
                    shared.write_text(content)
                    shared.chmod(0o755)
                    observed = []
                    for link in (False, True):
                        for name in ("calls.log", "ps.log", "rows", "windows", "procs", "chain"):
                            (root / name).unlink(missing_ok=True)
                        for name, data in files.items():
                            (root / name).write_text(data)
                        executable.unlink(missing_ok=True)
                        if link:
                            executable.symlink_to(shared)
                        else:
                            executable.write_text(content)
                            executable.chmod(0o755)
                        result = subprocess.run([str(executable), *args],
                                                env=dict(os.environ, FIXTURE_ROOT=str(root)),
                                                capture_output=True, check=False)
                        logs = tuple((root / name).read_bytes() if (root / name).exists() else None
                                     for name in ("calls.log", "ps.log"))
                        observed.append((result.returncode, result.stdout, result.stderr, logs))
                    self.assertEqual(observed[0], observed[1])

    def test_parallel_calls_use_private_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "shared"
            template.write_text(f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n{INBOX_TMUX}\n")
            template.chmod(0o755)
            def invoke(index: int) -> tuple[bytes, bytes]:
                private = root / str(index)
                private.mkdir()
                executable = private / "tmux"
                executable.symlink_to(template)
                result = subprocess.run([str(executable), "display", "雪", str(index)],
                                        env=dict(os.environ, FIXTURE_ROOT=str(private)),
                                        capture_output=True, check=True)
                return result.stdout, (private / "calls.log").read_bytes()
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(invoke, range(8)))
            for index, (output, log) in enumerate(results):
                self.assertEqual(output, b"fixture:0.0  /work/demo\n")
                self.assertEqual(json.loads(log), ["display", "雪", str(index)])

    def test_real_fixture_materialization_and_override(self) -> None:
        from codex.test_activity import ActivityFixture
        from codex.test_agent_inbox import Fixture

        for fixture_type in (ActivityFixture, Fixture):
            with self.subTest(fixture=fixture_type.__name__):
                class IsolatedFixture(fixture_type):  # type: ignore[valid-type,misc]
                    pass
                IsolatedFixture.setUpClass()
                first, second = IsolatedFixture(), IsolatedFixture()
                try:
                    first.setUp()
                    second.setUp()
                    first.stub("shared", INBOX_PS)
                    second.stub("shared", INBOX_PS)
                    a, b = first.bin / "shared", second.bin / "shared"
                    # ActivityFixture intentionally shares only its known immutable stubs.
                    if fixture_type is ActivityFixture:
                        first.shell_stub("ps", "echo one")
                        second.shell_stub("ps", "echo one")
                        a, b = first.bin / "ps", second.bin / "ps"
                    self.assertTrue(a.is_symlink())
                    self.assertEqual(a.stat().st_ino, b.stat().st_ino)
                    self.assertEqual(a.stat().st_mode & 0o222, 0)
                    saved = b.read_bytes()
                    if fixture_type is ActivityFixture:
                        first.shell_stub("ps", "echo different")
                    else:
                        first.stub("shared", "print('different')")
                    self.assertNotEqual(a.read_bytes(), saved)
                    self.assertEqual(b.read_bytes(), saved)
                    self.assertNotEqual(a.stat().st_ino, b.stat().st_ino)
                    template = b.resolve()
                finally:
                    first.doCleanups()
                    second.doCleanups()
                    IsolatedFixture.doClassCleanups()
                self.assertFalse(template.exists())

    def test_notifier_decoded_records_and_exit(self) -> None:
        import shlex
        import shutil

        jq = shutil.which("jq")
        assert jq is not None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old, new = root / "old", root / "new"
            old.write_text(f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                           "import os\nwith open(os.environ['FIXTURE_LOG'], 'a') as log:\n"
                           "    log.write(json.dumps(['terminal-notifier', *sys.argv[1:]]) + '\\n')\n"
                           "sys.exit(int(os.environ.get('FIXTURE_NOTIFIER_EXIT', '0')))\n")
            new.write_text(f"#!/bin/bash\n{shlex.quote(jq)} -cn --args '$ARGS.positional' -- "
                           'terminal-notifier "$@" >> "$FIXTURE_LOG"\n'
                           'exit ${FIXTURE_NOTIFIER_EXIT:-0}\n')
            old.chmod(0o755)
            new.chmod(0o755)
            args = ["", "雪", "line\nnext", "'\"", r"a\0b"]
            for status in ("0", "3"):
                observed = []
                for path in (old, new):
                    log = root / "log"
                    log.unlink(missing_ok=True)
                    env = {"PATH": "/nonexistent", "FIXTURE_LOG": str(log),
                           "FIXTURE_NOTIFIER_EXIT": status}
                    result = subprocess.run([str(path), *args], env=env, capture_output=True, check=False)
                    observed.append((result.returncode, result.stdout, result.stderr, json.loads(log.read_text())))
                self.assertEqual(observed[0], observed[1])
