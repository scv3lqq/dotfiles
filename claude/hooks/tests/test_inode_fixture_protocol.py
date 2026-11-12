"""Protocol and isolation checks for a shared immutable uname stub."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UNAME = '''#!/bin/bash
if [ -n "${FIXTURE_LINUX:-}" ]; then echo Linux; else echo Darwin; fi
'''


class UnameProtocolTests(unittest.TestCase):
    def test_original_and_shared_stub_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, shared, linked = (root / name for name in ("old", "shared", "linked"))
            for path in (original, shared):
                path.write_text(UNAME)
                path.chmod(0o755)
            linked.symlink_to(shared)
            for value in (None, "", "0", "雪\n'\"", r"\0"):
                with self.subTest(value=value):
                    env = dict(os.environ)
                    env.pop("FIXTURE_LINUX", None)
                    env["PATH"] = "/nonexistent"
                    if value is not None:
                        env["FIXTURE_LINUX"] = value
                    results = [subprocess.run([str(path), "", "雪", "\n", r"\0"], env=env,
                                              text=True, capture_output=True, check=False)
                               for path in (original, linked)]
                    self.assertEqual((results[0].stdout, results[0].stderr, results[0].returncode),
                                     (results[1].stdout, results[1].stderr, results[1].returncode))

    def test_nul_argument_is_rejected_by_process_api(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for name in ("old", "linked"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    subprocess.run([str(Path(temporary) / name), "a\0b"], check=False)

    def test_parallel_isolation_and_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared = root / "shared"
            shared.write_text(UNAME)
            shared.chmod(0o755)
            links = [root / str(i) for i in range(12)]
            for link in links:
                link.symlink_to(shared)
            def invoke(index: int) -> str:
                env = dict(os.environ, FIXTURE_LINUX="1" if index % 2 else "")
                return subprocess.run([str(links[index])], env=env, capture_output=True,
                                      text=True, check=True).stdout
            with ThreadPoolExecutor(max_workers=12) as pool:
                self.assertEqual(list(pool.map(invoke, range(12))),
                                 ["Linux\n" if i % 2 else "Darwin\n" for i in range(12)])
            links[0].unlink()
            links[0].write_text("replacement")
            self.assertEqual(shared.read_text(), UNAME)
            self.assertEqual(links[1].read_text(), UNAME)
            links[1].unlink()
            self.assertTrue(shared.exists())

    def test_activity_fixture_links_and_override_are_isolated(self) -> None:
        from codex.test_activity import ActivityFixture

        class Fixture(ActivityFixture):
            pass

        Fixture.setUpClass()
        first, second = Fixture(), Fixture()
        try:
            first.setUp()
            second.setUp()
            first_stub, second_stub = first.bin / "uname", second.bin / "uname"
            self.assertTrue(first_stub.is_symlink())
            self.assertEqual(first_stub.stat().st_ino, second_stub.stat().st_ino)
            first.env["FIXTURE_LINUX"] = "1"
            results = [subprocess.run([str(path)], env=env, text=True, capture_output=True,
                                      check=True).stdout
                       for path, env in ((first_stub, first.env), (second_stub, second.env))]
            self.assertEqual(results, ["Linux\n", "Darwin\n"])
            first.shell_stub("uname", "echo overridden")
            self.assertFalse(first_stub.is_symlink())
            self.assertEqual(second_stub.read_text(), UNAME)
        finally:
            first.doCleanups()
            second.doCleanups()
            Fixture.doClassCleanups()
