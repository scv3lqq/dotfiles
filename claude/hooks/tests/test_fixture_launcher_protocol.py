"""Check the activity fixture's Python launcher transport contract."""

from __future__ import annotations

import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LauncherProtocolTests(unittest.TestCase):
    def test_shell_launcher_matches_python_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            candidate = root / "candidate"
            direct = root / "direct"
            direct.symlink_to(sys.executable)
            original.write_text(
                f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                f"import os; os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[1:])\n"
            )
            candidate.write_text(f"#!/bin/bash\nexec {shlex.quote(sys.executable)} \"$@\"\n")
            original.chmod(0o755)
            candidate.chmod(0o755)
            env = {"HOME": str(root), "PATH": str(root), "FIXTURE_VALUE": "unicode 你好\n'quoted'"}
            program = ("import json, os, sys; "
                       "print(json.dumps([sys.argv[1:], os.environ['FIXTURE_VALUE'], "
                       "sys.stdin.read()], ensure_ascii=True))")
            cases = [
                (["-c", program, "", "a b", "'quote'", "line\nnext", "雪", r"a\0b"], "a\0b\n"),
                (["-c", "import sys; print('error', file=sys.stderr); sys.exit(7)"], ""),
                (["-c", "raise ValueError('broken')"], ""),
                (["-c", "import json; print(json.loads('null'))"], ""),
                ([str(root / "missing.py")], ""),
            ]
            for args, data in cases:
                with self.subTest(args=args):
                    results = [subprocess.run([str(path), *args], input=data, text=True,
                                              capture_output=True, env=env, check=False)
                               for path in (original, candidate, direct)]
                    for actual in results[1:]:
                        self.assertEqual((results[0].stdout, results[0].stderr, results[0].returncode),
                                         (actual.stdout, actual.stderr, actual.returncode))


    def test_missing_absolute_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing-python"
            original, direct = root / "original", root / "direct"
            original.write_text(f"#!{missing}\npass\n")
            original.chmod(0o755)
            direct.symlink_to(missing)
            for path in (original, direct):
                with self.subTest(path=path), self.assertRaises(FileNotFoundError):
                    subprocess.run([str(path)], check=False)


if __name__ == "__main__":
    unittest.main()

