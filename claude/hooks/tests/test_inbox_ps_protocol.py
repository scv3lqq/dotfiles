"""Compare the process recorder with the original fixture program."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codex import test_agent_inbox


class InboxPsProtocolTests(unittest.TestCase):
    def test_output_errors_and_log_match_original(self) -> None:
        fixture_type = test_agent_inbox.Fixture
        fixture_type.setUpClass()
        fixture = fixture_type()
        try:
            fixture.setUp()
            fixture.stub("ps", test_agent_inbox.INBOX_PS)
            candidate = (fixture.bin / "ps").read_text()
            original = (f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                        f"{test_agent_inbox.INBOX_PS}\n")
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                executable = root / "ps"
                procs = root / "procs"
                log = root / "ps.log"
                args = ["-A", "-o", "pid=,ppid=,comm="]
                cases = [(b"", args), (b"1 0 sh", args), (b"1 0 sh\n2 1 codex\n", args),
                         (b"1 0 sh\r\n", args),
                         ("雪 ' \"\n".encode(), args), (b"nul\0byte\n", args),
                         (b"\xff", args), (None, args), (b"1 0 sh\n", ["invalid"])]
                for data, arguments in cases:
                    with self.subTest(data=data, arguments=arguments):
                        if data is None:
                            procs.unlink(missing_ok=True)
                        else:
                            procs.write_bytes(data)
                        observed = []
                        for program in (original, candidate):
                            log.unlink(missing_ok=True)
                            executable.write_text(program)
                            executable.chmod(0o700)
                            result = subprocess.run([str(executable), *arguments], input=b"a\0b", check=False,
                                env=dict(os.environ, FIXTURE_ROOT=str(root)), capture_output=True)
                            records = [json.loads(line) for line in log.read_text().splitlines()]
                            observed.append((result.returncode, result.stdout, result.stderr, records))
                        self.assertEqual(*observed)
                        self.assertFalse(list(root.glob(".ps.*")))
        finally:
            fixture.doCleanups()
            fixture_type.doClassCleanups()

    def test_replacement_during_validation_matches_python(self) -> None:
        fixture_type = test_agent_inbox.Fixture
        fixture_type.setUpClass()
        fixture = fixture_type()
        try:
            fixture.setUp()
            fixture.stub("ps", test_agent_inbox.INBOX_PS)
            candidate = (fixture.bin / "ps").read_text()
            original = (f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                        f"{test_agent_inbox.INBOX_PS}\n")
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tool, grep = root / "ps", root / "grep"
                ready, proceed = root / "ready", root / "proceed"
                procs, log = root / "procs", root / "ps.log"
                grep.write_text("#!/bin/bash\n/usr/bin/grep \"$@\"; status=$?\n"
                                "printf ready > \"$READY\"\n"
                                "while [ ! -e \"$PROCEED\" ]; do /bin/sleep .01; done\n"
                                "exit \"$status\"\n")
                grep.chmod(0o700)
                procs.write_text("1 0 sh\n")
                tool.write_text(candidate.replace("/usr/bin/grep", str(grep)))
                tool.chmod(0o700)
                env = dict(os.environ, FIXTURE_ROOT=str(root), READY=str(ready), PROCEED=str(proceed))
                args = [str(tool), "-A", "-o", "pid=,ppid=,comm="]
                process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 5
                    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertTrue(ready.exists(), "candidate did not reach the validation barrier")
                    replacement = root / "replacement"
                    replacement.write_bytes(b"\xff")
                    replacement.replace(procs)
                    proceed.touch()
                    stdout, stderr = process.communicate(timeout=5)
                    candidate_result = (process.returncode, stdout, stderr, log.read_bytes())
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()
                self.assertEqual((process.returncode, stdout), (0, b"1 0 sh\n"))
                log.unlink()
                procs.write_text("1 0 sh\n")
                tool.write_text(original)
                reference = subprocess.run(args, env=env, capture_output=True, check=False)
                self.assertEqual(candidate_result, (reference.returncode, reference.stdout,
                                                    reference.stderr, log.read_bytes()))
        finally:
            fixture.doCleanups()
            fixture_type.doClassCleanups()

    def test_concurrent_recording_and_log_failure(self) -> None:
        fixture_type = test_agent_inbox.Fixture
        fixture_type.setUpClass()
        fixture = fixture_type()
        try:
            fixture.setUp()
            fixture.stub("ps", test_agent_inbox.INBOX_PS)
            executable = fixture.bin / "ps"
            (fixture.root / "procs").write_text("1 0 sh\n")
            arguments = [str(executable), "-A", "-o", "pid=,ppid=,comm="]
            def invoke() -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(arguments, env=fixture.env, capture_output=True, check=False)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = [future.result() for future in [pool.submit(invoke) for _ in range(8)]]
            self.assertTrue(all((r.returncode, r.stdout, r.stderr) == (0, b"1 0 sh\n", b"") for r in results))
            log = fixture.root / "ps.log"
            self.assertEqual([json.loads(line) for line in log.read_text().splitlines()],
                             [arguments[1:]] * 8)
            self.assertFalse(list(fixture.root.glob(".ps.*")))
            log.unlink()
            log.mkdir()
            result = invoke()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"IsADirectoryError", result.stderr)
        finally:
            fixture.doCleanups()
            fixture_type.doClassCleanups()
