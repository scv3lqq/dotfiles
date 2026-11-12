"""Differential checks for the activity tmux fixture's JSON call logger."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

# Keep the fallback on line 3, as in the existing generated fixture.
FAST_LOGGER = r'''if command -v jq >/dev/null 2>&1 && [ -f "$FIXTURE_LOG" ] && [ -w "$FIXTURE_LOG" ]; then record='["tmux"'; simple=1; for arg in "$@"; do case "$arg" in *[!a-zA-Z0-9_.,:/%#@={}\ -]*) simple=0; break;; esac; record="$record,\"$arg\""; done; if [ "$simple" = 1 ]; then printf '%s\n' "$record]" >> "$FIXTURE_LOG"; else jq -cn --args '$ARGS.positional' -- tmux "$@" >> "$FIXTURE_LOG"; fi; else jq -cn --args '$ARGS.positional' -- tmux "$@" >> "$FIXTURE_LOG"; fi'''
OLD_LOGGER = '''jq -cn --args '$ARGS.positional' -- tmux "$@" >> "$FIXTURE_LOG"'''


class TmuxLoggerProtocolTests(unittest.TestCase):
    def test_original_and_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "tmux"
            log = root / "log"
            cases = [
                (["display-message", "-p", "#{pane_pid}"], None),
                (["", "space value", "雪", 'a"b', "line\nend", r"a\0b"], None),
                (["select-pane", "-t", "%7"], "/nonexistent"),
            ]
            for args, path in cases:
                with self.subTest(args=args, path=path):
                    results = []
                    for source in (OLD_LOGGER, FAST_LOGGER):
                        script.write_text(f"#!/bin/bash\n\n{source}\n")
                        log.write_text("")
                        env = dict(os.environ, FIXTURE_LOG=str(log))
                        if path is not None:
                            env["PATH"] = path
                        result = subprocess.run(["/bin/bash", str(script), *args], env=env,
                                                capture_output=True, text=True, check=False)
                        results.append((result.returncode, result.stdout, result.stderr, log.read_bytes()))
                    self.assertEqual(*results)
                    if path is None:
                        self.assertEqual(json.loads(results[0][3]), ["tmux", *args])

    def test_log_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "tmux"
            results = []
            for source in (OLD_LOGGER, FAST_LOGGER):
                script.write_text(f"#!/bin/bash\n\n{source}\n")
                result = subprocess.run(["/bin/bash", str(script), "select-pane"],
                                        env=dict(os.environ, FIXTURE_LOG=str(root)),
                                        text=True, capture_output=True, check=False)
                results.append((result.returncode, result.stdout, result.stderr))
            self.assertEqual(*results)

    def test_fast_path_and_concurrent_records(self) -> None:
        import shutil

        jq = shutil.which("jq")
        assert jq is not None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script, wrapper, log, marker = (root / name for name in ("tmux", "jq", "log", "marker"))
            script.write_text(f"#!/bin/bash\n\n{FAST_LOGGER}\n")
            wrapper.write_text(f'#!/bin/bash\nprintf "called\\n" >> "$MARKER"\nexec "{jq}" "$@"\n')
            wrapper.chmod(0o755)
            log.write_text("")
            env = dict(os.environ, FIXTURE_LOG=str(log), MARKER=str(marker), PATH=str(root))
            commands = [["/bin/bash", str(script), "display-message", "-t", f"%{index}"]
                        for index in range(16)]
            processes = [subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE) for command in commands]
            for process in processes:
                self.assertEqual(process.communicate(), (b"", b""))
                self.assertEqual(process.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertCountEqual([json.loads(line) for line in log.read_text().splitlines()],
                                  [["tmux", *command[2:]] for command in commands])
            subprocess.run(["/bin/bash", str(script), "quote\""], env=env, check=True)
            self.assertEqual(marker.read_text(), "called\n")

    def test_failing_jq_rejects_fast_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script, jq, log = (root / name for name in ("tmux", "jq", "log"))
            jq.write_text('#!/bin/bash\nprintf "jq failed\\n" >&2\nexit 9\n')
            jq.chmod(0o755)
            env = dict(os.environ, FIXTURE_LOG=str(log), PATH=str(root))
            observations = []
            for source in (OLD_LOGGER, FAST_LOGGER):
                script.write_text(f"#!/bin/bash\n\n{source}\n")
                log.write_text("")
                result = subprocess.run(["/bin/bash", str(script), "select-pane"],
                                        env=env, capture_output=True, text=True, check=False)
                observations.append((result.returncode, result.stderr, log.read_text()))
            self.assertEqual(observations[0], (9, "jq failed\n", ""))
            self.assertNotEqual(observations[0], observations[1])
