"""Private executable cache validates contents and concurrent publication."""
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from pathlib import Path

from claude.hooks.tests.fixture_code_cache import cached_executable


class FixtureCodeCacheTests(unittest.TestCase):
    def test_concurrent_publication_and_content_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "cache"
            body = "#!/bin/bash\nprintf '%s\\n' \"$1\"\n"
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(cached_executable, repeat(body, 24), repeat(root, 24)))
            self.assertEqual(len(set(paths)), 1)
            self.assertEqual(subprocess.run([str(paths[0]), "雪 ' quote"], capture_output=True,
                                            text=True, check=True).stdout, "雪 ' quote\n")
            other = cached_executable(body + "# changed\n", root)
            self.assertNotEqual(paths[0], other)
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_interpreter_replacement_invalidates_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            interpreter = root / "interpreter"
            interpreter.write_bytes(b"first")
            body = f"#!{interpreter}\nfixture\n"
            first = cached_executable(body, root / "cache")
            replacement = root / "replacement"
            replacement.write_bytes(b"second")
            replacement.replace(interpreter)
            second = cached_executable(body, root / "cache")
            self.assertNotEqual(first, second)

    def test_concurrent_processes_publish_one_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "cache"
            program = ("from pathlib import Path; from claude.hooks.tests.fixture_code_cache "
                       "import cached_executable; import sys; "
                       "print(cached_executable('#!/bin/bash\\nexit 0\\n', Path(sys.argv[1])))")
            processes = [subprocess.Popen([sys.executable, "-B", "-c", program, str(root)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                         for _ in range(3)]
            results = [process.communicate() for process in processes]
            self.assertTrue(all(process.returncode == 0 for process in processes), results)
            self.assertEqual(len({output for output, _ in results}), 1)
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_rejects_symlinks_and_untrusted_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            link = root / "link"
            link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                cached_executable("#!/bin/bash\nexit 0\n", link)
            cache = root / "cache"
            body = "#!/bin/bash\nexit 0\n"
            path = cached_executable(body, cache)
            path.unlink()
            path.symlink_to(outside)
            with self.assertRaises(OSError):
                cached_executable(body, cache)

    def test_rejects_corrupted_cached_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            body = "#!/bin/bash\nexit 0\n"
            path = cached_executable(body, cache)
            path.unlink()
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o500)
            with os.fdopen(fd, "w") as stream:
                stream.write("corrupt")
            with self.assertRaises(RuntimeError):
                cached_executable(body, cache)
