"""Run discovered unittest groups in isolated, bounded processes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover(root):
    return list(flatten(unittest.TestLoader().discover(root, pattern="test_*.py")))


def groups(tests):
    result = {}
    for index, test in enumerate(tests):
        cls = type(test)
        module = sys.modules.get(cls.__module__)
        # Module fixtures and custom collection must run together in their original order.
        whole_module = module and any(hasattr(module, name) for name in
                                      ("setUpModule", "tearDownModule", "load_tests"))
        key = cls.__module__ if whole_module else f"{cls.__module__}.{cls.__qualname__}"
        result.setdefault(key, []).append(index)
    return result


def cleanup_sockets(directory):
    tmux = shutil.which("tmux")
    if not tmux:
        return not any(Path(directory).iterdir())
    clean = True
    for path in Path(directory).iterdir():
        try:
            if not stat.S_ISSOCK(path.lstat().st_mode):
                clean = False
                continue
            subprocess.run([tmux, "-S", str(path), "kill-server"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            path.unlink(missing_ok=True)
        except (OSError, subprocess.TimeoutExpired):
            clean = False
    return clean and not any(Path(directory).iterdir())


def stop_workers(active):
    # A leader may have exited while its process group still has descendants.
    processes = list(active)
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        remaining = False
        for process in processes:
            process.poll()  # Reap an exited leader before checking the group.
            try:
                os.killpg(process.pid, 0)
                remaining = True
            except ProcessLookupError:
                pass
        if not remaining:
            break
        time.sleep(0.02)
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-directory", default="codex")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args()
    tests = discover(args.start_directory)
    if args.worker is not None:
        selected = [tests[int(index)] for index in args.worker.split(",")]
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
        Path(os.environ["CODEX_TEST_RESULT"]).write_text(json.dumps({"count": result.testsRun}))
        return 0 if result.wasSuccessful() else 1
    pending = list(groups(tests).items())
    limit = min(4, os.cpu_count() or 1, max(1, len(pending)))
    active = {}
    failed = False
    interrupted = False

    def interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True

    old_handlers = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGINT, signal.SIGTERM)}
    with tempfile.TemporaryDirectory(prefix="ct-") as directory:
        env = os.environ.copy()
        socket_dir = Path(directory) / "s"
        socket_dir.mkdir()
        env["CODEX_TEST_TMUX_DIR"] = str(socket_dir)
        try:
            while (pending or active) and not interrupted:
                while pending and len(active) < limit and not interrupted:
                    name, indexes = pending.pop(0)
                    print(f"START {name} ({len(indexes)} tests)", flush=True)
                    cmd = [sys.executable, "-B", str(Path(__file__).resolve()),
                           "--start-directory", args.start_directory,
                           "--worker", ",".join(map(str, indexes))]
                    worker_env = env.copy()
                    result_file = Path(directory) / f"result-{indexes[0]}.json"
                    worker_env["CODEX_TEST_RESULT"] = str(result_file)
                    process = subprocess.Popen(cmd, env=worker_env, start_new_session=True)
                    active[process] = (name, result_file)
                for process, (name, result_file) in list(active.items()):
                    code = process.poll()
                    if code is not None:
                        print(f"END {name}: exit {code}", flush=True)
                        try:
                            result = json.loads(result_file.read_text())
                            failed |= not isinstance(result["count"], int)
                        except (OSError, ValueError, KeyError, TypeError):
                            print(f"Missing or invalid result: {name}", flush=True)
                            failed = True
                        failed |= code != 0
                        stop_workers([process])
                        del active[process]
                if active:
                    time.sleep(0.02)
        finally:
            stop_workers(active)
            failed |= not cleanup_sockets(socket_dir)
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
    return int(failed or interrupted)


if __name__ == "__main__":
    sys.exit(main())
