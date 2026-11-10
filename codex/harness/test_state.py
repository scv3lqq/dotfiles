"""Behavioral tests for artifact-backed harness checkpoints."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("state.py")


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "plan.md").write_text("approved scope\n", encoding="utf-8")
        (self.root / "source.txt").write_text("implementation\n", encoding="utf-8")

    def call(self, *args: str, ok: bool = True) -> dict:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], cwd=self.root,
            capture_output=True, text=True, check=False,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return {}

    def init(self, run: str = "one") -> dict:
        return self.call("init", run, "--plan", "plan.md", "--approval", "approved")

    def checkpoint(self, run: str, revision: int, status: str, *extra: str,
                   ok: bool = True) -> dict:
        return self.call("checkpoint", run, "--expect-revision", str(revision),
                         "--status", status, "--summary", "checkpoint", *extra, ok=ok)

    def detail(self, run: str = "one") -> dict:
        path = self.root / ".harness" / "runs" / run / "state.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def artifact(self, relative: str, data: object, run: str = "one") -> None:
        path = self.root / ".harness" / "runs" / run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data) if not isinstance(data, str) else data,
                        encoding="utf-8")

    def report(self, path: str, verdict: str, *, run: str = "one",
               hashes: dict | None = None, findings: list | None = None,
               checks: list | None = None) -> None:
        if hashes is None:
            hashes = self.detail(run)["source_hashes"]
        self.artifact(path, {"verdict": verdict, "source_hashes": hashes,
                             "findings": findings or [], "checks": checks or [],
                             "not_run": []}, run)

    def reviewing(self, run: str = "one") -> dict:
        self.init(run)
        self.checkpoint(run, 0, "implementing")
        self.checkpoint(run, 1, "reviewing", "--bind", "source.txt")
        return self.detail(run)

    def test_init_collision_and_missing_run(self) -> None:
        state = self.init()
        self.assertEqual((state["revision"], state["iteration"], state["status"]),
                         (0, 0, "approved"))
        self.call("init", "one", "--plan", "plan.md", "--approval", "approved", ok=False)
        self.call("show", "missing", ok=False)
        self.call("init", "../escape", "--plan", "plan.md", "--approval", "x", ok=False)
        self.call("init", "two", "--plan", "plan.md", "--approval", "", ok=False)

    def test_happy_lifecycle_and_terminal_refusal(self) -> None:
        self.reviewing()
        self.report("review.json", "ACCEPT")
        self.checkpoint("one", 2, "validating", "--report", "review.json")
        self.report("validation.json", "PASS")
        self.checkpoint("one", 3, "retrospective", "--report", "validation.json")
        for name in ("retrospective.md", "knowledge.md", "proposals.md"):
            self.artifact(name, "evidence")
        state = self.checkpoint("one", 4, "completed", "--artifact", "retrospective.md",
                                "--artifact", "knowledge.md", "--artifact", "proposals.md")
        self.assertEqual(state["status"], "completed")
        self.call("verify", "one")
        self.checkpoint("one", 5, "implementing", ok=False)
        self.call("resume", "one", "--expect-revision", "5", "--approval", "yes", ok=False)

    def test_traversal_and_symlink_escape(self) -> None:
        self.init()
        self.checkpoint("one", 0, "implementing")
        self.checkpoint("one", 1, "reviewing", "--bind", "../escape", ok=False)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "outside").symlink_to(outside, target_is_directory=True)
            self.checkpoint("one", 1, "reviewing", "--bind", "outside/file", ok=False)
            self.artifact("safe.txt", "ok")
            run = self.root / ".harness/runs/one"
            (run / "escape").symlink_to(outside, target_is_directory=True)
            (Path(outside) / "artifact").write_text("private", encoding="utf-8")
            self.checkpoint("one", 1, "reviewing", "--bind", "source.txt",
                            "--artifact", "escape/artifact", ok=False)

    def test_plan_and_artifact_tampering_are_rejected(self) -> None:
        self.init()
        self.artifact("note.txt", "first")
        self.checkpoint("one", 0, "implementing", "--artifact", "note.txt")
        self.artifact("note.txt", "changed")
        self.call("verify", "one", ok=False)
        self.checkpoint("one", 1, "reviewing", "--bind", "source.txt", ok=False)
        self.artifact("note.txt", "first")
        (self.root / ".harness/runs/one/plan.md").write_text("changed", encoding="utf-8")
        self.call("verify", "one", ok=False)

    def test_source_drift_can_be_blocked_but_not_rebased(self) -> None:
        before = self.reviewing()
        (self.root / "source.txt").write_text("drift", encoding="utf-8")
        self.call("verify", "one", ok=False)
        self.checkpoint("one", 2, "blocked")
        blocked = self.detail()
        self.assertEqual(blocked["blocked_from"], "reviewing")
        self.assertEqual(blocked["source_hashes"], before["source_hashes"])
        self.assertTrue(blocked["integrity_errors"])
        self.call("resume", "one", "--expect-revision", "3", "--approval", "yes", ok=False)
        self.artifact("retrospective.md", "failed after drift")
        self.checkpoint("one", 3, "blocked", "--artifact", "retrospective.md")
        after = self.detail()
        self.assertEqual(after["integrity_errors"], blocked["integrity_errors"])
        self.assertEqual(after["source_hashes"], before["source_hashes"])
        self.checkpoint("one", 4, "blocked", "--bind", "source.txt", ok=False)

    def test_resume_preserves_progress_and_requires_approval(self) -> None:
        self.init()
        self.checkpoint("one", 0, "implementing")
        self.artifact("progress.md", "already done")
        self.checkpoint("one", 1, "blocked", "--artifact", "progress.md")
        self.call("resume", "one", "--expect-revision", "2", "--approval", "", ok=False)
        self.call("resume", "one", "--expect-revision", "2", "--approval", "continue")
        state = self.detail()
        self.assertEqual((state["status"], state["iteration"], state["approval"]),
                         ("implementing", 1, "approved"))
        self.assertEqual(state["resume_approval"], "continue")
        self.assertIn("progress.md", state["artifacts"])

    def test_stale_revision_invalid_transition_and_no_overwrite(self) -> None:
        self.init()
        path = self.root / ".harness/runs/one/state.json"
        before = path.read_bytes()
        self.checkpoint("one", 3, "implementing", ok=False)
        self.checkpoint("one", 0, "validating", ok=False)
        self.assertEqual(path.read_bytes(), before)

    def test_malformed_state_is_a_concise_failure(self) -> None:
        self.init()
        path = self.root / ".harness/runs/one/state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["status"] = []
        path.write_text(json.dumps(state), encoding="utf-8")
        self.call("show", "one", ok=False)

    def test_three_round_limit(self) -> None:
        self.reviewing()
        self.report("review-1.json", "REJECT")
        self.checkpoint("one", 2, "implementing", "--report", "review-1.json")
        self.checkpoint("one", 3, "reviewing", "--bind", "source.txt")
        self.report("review-2.json", "REJECT")
        self.checkpoint("one", 4, "implementing", "--report", "review-2.json")
        self.checkpoint("one", 5, "reviewing", "--bind", "source.txt")
        self.report("review-3.json", "REJECT")
        self.checkpoint("one", 6, "implementing", "--report", "review-3.json", ok=False)
        self.assertEqual(self.call("show", "one")["iteration"], 3)

    def test_active_count_includes_blocked_beyond_display_limit(self) -> None:
        for index in range(12):
            self.init(f"run-{index:02d}")
        self.checkpoint("run-00", 0, "blocked")
        result = self.call("show")
        self.assertEqual(result["total_runs"], 12)
        self.assertEqual(result["active_count"], 12)
        self.assertEqual(len(result["runs"]), 10)

    def test_active_run_id_includes_older_hidden_run(self) -> None:
        self.assertIsNone(self.call("show")["active_run_id"])
        self.init("old-active")
        old_state = self.root / ".harness/runs/old-active/state.json"
        os.utime(old_state, ns=(1, 1))
        for index in range(10):
            run = f"new-completed-{index}"
            self.init(run)
            path = self.root / ".harness/runs" / run / "state.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            state["status"] = "completed"
            path.write_text(json.dumps(state), encoding="utf-8")
        result = self.call("show")
        self.assertEqual(result["active_count"], 1)
        self.assertEqual(result["active_run_id"], "old-active")
        self.assertNotIn("old-active", [item["run_id"] for item in result["runs"]])
        self.init("new-active")
        self.assertIsNone(self.call("show")["active_run_id"])

    def test_listing_isolates_partial_and_malformed_runs(self) -> None:
        self.init("good")
        runs = self.root / ".harness/runs"
        partial = runs / "00-partial"
        partial.mkdir()
        (partial / ".lock").write_text("", encoding="utf-8")
        (partial / "plan.md").write_text("approved", encoding="utf-8")
        malformed = runs / "01-malformed"
        malformed.mkdir()
        (malformed / ".lock").write_text("", encoding="utf-8")
        (malformed / "plan.md").write_text("approved", encoding="utf-8")
        (malformed / "state.json").write_text("{invalid", encoding="utf-8")

        listing = self.call("show")
        self.assertEqual(listing["total_runs"], 3)
        self.assertEqual(listing["active_count"], 3)
        self.assertIsNone(listing["active_run_id"])
        self.assertEqual(listing["unreadable_count"], 2)
        self.assertEqual({item["run_id"] for item in listing["unreadable_runs"]},
                         {"00-partial", "01-malformed"})
        self.assertEqual([item["run_id"] for item in listing["runs"]], ["good"])
        self.assertEqual(self.call("show", "good")["run_id"], "good")
        self.assertTrue(self.call("verify", "good")["verified"])
        self.assertFalse((partial / "state.json").exists())
        self.assertEqual((malformed / "state.json").read_text(encoding="utf-8"), "{invalid")

        for index in range(10):
            (runs / f"z-incomplete-{index}").mkdir()
        bounded = self.call("show")
        self.assertEqual((bounded["total_runs"], bounded["active_count"],
                          bounded["unreadable_count"]), (13, 13, 12))
        self.assertEqual(len(bounded["unreadable_runs"]), 10)
        self.assertTrue(all(len(item["error"]) <= 240 for item in bounded["unreadable_runs"]))

    def test_report_verdict_hash_and_shape_guards(self) -> None:
        state = self.reviewing()
        self.checkpoint("one", 2, "validating", ok=False)
        self.report("rejected.json", "REJECT")
        self.checkpoint("one", 2, "validating", "--report", "rejected.json", ok=False)
        self.report("wrong.json", "ACCEPT", hashes={"source.txt": {"kind": "absent"}})
        self.checkpoint("one", 2, "validating", "--report", "wrong.json", ok=False)
        self.report("blocking.json", "ACCEPT", findings=[{"id": "F1", "severity": "blocking", "summary": "bad"}])
        self.checkpoint("one", 2, "validating", "--report", "blocking.json", ok=False)
        self.artifact("malformed.json", {"verdict": "ACCEPT", "source_hashes": state["source_hashes"]})
        self.checkpoint("one", 2, "validating", "--report", "malformed.json", ok=False)
        self.report("ok.json", "ACCEPT")
        self.checkpoint("one", 2, "validating", "--report", "ok.json")
        self.report("failed-check.json", "PASS", checks=[{"command": "x", "exit_code": 1, "result": "bad"}])
        self.checkpoint("one", 3, "retrospective", "--report", "failed-check.json", ok=False)

    def test_deletion_symlink_and_fingerprint_consistency(self) -> None:
        (self.root / "target.txt").write_text("target", encoding="utf-8")
        (self.root / "link.txt").symlink_to("target.txt")
        first = self.call("fingerprint", "source.txt", "gone.txt", "link.txt")
        self.assertEqual(first["gone.txt"], {"kind": "absent"})
        self.assertEqual(first["link.txt"]["kind"], "symlink")
        self.init()
        self.checkpoint("one", 0, "implementing")
        self.checkpoint("one", 1, "reviewing", "--bind", "source.txt", "--bind", "gone.txt", "--bind", "link.txt")
        state = self.detail()
        self.assertEqual(state["source_hashes"], first)
        (self.root / "gone.txt").write_text("returned", encoding="utf-8")
        self.call("verify", "one", ok=False)
        (self.root / "gone.txt").unlink()
        (self.root / "link.txt").unlink()
        (self.root / "link.txt").symlink_to("source.txt")
        self.call("verify", "one", ok=False)

    def test_compact_outputs_do_not_grow_with_evidence(self) -> None:
        expected_keys = {"schema_version", "run_id", "revision", "status", "iteration",
                         "summary", "state_path", "plan_path", "artifact_count",
                         "source_count", "blocked_from", "integrity_error_count"}

        def check_envelope(value: dict, *, verified: bool = False) -> None:
            self.assertEqual(set(value), expected_keys | ({"verified"} if verified else set()))
            self.assertLess(len(json.dumps(value, ensure_ascii=False).encode()), 2000)
            self.assertLessEqual(len(value["summary"]), 240)
            self.assertEqual(value["state_path"], ".harness/runs/one/state.json")
            self.assertEqual(value["plan_path"], ".harness/runs/one/plan.md")
            for key in ("approval", "resume_approval", "source_hashes", "artifacts"):
                self.assertNotIn(key, value)

        check_envelope(self.init())
        artifact_args: list[str] = []
        for index in range(64):
            name = f"reports/{index}.txt"
            self.artifact(name, "evidence")
            artifact_args += ["--artifact", name]
        check_envelope(self.call("checkpoint", "one", "--expect-revision", "0",
                                 "--status", "implementing", "--summary", "x" * 1000,
                                 *artifact_args))
        bind_args: list[str] = []
        for index in range(128):
            name = f"source-{index}.txt"
            (self.root / name).write_text(str(index), encoding="utf-8")
            bind_args += ["--bind", name]
        review = self.checkpoint("one", 1, "reviewing", *bind_args)
        check_envelope(review)
        self.assertEqual((review["artifact_count"], review["source_count"]), (64, 128))
        check_envelope(self.call("show", "one"))
        check_envelope(self.call("verify", "one"), verified=True)
        check_envelope(self.checkpoint("one", 2, "blocked"))
        check_envelope(self.call("resume", "one", "--expect-revision", "3",
                                 "--approval", "approved resumption"))
        listed = self.call("show")
        check_envelope(listed["runs"][0])


class PortableStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def command(self, cwd: Path, *args: str, env: dict[str, str] | None = None,
                ok: bool = True) -> dict:
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=cwd,
                                env=env, capture_output=True, text=True, check=False)
        if not ok:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            return {}
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def git_init(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       capture_output=True, text=True)

    def test_plain_and_explicit_root_and_missing_git(self) -> None:
        nested = self.root / "nested"
        nested.mkdir()
        plain = self.command(nested, "prepare")
        self.assertEqual(plain["working_root"], str(nested))
        self.assertEqual((nested / ".harness/.gitignore").read_bytes(), b"/runs/\n/staging/\n")
        self.assertTrue(plain["ignore_created"])
        self.assertFalse((nested / ".harness/runs").exists())
        explicit = self.command(nested, "--root", str(self.root), "prepare")
        self.assertEqual(explicit["working_root"], str(self.root))
        missing = self.root / "missing-git"
        missing.mkdir()
        environment = dict(os.environ)
        environment["PATH"] = ""
        result = self.command(missing, "prepare", env=environment)
        self.assertEqual(result["working_root"], str(missing))
        self.assertIsNone(result["ignored"])
        self.assertFalse((missing / ".harness/runs").exists())
        self.command(nested, "--root", str(self.root / "absent"), "prepare", ok=False)

    def test_nested_git_root_and_runtime_ignore(self) -> None:
        self.git_init()
        nested = self.root / "deep" / "nested"
        nested.mkdir(parents=True)
        result = self.command(nested, "prepare")
        self.assertEqual(result["working_root"], str(self.root))
        self.assertTrue(result["ignored"])
        self.assertFalse((nested / ".harness").exists())
        self.assertEqual((self.root / ".harness/.gitignore").read_bytes(), b"/runs/\n/staging/\n")
        self.assertFalse((self.root / ".harness/runs").exists())
        self.assertFalse((self.root / ".harness/staging").exists())
        (self.root / ".harness/staging").mkdir()
        (self.root / ".harness/staging/approved.md").write_text("approved", encoding="utf-8")
        state = self.command(nested, "init", "nested", "--plan", ".harness/staging/approved.md",
                             "--approval", "yes")
        self.assertEqual(state["status"], "approved")
        self.assertTrue((self.root / ".harness/runs/nested/state.json").is_file())

    def test_existing_ignore_preserved_and_negation_rejected(self) -> None:
        self.git_init()
        harness = self.root / ".harness"
        harness.mkdir()
        ignore = harness / ".gitignore"
        existing = b"# user data\n/runs/\n/staging/\n"
        ignore.write_bytes(existing)
        result = self.command(self.root, "prepare")
        self.assertFalse(result["ignore_created"])
        self.assertEqual(ignore.read_bytes(), existing)
        conflicting = b"/runs/\n/staging/\n!/runs/\n!/runs/**\n"
        ignore.write_bytes(conflicting)
        self.command(self.root, "prepare", ok=False)
        self.assertEqual(ignore.read_bytes(), conflicting)
        self.assertFalse((harness / "runs").exists())

    def test_sentinel_only_ignore_does_not_hide_real_runtime_data(self) -> None:
        self.git_init()
        harness = self.root / ".harness"
        harness.mkdir()
        ignore = harness / ".gitignore"
        existing = b"/runs/.harness-ignore-probe\n/staging/.harness-ignore-probe\n"
        ignore.write_bytes(existing)
        self.command(self.root, "prepare", ok=False)
        self.assertEqual(ignore.read_bytes(), existing)

    def test_unignored_existing_runtime_data_is_not_hidden(self) -> None:
        self.git_init()
        data = self.root / ".harness/runs/foreign.txt"
        data.parent.mkdir(parents=True)
        data.write_text("foreign data", encoding="utf-8")
        self.command(self.root, "prepare", ok=False)
        self.assertFalse((self.root / ".harness/.gitignore").exists())
        self.assertEqual(data.read_text(encoding="utf-8"), "foreign data")

    def test_git_ignore_error_rolls_back_new_metadata(self) -> None:
        binary = self.root / "bin"
        binary.mkdir()
        fake = binary / "git"
        fake.write_text("#!/bin/sh\nif [ \"$3\" = rev-parse ]; then printf '%s\\n' \"$2\"; exit 0; fi\nexit 128\n", encoding="utf-8")
        fake.chmod(0o755)
        target = self.root / "project"
        target.mkdir()
        environment = dict(os.environ)
        environment["PATH"] = str(binary)
        self.command(target, "prepare", env=environment, ok=False)
        self.assertFalse((target / ".harness").exists())

    def test_missing_git_does_not_skip_checks_in_existing_git_repository(self) -> None:
        self.git_init()
        environment = dict(os.environ)
        environment["PATH"] = ""
        self.command(self.root, "prepare", env=environment, ok=False)
        self.assertFalse((self.root / ".harness").exists())

    def test_git_commands_are_bounded(self) -> None:
        spec = importlib.util.spec_from_file_location("harness_state_timeout_probe", SCRIPT)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 10)):
            with self.assertRaisesRegex(module.StateError, "timed out"):
                module.git_root(self.root)
            with self.assertRaisesRegex(module.StateError, "timed out"):
                module.git_ignored(self.root, ".harness/runs/")

    def test_foreign_and_symlink_runtime_paths_are_rejected(self) -> None:
        for name in (".harness", ".harness/runs", ".harness/staging", ".harness/.gitignore"):
            with self.subTest(path=name):
                with tempfile.TemporaryDirectory(dir=self.root) as raw:
                    root = Path(raw)
                    target = root / "local-target"
                    target.mkdir()
                    link = root / name
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(target, target_is_directory=True)
                    self.command(root, "prepare", ok=False)
                    self.assertTrue(link.is_symlink())
                    if name != ".harness/.gitignore":
                        self.assertFalse((root / ".harness/.gitignore").exists())
        with tempfile.TemporaryDirectory(dir=self.root) as raw:
            root = Path(raw)
            (root / ".harness").write_text("foreign", encoding="utf-8")
            self.command(root, "prepare", ok=False)
            self.assertEqual((root / ".harness").read_text(encoding="utf-8"), "foreign")

    def test_unexpected_git_failure_does_not_prepare(self) -> None:
        binary = self.root / "bin"
        binary.mkdir()
        fake = binary / "git"
        fake.write_text("#!/bin/sh\necho 'fatal: permission denied' >&2\nexit 128\n", encoding="utf-8")
        fake.chmod(0o755)
        target = self.root / "project"
        target.mkdir()
        environment = dict(os.environ)
        environment["PATH"] = str(binary)
        self.command(target, "prepare", env=environment, ok=False)
        self.assertFalse((target / ".harness").exists())


if __name__ == "__main__":
    unittest.main()
