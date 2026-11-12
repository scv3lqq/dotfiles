"""Ensure launch fixture code is shared without sharing per-test state."""
import unittest
from concurrent.futures import ThreadPoolExecutor

from codex import test_launch


class LaunchFixtureIsolationTests(unittest.TestCase):
    def test_shared_code_and_private_logs(self) -> None:
        test_launch.LaunchTests.setUpClass()
        first, second = test_launch.LaunchTests(), test_launch.LaunchTests()
        try:
            first.setUp()
            second.setUp()
            self.assertTrue((first.bin / "codex").is_symlink())
            self.assertEqual((first.bin / "codex").stat().st_ino,
                             (second.bin / "codex").stat().st_ino)
            self.assertNotEqual(first.log, second.log)
            with ThreadPoolExecutor(max_workers=2) as pool:
                first_run = pool.submit(first.launch, "first")
                second_run = pool.submit(second.launch, "second")
                self.assertEqual(first_run.result()[1], ["--no-daemon", "first"])
                self.assertEqual(second_run.result()[1], ["--no-daemon", "second"])
            (first.bin / "codex").unlink()
            self.assertTrue((second.bin / "codex").exists())
        finally:
            first.doCleanups()
            second.doCleanups()
            test_launch.LaunchTests.doClassCleanups()


class DateFixtureIsolationTests(unittest.TestCase):
    def test_date_output_and_override_are_private(self) -> None:
        import subprocess

        from codex import test_agent_inbox

        fixture = test_agent_inbox.Fixture
        fixture.setUpClass()
        first, second = fixture(), fixture()
        try:
            first.setUp()
            second.setUp()
            self.assertEqual((first.bin / "date").stat().st_ino,
                             (second.bin / "date").stat().st_ino)
            first.set_now(-42)
            for instance, expected in ((first, "-42\n"), (second, f"{test_agent_inbox.NOW}\n")):
                result = subprocess.run([str(instance.bin / "date"), "+%s"],
                                        capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout, expected)
            self.assertTrue((second.bin / "date").is_symlink())
        finally:
            first.doCleanups()
            second.doCleanups()
            fixture.doClassCleanups()
