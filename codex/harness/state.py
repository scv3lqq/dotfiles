#!/usr/bin/env python3
"""Store approved harness runs and verify immutable handoff evidence."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterator, TypedDict, cast
from contextlib import contextmanager


class StateError(ValueError):
    """A state operation cannot safely proceed."""


class Fingerprint(TypedDict, total=False):
    kind: str
    sha256: str
    target: str
    target_sha256: str | None


class RunState(TypedDict):
    schema_version: int
    run_id: str
    revision: int
    status: str
    iteration: int
    plan_sha256: str
    approval: str
    summary: str
    artifacts: dict[str, str]
    source_hashes: dict[str, Fingerprint]
    blocked_from: str | None
    resume_approval: str | None
    integrity_errors: list[str]


STATUSES = frozenset({"approved", "implementing", "reviewing", "validating",
                      "retrospective", "blocked", "completed"})
TRANSITIONS = {
    "approved": frozenset({"implementing", "blocked"}),
    "implementing": frozenset({"reviewing", "blocked"}),
    "reviewing": frozenset({"implementing", "validating", "blocked"}),
    "validating": frozenset({"implementing", "retrospective", "blocked"}),
    "retrospective": frozenset({"completed", "blocked"}),
    "blocked": frozenset({"blocked"}),
    "completed": frozenset(),
}
ARCHIVE_FILES = frozenset({"retrospective.md", "knowledge.md", "proposals.md"})
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def require_text(value: object, field: str, limit: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise StateError(f"{field} must be nonempty text of at most {limit} characters")
    return value


def require_run_id(value: str) -> str:
    if not RUN_ID.fullmatch(value):
        raise StateError("invalid run ID")
    return value


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def git_root(directory: Path) -> Path | None:
    """Resolve a Git root without changing trust or treating Git errors as non-Git."""
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, env=environment, timeout=10,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired as error:
        raise StateError("Git root discovery timed out") from error
    if result.returncode:
        if "not a git repository" in result.stderr.lower() and not os.environ.get("GIT_DIR"):
            return None
        raise StateError(f"Git root discovery failed (exit {result.returncode})")
    value = result.stdout.rstrip("\n")
    if not value:
        raise StateError("Git root discovery returned an empty path")
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise StateError("Git root discovery returned an invalid path") from error
    if not root.is_dir() or not inside(directory, root):
        raise StateError("Git root does not contain the working directory")
    return root


def working_root(value: str | None) -> Path:
    if value is None:
        cwd = Path.cwd().resolve()
        return git_root(cwd) or cwd
    try:
        root = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise StateError("working root must be an existing directory") from error
    if not root.is_dir():
        raise StateError("working root must be an existing directory")
    return root


def git_ignored(root: Path, path: str) -> bool:
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--no-index", "--quiet", "--", path],
            capture_output=True, text=True, check=False, env=environment, timeout=10,
        )
    except FileNotFoundError as error:
        raise StateError("Git is required to verify runtime ignore rules") from error
    except subprocess.TimeoutExpired as error:
        raise StateError("Git ignore verification timed out") from error
    if result.returncode not in (0, 1):
        raise StateError(f"Git ignore verification failed (exit {result.returncode})")
    return result.returncode == 0


def prepare(root: Path) -> dict[str, object]:
    """Prepare only the private runtime ignore rules after approval."""
    harness = root / ".harness"
    for directory in (harness, harness / "runs", harness / "staging"):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise StateError("harness runtime path must be a regular directory, not a symlink")
    ignore = harness / ".gitignore"
    if ignore.is_symlink() or (ignore.exists() and not ignore.is_file()):
        raise StateError("harness ignore path must be a regular file, not a symlink")

    repository = git_root(root)
    in_git = repository is not None
    if not in_git and (os.environ.get("GIT_DIR") or
                       any((parent / ".git").exists() for parent in (root, *root.parents))):
        raise StateError("Git is required to verify runtime ignore rules")
    sentinels = (".harness/runs/", ".harness/staging/")
    if in_git and not ignore.exists():
        for directory, sentinel in zip((harness / "runs", harness / "staging"), sentinels):
            if directory.exists() and next(directory.iterdir(), None) is not None:
                if not git_ignored(root, sentinel):
                    raise StateError("existing runtime data would become newly ignored")

    directory_created = False
    ignore_created = False
    created_identity: tuple[int, int] | None = None
    try:
        if not harness.exists():
            harness.mkdir(mode=0o700)
            directory_created = True
        if not ignore.exists():
            descriptor, temporary = tempfile.mkstemp(prefix=".harness-ignore-", dir=harness)
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(b"/runs/\n/staging/\n")
                    output.flush()
                    os.fsync(output.fileno())
                os.link(temporary, ignore)
                info = ignore.stat()
                created_identity = (info.st_dev, info.st_ino)
                ignore_created = True
            finally:
                os.unlink(temporary)
        ignored = all(git_ignored(root, path) for path in sentinels) if in_git else None
        if in_git and not ignored:
            raise StateError("existing ignore rules do not ignore both runtime paths")
        return {"working_root": str(root), "ignore_created": ignore_created, "ignored": ignored}
    except (OSError, StateError):
        if ignore_created and not ignore.is_symlink():
            try:
                info = ignore.stat()
                if (info.st_dev, info.st_ino) == created_identity:
                    ignore.unlink()
            except FileNotFoundError:
                pass
        if directory_created:
            try:
                harness.rmdir()
            except OSError:
                pass
        raise


def checked_path(root: Path, value: str) -> tuple[Path, str]:
    require_text(value, "path", 4096)
    relative = Path(value)
    if relative.is_absolute() or any(part in {"..", "."} for part in relative.parts):
        raise StateError("path must be relative and cannot traverse parents")
    if not relative.parts:
        raise StateError("empty path")
    try:
        parent = (root / relative).parent.resolve(strict=True)
        target = parent / relative.name
        if not inside(parent, root) or not inside(target.resolve(strict=False), root):
            raise StateError("path escapes its root")
    except (OSError, RuntimeError) as error:
        raise StateError(f"invalid path: {value}") from error
    return target, relative.as_posix()


def file_digest(path: Path) -> str:
    if not path.is_file():
        raise StateError(f"not a regular file: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(131072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(root: Path, value: str) -> Fingerprint:
    path, relative = checked_path(root, value)
    if relative == ".git" or relative.startswith(".git/") or (
        relative == ".harness/runs" or relative.startswith(".harness/runs/")
    ):
        raise StateError("source path cannot be Git metadata or harness runs")
    if path.is_symlink():
        target = os.readlink(path)
        resolved = path.resolve(strict=False)
        return {"kind": "symlink", "target": target,
                "target_sha256": file_digest(resolved) if resolved.is_file() else None}
    if not path.exists():
        return {"kind": "absent"}
    if not path.is_file():
        raise StateError(f"source path is not a regular file: {relative}")
    return {"kind": "file", "sha256": file_digest(path)}


def fingerprints(root: Path, values: list[str]) -> dict[str, Fingerprint]:
    if len(values) > 128:
        raise StateError("too many source paths")
    result: dict[str, Fingerprint] = {}
    for value in values:
        path, relative = checked_path(root, value)
        del path
        if relative in result:
            raise StateError(f"duplicate source path: {relative}")
        result[relative] = fingerprint(root, relative)
    return result


def runs_path(root: Path, create: bool = False) -> Path:
    current = root
    for name in (".harness", "runs"):
        candidate = current / name
        if candidate.is_symlink():
            raise StateError("harness storage cannot be a symlink")
        if create:
            candidate.mkdir(mode=0o700, exist_ok=True)
        if candidate.exists() and not candidate.is_dir():
            raise StateError("harness storage is not a directory")
        current = candidate
    return current


def run_path(root: Path, run_id: str) -> Path:
    path = runs_path(root) / require_run_id(run_id)
    if path.is_symlink() or not path.is_dir():
        raise StateError("run does not exist or is not a regular directory")
    return path


@contextmanager
def locked(run: Path, *, exclusive: bool) -> Iterator[None]:
    lock = run / ".lock"
    if lock.is_symlink() or not lock.is_file():
        raise StateError("run lock is missing or invalid")
    with lock.open("rb") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_json(path: Path, value: RunState) -> None:
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".state-", delete=False) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def load_state(run: Path, run_id: str) -> RunState:
    path = run / "state.json"
    if path.is_symlink() or not path.is_file():
        raise StateError("state file is missing or invalid")
    try:
        state: object = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StateError("invalid state JSON") from error
    fields = {"schema_version", "run_id", "revision", "status", "iteration", "plan_sha256",
              "approval", "summary", "artifacts", "source_hashes", "blocked_from",
              "resume_approval", "integrity_errors"}
    if not isinstance(state, dict) or set(state) != fields:
        raise StateError("invalid state fields")
    if type(state["schema_version"]) is not int or state["schema_version"] != 1 or state["run_id"] != run_id:
        raise StateError("invalid state identity")
    if (type(state["revision"]) is not int or state["revision"] < 0 or
            type(state["iteration"]) is not int or not 0 <= state["iteration"] <= 3 or
            not isinstance(state["status"], str) or state["status"] not in STATUSES):
        raise StateError("invalid state counters or status")
    if not isinstance(state["plan_sha256"], str) or not SHA256.fullmatch(state["plan_sha256"]):
        raise StateError("invalid approved plan hash")
    require_text(state["approval"], "approval")
    require_text(state["summary"], "summary")
    if not isinstance(state["artifacts"], dict) or not isinstance(state["source_hashes"], dict):
        raise StateError("invalid evidence map")
    if not isinstance(state["integrity_errors"], list) or not all(
        isinstance(item, str) for item in state["integrity_errors"]
    ):
        raise StateError("invalid integrity errors")
    if state["blocked_from"] is not None and (
        not isinstance(state["blocked_from"], str) or
        state["blocked_from"] not in STATUSES - {"blocked", "completed"}
    ):
        raise StateError("invalid blocked phase")
    if state["status"] == "blocked" and state["blocked_from"] is None:
        raise StateError("missing blocked phase")
    if state["resume_approval"] is not None:
        require_text(state["resume_approval"], "resume approval")
    return cast(RunState, state)


def artifact_digest(run: Path, relative: str) -> tuple[str, str]:
    path, normalized = checked_path(run, relative)
    if normalized in {"state.json", "plan.md", ".lock"} or normalized.startswith(".state-"):
        raise StateError("reserved artifact path")
    return normalized, file_digest(path)


def integrity_errors(root: Path, run: Path, state: RunState) -> list[str]:
    errors: list[str] = []
    try:
        plan = run / "plan.md"
        if plan.is_symlink() or file_digest(plan) != state["plan_sha256"]:
            errors.append("approved plan changed")
    except (OSError, StateError) as error:
        errors.append(f"approved plan invalid: {error}")
    for path, expected in state["artifacts"].items():
        try:
            if not isinstance(path, str) or not isinstance(expected, str):
                raise StateError("invalid artifact entry")
            if artifact_digest(run, path)[1] != expected:
                errors.append(f"artifact changed: {path}")
        except (OSError, StateError) as error:
            errors.append(f"artifact invalid: {path}: {error}")
    for path, expected in state["source_hashes"].items():
        try:
            if not isinstance(path, str) or not isinstance(expected, dict):
                raise StateError("invalid source entry")
            if fingerprint(root, path) != expected:
                errors.append(f"source changed: {path}")
        except (OSError, StateError) as error:
            errors.append(f"source invalid: {path}: {error}")
    return errors


def assert_integrity(root: Path, run: Path, state: RunState) -> None:
    errors = integrity_errors(root, run, state)
    if errors:
        raise StateError("; ".join(errors))


def add_artifacts(run: Path, state: RunState, values: list[str], *, new_only: bool = False) -> None:
    if len(values) > 128:
        raise StateError("too many artifacts")
    for value in values:
        path, digest = artifact_digest(run, value)
        previous = state["artifacts"].get(path)
        if previous is not None and (new_only or previous != digest):
            raise StateError(f"artifact is immutable: {path}")
        state["artifacts"][path] = digest


def check_report(run: Path, state: RunState, path: str, expected: str) -> None:
    report_path, _ = checked_path(run, path)
    try:
        report: object = json.loads(report_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StateError("invalid report JSON") from error
    if not isinstance(report, dict) or not {"verdict", "source_hashes", "findings", "checks", "not_run"} <= set(report):
        raise StateError("invalid report fields")
    if report["verdict"] != expected:
        raise StateError(f"report verdict must be {expected}")
    if not state["source_hashes"] or report["source_hashes"] != state["source_hashes"]:
        raise StateError("report source hashes do not match current bindings")
    findings, checks, not_run = report["findings"], report["checks"], report["not_run"]
    if not isinstance(findings, list) or not isinstance(checks, list) or not isinstance(not_run, list):
        raise StateError("invalid report lists")
    for item in findings:
        if (not isinstance(item, dict) or not isinstance(item.get("severity"), str) or
                item["severity"] not in {"blocking", "nonblocking"}):
            raise StateError("invalid finding")
        require_text(item.get("id"), "finding ID", 128)
        require_text(item.get("summary"), "finding summary")
        if expected in {"ACCEPT", "PASS"} and item["severity"] == "blocking":
            raise StateError("accepted report contains blocking findings")
    for item in checks:
        if not isinstance(item, dict) or type(item.get("exit_code")) is not int:
            raise StateError("invalid check")
        require_text(item.get("command"), "check command")
        require_text(item.get("result"), "check result")
        if expected == "PASS" and item["exit_code"] != 0:
            raise StateError("passing report contains failed checks")
    if not all(isinstance(item, str) for item in not_run):
        raise StateError("invalid not-run list")
    add_artifacts(run, state, [path])


def initialize(root: Path, args: argparse.Namespace) -> RunState:
    run_id = require_run_id(args.run)
    approval = require_text(args.approval, "approval")
    plan, _ = checked_path(root, args.plan)
    if not plan.is_file():
        raise StateError("approved plan is not a regular file")
    plan_bytes = plan.read_bytes()
    runs = runs_path(root, create=True)
    run = runs / run_id
    try:
        run.mkdir(mode=0o700)
    except FileExistsError as error:
        raise StateError("run already exists") from error
    with (run / ".lock").open("xb") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    with (run / "plan.md").open("xb") as stream:
        stream.write(plan_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    state: RunState = {
        "schema_version": 1, "run_id": run_id, "revision": 0,
        "status": "approved", "iteration": 0,
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(), "approval": approval,
        "summary": "Approved plan saved", "artifacts": {}, "source_hashes": {},
        "blocked_from": None, "resume_approval": None, "integrity_errors": [],
    }
    atomic_json(run / "state.json", state)
    return state


def checkpoint(root: Path, args: argparse.Namespace) -> RunState:
    run = run_path(root, args.run)
    require_text(args.summary, "summary")
    with locked(run, exclusive=True):
        state = load_state(run, args.run)
        if state["revision"] != args.expect_revision:
            raise StateError("stale revision")
        current, next_status = state["status"], args.status
        if next_status not in TRANSITIONS[current]:
            raise StateError(f"invalid transition: {current} -> {next_status}")
        if current == "blocked":
            if args.bind or args.report or not args.artifact or not set(args.artifact) <= ARCHIVE_FILES:
                raise StateError("blocked checkpoint permits only new archival artifacts")
            add_artifacts(run, state, args.artifact, new_only=True)
        elif next_status == "blocked":
            if args.bind or args.report:
                raise StateError("cannot bind sources or reports while blocking")
            state["integrity_errors"] = integrity_errors(root, run, state)
            state["blocked_from"] = current
            add_artifacts(run, state, args.artifact)
        else:
            assert_integrity(root, run, state)
            if next_status == "reviewing":
                if not args.bind:
                    raise StateError("reviewing requires source bindings")
                state["source_hashes"] = fingerprints(root, args.bind)
            elif args.bind:
                raise StateError("source bindings are only accepted when entering review")
            required_report = {
                ("reviewing", "implementing"): "REJECT",
                ("reviewing", "validating"): "ACCEPT",
                ("validating", "implementing"): "FAIL",
                ("validating", "retrospective"): "PASS",
            }.get((current, next_status))
            if required_report:
                if not args.report:
                    raise StateError("transition requires a report")
                check_report(run, state, args.report, required_report)
            elif args.report:
                raise StateError("report is not accepted for this transition")
            if next_status == "implementing":
                if state["iteration"] >= 3:
                    raise StateError("implementation round limit reached")
                state["iteration"] += 1
                state["source_hashes"] = {}
            add_artifacts(run, state, args.artifact)
            if next_status == "completed" and not ARCHIVE_FILES <= state["artifacts"].keys():
                raise StateError("completion requires all retrospective artifacts")
        state["revision"] += 1
        state["status"] = next_status
        state["summary"] = args.summary
        atomic_json(run / "state.json", state)
        return state


def resume(root: Path, args: argparse.Namespace) -> RunState:
    approval = require_text(args.approval, "resume approval")
    run = run_path(root, args.run)
    with locked(run, exclusive=True):
        state = load_state(run, args.run)
        if state["revision"] != args.expect_revision:
            raise StateError("stale revision")
        if state["status"] != "blocked" or state["blocked_from"] is None:
            raise StateError("only a blocked run may be resumed")
        assert_integrity(root, run, state)
        state["status"] = state["blocked_from"]
        state["blocked_from"] = None
        state["resume_approval"] = approval
        state["integrity_errors"] = []
        state["revision"] += 1
        state["summary"] = "Resumed with approval"
        atomic_json(run / "state.json", state)
        return state


def compact(state: RunState) -> dict[str, object]:
    base = f'.harness/runs/{state["run_id"]}'
    return {
        "schema_version": state["schema_version"],
        "run_id": state["run_id"],
        "revision": state["revision"],
        "status": state["status"],
        "iteration": state["iteration"],
        "summary": state["summary"][:240],
        "state_path": f"{base}/state.json",
        "plan_path": f"{base}/plan.md",
        "artifact_count": len(state["artifacts"]),
        "source_count": len(state["source_hashes"]),
        "blocked_from": state["blocked_from"],
        "integrity_error_count": len(state["integrity_errors"]),
    }


def show(root: Path, run_id: str | None) -> dict[str, object]:
    if run_id is not None:
        run = run_path(root, run_id)
        with locked(run, exclusive=False):
            return compact(load_state(run, run_id))
    runs = runs_path(root)
    if not runs.exists():
        return {"runs": [], "total_runs": 0, "active_count": 0, "active_run_id": None,
                "unreadable_count": 0, "unreadable_runs": []}
    entries: list[tuple[int, RunState]] = []
    unreadable: list[dict[str, str]] = []
    for path in sorted(runs.iterdir(), key=lambda entry: entry.name):
        if not path.is_symlink() and not path.is_dir():
            continue
        try:
            if path.is_symlink():
                raise StateError("run directory cannot be a symlink")
            run_id = require_run_id(path.name)
            with locked(path, exclusive=False):
                state = load_state(path, run_id)
                entries.append(((path / "state.json").stat().st_mtime_ns, state))
        except (OSError, StateError, ValueError) as error:
            unreadable.append({"run_id": path.name, "error": str(error)[:240]})
    entries.sort(key=lambda entry: (entry[0], entry[1]["run_id"]), reverse=True)
    active_runs = [state["run_id"] for _, state in entries if state["status"] != "completed"]
    return {"total_runs": len(entries) + len(unreadable),
            "active_count": len(active_runs) + len(unreadable),
            "active_run_id": active_runs[0] if len(active_runs) == 1 and not unreadable else None,
            "unreadable_count": len(unreadable),
            "unreadable_runs": unreadable[:10],
            "runs": [compact(state) for _, state in entries[:10]]}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", help="working root; defaults to Git root or current directory")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    init = commands.add_parser("init")
    init.add_argument("run")
    init.add_argument("--plan", required=True)
    init.add_argument("--approval", required=True)
    listing = commands.add_parser("show")
    listing.add_argument("run", nargs="?")
    advance = commands.add_parser("checkpoint")
    advance.add_argument("run")
    advance.add_argument("--expect-revision", type=int, required=True)
    advance.add_argument("--status", choices=sorted(STATUSES), required=True)
    advance.add_argument("--summary", required=True)
    advance.add_argument("--artifact", action="append", default=[])
    advance.add_argument("--bind", action="append", default=[])
    advance.add_argument("--report")
    resume_parser = commands.add_parser("resume")
    resume_parser.add_argument("run")
    resume_parser.add_argument("--expect-revision", type=int, required=True)
    resume_parser.add_argument("--approval", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("run")
    digest = commands.add_parser("fingerprint")
    digest.add_argument("paths", nargs="+")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        root = working_root(args.root)
        if args.command == "prepare":
            output: object = prepare(root)
        elif args.command == "init":
            output = compact(initialize(root, args))
        elif args.command == "show":
            output = show(root, args.run)
        elif args.command == "checkpoint":
            output = compact(checkpoint(root, args))
        elif args.command == "resume":
            output = compact(resume(root, args))
        elif args.command == "verify":
            run = run_path(root, args.run)
            with locked(run, exclusive=False):
                state = load_state(run, args.run)
                assert_integrity(root, run, state)
                output = compact(state) | {"verified": True}
        else:
            output = fingerprints(root, args.paths)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    except (StateError, OSError, ValueError) as error:
        print(f"state: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
