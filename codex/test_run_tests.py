"""Behavioral checks for the isolated unittest runner."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid

RUNNER = Path(__file__).with_name("run_tests.py")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self, name, source):
        (self.root / (name + ".py")).write_text(textwrap.dedent(source))

    def run_fixture(self):
        return subprocess.run([sys.executable, "-B", str(RUNNER), "--start-directory", str(self.root)],
                              text=True, capture_output=True, timeout=15)

    def test_discovery_and_class_fixtures(self):
        self.module("test_example", '''
            import unittest
            class Example(unittest.TestCase):
                @classmethod
                def setUpClass(cls): cls.value = []
                def test_a(self): self.value.append(1)
                def test_b(self): self.assertEqual(self.value, [1])
        ''')
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("test_example.Example.test_a", result.stdout + result.stderr)
        self.assertIn("test_example.Example.test_b", result.stdout + result.stderr)

    def test_failure_error_and_import_error_fail(self):
        self.module("test_bad", '''
            import unittest
            class Bad(unittest.TestCase):
                def test_fail(self): self.fail("failure marker")
                def test_error(self): raise RuntimeError("error marker")
        ''')
        self.module("test_import", 'raise RuntimeError("import marker")')
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        for marker in ("failure marker", "error marker", "import marker"):
            self.assertIn(marker, result.stdout + result.stderr)

    def test_module_fixtures_and_process_isolation(self):
        for name in ("test_first", "test_second"):
            self.module(name, '''
                import os, unittest
                def setUpModule(): os.environ["RUNNER_FIXTURE"] = "module"
                def tearDownModule(): del os.environ["RUNNER_FIXTURE"]
                class First(unittest.TestCase):
                    def test_one(self): self.assertEqual(os.environ["RUNNER_FIXTURE"], "module")
                class Second(unittest.TestCase):
                    def test_two(self): self.assertEqual(os.environ["RUNNER_FIXTURE"], "module")
            ''')
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_worker_result_is_failure(self):
        self.module("test_crash", "import os, unittest\nclass Crash(unittest.TestCase):\n def test_exit(self): os._exit(0)\n")
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing or invalid result", result.stdout)

    def test_worker_limit(self):
        for number in range(6):
            self.module(f"test_slot_{number}", f"""
                import fcntl, pathlib, time, unittest
                root = pathlib.Path({str(self.root)!r})
                class Slot(unittest.TestCase):
                    def test_slot(self):
                        with (root / 'lock').open('a') as lock:
                            fcntl.flock(lock, fcntl.LOCK_EX)
                            active = list(root.glob('active-*'))
                            self.assertLess(len(active), 4)
                            marker = root / 'active-{number}'
                            marker.touch()
                            fcntl.flock(lock, fcntl.LOCK_UN)
                            try: time.sleep(0.15)
                            finally: marker.unlink()
            """)
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(self.root.glob("active-*"))), 0)

    def test_interruption_terminates_worker_group(self):
        self.module("test_wait", f"""
            import pathlib, subprocess, sys, time, unittest
            class Wait(unittest.TestCase):
                def test_wait(self):
                    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
                    pathlib.Path({str(self.root / 'child')!r}).write_text(str(child.pid))
                    time.sleep(30)
        """)
        import signal
        import time
        process = subprocess.Popen([sys.executable, "-B", str(RUNNER), "--start-directory", str(self.root)],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "child").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / "child").exists())
            child = int((self.root / "child").read_text())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_interruption_cleans_only_owned_tmux_server(self):
        import shutil
        import signal
        import time
        tmux = shutil.which("tmux")
        if tmux is None:
            self.skipTest("tmux unavailable")
        inherited = os.environ.get("CODEX_TEST_TMUX_DIR")
        foreign = Path(inherited) / ("f" + uuid.uuid4().hex[:12]) if inherited else self.root / "foreign.sock"
        self.addCleanup(lambda: subprocess.run([tmux, "-S", str(foreign), "kill-server"],
                                                capture_output=True))
        subprocess.run([tmux, "-S", str(foreign), "new-session", "-d", "sleep 30"], check=True)
        self.module("test_server", f"""
            import os, pathlib, subprocess, time, unittest
            class Server(unittest.TestCase):
                def test_wait(self):
                    socket = pathlib.Path(os.environ['CODEX_TEST_TMUX_DIR']) / 'owned.sock'
                    subprocess.run([{tmux!r}, '-S', str(socket), 'new-session', '-d', 'sleep 30'], check=True)
                    pathlib.Path({str(self.root / 'socket-path')!r}).write_text(str(socket))
                    time.sleep(30)
        """)
        process = subprocess.Popen([sys.executable, "-B", str(RUNNER), "--start-directory", str(self.root)],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "socket-path").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / "socket-path").exists())
            owned = Path((self.root / "socket-path").read_text())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(owned.exists())
            self.assertEqual(subprocess.run([tmux, "-S", str(foreign), "has-session"],
                                            capture_output=True).returncode, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_unittest_result_categories(self):
        self.module("test_outcomes", """
            import unittest
            class Outcomes(unittest.TestCase):
                @unittest.skip('skip marker')
                def test_skip(self): pass
                @unittest.expectedFailure
                def test_expected(self): self.fail('expected marker')
                @unittest.expectedFailure
                def test_unexpected(self): pass
        """)
        result = self.run_fixture()
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        for marker in ("skipped", "expected failure", "unexpected success"):
            self.assertIn(marker, output)

    def test_interruption_kills_term_ignoring_descendant(self):
        import signal
        import time
        self.module("test_stubborn", f"""
            import pathlib, subprocess, sys, time, unittest
            class Stubborn(unittest.TestCase):
                def test_wait(self):
                    subprocess.Popen([sys.executable, '-c', {('import signal,time,pathlib; signal.signal(signal.SIGTERM, signal.SIG_IGN); pathlib.Path(' + repr(str(self.root / 'stubborn')) + ').write_text(str(__import__("os").getpid())); time.sleep(30)')!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(30)
        """)
        process = subprocess.Popen([sys.executable, '-B', str(RUNNER), '--start-directory', str(self.root)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        child = None
        try:
            deadline = time.monotonic() + 5
            while not (self.root / 'stubborn').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / 'stubborn').exists())
            child = int((self.root / 'stubborn').read_text())
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if child:
                try: os.kill(child, signal.SIGKILL)
                except ProcessLookupError: pass

    def test_finished_worker_cleans_descendant(self):
        import signal
        self.module("test_orphan", f"""
            import pathlib, subprocess, sys, time, unittest
            class Orphan(unittest.TestCase):
                def test_spawn(self):
                    path = pathlib.Path({str(self.root / 'orphan')!r})
                    subprocess.Popen([sys.executable, '-c', {('import signal,time,pathlib,os; signal.signal(signal.SIGTERM, signal.SIG_IGN); pathlib.Path(' + repr(str(self.root / 'orphan')) + ').write_text(str(os.getpid())); time.sleep(30)')!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    deadline = time.monotonic() + 5
                    while not path.exists() and time.monotonic() < deadline: time.sleep(0.02)
                    self.assertTrue(path.exists())
        """)
        child = None
        try:
            result = self.run_fixture()
            self.assertTrue((self.root / 'orphan').exists())
            child = int((self.root / 'orphan').read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            if child:
                try: os.kill(child, signal.SIGKILL)
                except ProcessLookupError: pass

    def test_outer_interruption_cleans_nested_regression_server(self):
        import shutil
        import signal
        import time
        tmux = shutil.which('tmux')
        if tmux is None:
            self.skipTest('tmux unavailable')
        inherited = os.environ.get('CODEX_TEST_TMUX_DIR')
        unrelated = Path(inherited) / ('u' + uuid.uuid4().hex[:12]) if inherited else self.root / 'unrelated.sock'
        self.addCleanup(lambda: subprocess.run([tmux, '-S', str(unrelated), 'kill-server'], capture_output=True))
        subprocess.run([tmux, '-S', str(unrelated), 'new-session', '-d', 'sleep 30'], check=True)
        self.module('test_outer', f'''
            import importlib.util, os, pathlib, subprocess, time, unittest
            spec = importlib.util.spec_from_file_location('nested_checks', {str(Path(__file__).resolve())!r})
            checks = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checks)
            class Outer(unittest.TestCase):
                def test_nested(self):
                    original = subprocess.run
                    def instrument(args, *a, **kw):
                        result = original(args, *a, **kw)
                        if 'new-session' in args and str(args[0]) == {tmux!r}:
                            pathlib.Path({str(self.root / 'nested-socket')!r}).write_text(str(args[2]))
                            time.sleep(30)
                        return result
                    subprocess.run = instrument
                    case = checks.RunnerTests('test_interruption_cleans_only_owned_tmux_server')
                    result = unittest.TestResult()
                    case.run(result)
                    self.assertTrue(result.wasSuccessful())
        ''')
        process = subprocess.Popen([sys.executable, '-B', str(RUNNER), '--start-directory', str(self.root)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        owned = None
        try:
            deadline = time.monotonic() + 5
            while not (self.root / 'nested-socket').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / 'nested-socket').exists())
            owned = Path((self.root / 'nested-socket').read_text())
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertNotEqual(subprocess.run([tmux, '-S', str(owned), 'has-session'], capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run([tmux, '-S', str(unrelated), 'has-session'], capture_output=True).returncode, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if owned:
                subprocess.run([tmux, '-S', str(owned), 'kill-server'], capture_output=True)

    def test_external_interrupt_cleans_nested_neighbor(self):
        import shutil
        import signal
        import time
        tmux = shutil.which('tmux')
        if tmux is None:
            self.skipTest('tmux unavailable')
        inherited = os.environ.get('CODEX_TEST_TMUX_DIR')
        neighbor = Path(inherited) / ('n' + uuid.uuid4().hex[:12]) if inherited else self.root / 'neighbor.sock'
        self.addCleanup(lambda: subprocess.run([tmux, '-S', str(neighbor), 'kill-server'], capture_output=True))
        subprocess.run([tmux, '-S', str(neighbor), 'new-session', '-d', 'sleep 30'], check=True)
        self.module('test_deep', f'''
            import importlib.util, pathlib, subprocess, time, unittest
            spec = importlib.util.spec_from_file_location('nested_checks', {str(Path(__file__).resolve())!r})
            checks = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checks)
            class Deep(unittest.TestCase):
                def test_nested(self):
                    original = subprocess.run
                    def instrument(args, *a, **kw):
                        result = original(args, *a, **kw)
                        if 'new-session' in args and str(args[0]) == {tmux!r}:
                            pathlib.Path({str(self.root / 'deep-socket')!r}).write_text(str(args[2]))
                            time.sleep(30)
                        return result
                    subprocess.run = instrument
                    checks.RunnerTests('test_outer_interruption_cleans_nested_regression_server').run(unittest.TestResult())
        ''')
        process = subprocess.Popen([sys.executable, '-B', str(RUNNER), '--start-directory', str(self.root)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        owned = None
        try:
            deadline = time.monotonic() + 5
            while not (self.root / 'deep-socket').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / 'deep-socket').exists())
            owned = Path((self.root / 'deep-socket').read_text())
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertNotEqual(subprocess.run([tmux, '-S', str(owned), 'has-session'], capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run([tmux, '-S', str(neighbor), 'has-session'], capture_output=True).returncode, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if owned:
                subprocess.run([tmux, '-S', str(owned), 'kill-server'], capture_output=True)
