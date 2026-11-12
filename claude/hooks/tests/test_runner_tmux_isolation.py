"""Regression coverage for tmux servers created by runner fixtures."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex import test_run_tests


class RunnerTmuxIsolationTests(unittest.TestCase):
    def test_fixture_server_ignores_user_config_and_remains_usable(self) -> None:
        tmux = shutil.which("tmux")
        if tmux is None:
            self.skipTest("tmux unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "config-loaded"
            config = root / ".tmux.conf"
            config.write_text(f"run-shell 'touch {marker}'\n")
            env = dict(os.environ, HOME=directory)
            env.pop("TMUX", None)
            for name, args in (("control", ["-f", str(config)]), ("fixture", ["-f", "/dev/null"])):
                socket = root / name
                base = [tmux, "-S", str(socket)]
                try:
                    subprocess.run(base + args + ["new-session", "-d", "sleep 30"], env=env, check=True)
                    subprocess.run(base + ["has-session"], env=env, check=True)
                    if name == "control":
                        self.assertTrue(marker.exists())
                        marker.unlink()
                    else:
                        self.assertFalse(marker.exists())
                finally:
                    subprocess.run(base + ["kill-server"], env=env, capture_output=True, check=False)

    def test_fixture_environment_excludes_inherited_zsh_startup(self) -> None:
        tmux = shutil.which("tmux")
        if tmux is None:
            self.skipTest("tmux unavailable")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            marker = parent / "loaded"
            (parent / ".zshenv").write_text(f"printf loaded > {marker}\n")
            with patch.dict(os.environ, {"SHELL": "/bin/zsh", "ZDOTDIR": directory}):
                fixture = test_run_tests.RunnerTests()
                try:
                    fixture.setUp()
                    self.assertEqual(os.environ["SHELL"], "/bin/sh")
                    self.assertEqual(os.environ["ZDOTDIR"], str(fixture.root))
                    socket = fixture.root / "canary.sock"
                    command = [tmux, "-S", str(socket), "-f", "/dev/null"]
                    try:
                        subprocess.run(command + ["new-session", "-d", "sleep 30"], check=True)
                        result = subprocess.run(command + ["show-options", "-gv", "default-shell"],
                                                text=True, capture_output=True, check=True)
                        self.assertEqual(result.stdout.strip(), "/bin/sh")
                        self.assertFalse(marker.exists())
                    finally:
                        subprocess.run(command + ["kill-server"], capture_output=True, check=False)
                finally:
                    fixture.doCleanups()
