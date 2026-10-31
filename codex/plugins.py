#!/usr/bin/env python3
"""Prepare complete local plugin packages without registering or running them."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn, TypeAlias, cast

JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)
MARKER = ".codex-parity.json"
SELECTION = (
    ("data@claude-plugins-official", "astronomer-data", 34),
    ("0bull@anthropic-plugin-directory", "0bull", 1),
    ("frontend-design@anthropic-plugin-directory", "frontend-design", 1),
    ("humanizer-blader@anthropic-plugin-directory", "humanizer", 1),
)


class PreparationError(ValueError):
    """A source or destination cannot be prepared safely."""


@dataclass(frozen=True)
class Package:
    registry_id: str
    name: str
    version: str
    source: Path
    source_sha256: str
    additions: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True)
class Ownership:
    source_sha256: str
    content_sha256: str


def _reject_non_finite_json(_value: str) -> NoReturn:
    raise PreparationError("Non-finite numbers are not valid JSON")


def _read_json(path: Path, label: str) -> JSONValue:
    try:
        return cast(JSONValue, json.loads(path.read_bytes().decode("utf-8"),
                                          parse_constant=_reject_non_finite_json))
    except (UnicodeDecodeError, json.JSONDecodeError, PreparationError) as error:
        raise PreparationError(f"{label} is not valid UTF-8 JSON") from error


def _object(value: JSONValue, label: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict):
        raise PreparationError(f"{label} must be a JSON object")
    return value


def _json_bytes(value: JSONValue) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _tree_entries(root: Path, *, exclude_marker: bool = False) -> Iterator[tuple[bytes, ...]]:
    def visit(directory: Path) -> Iterator[tuple[bytes, ...]]:
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            if exclude_marker and relative == MARKER:
                continue
            name = os.fsencode(relative)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                target = path.readlink()
                if target.is_absolute():
                    raise PreparationError(f"Absolute package link: {relative}")
                try:
                    resolved = path.resolve(strict=True)
                except (OSError, RuntimeError) as error:
                    raise PreparationError(f"Broken or cyclic package link: {relative}") from error
                if not resolved.is_relative_to(root):
                    raise PreparationError(f"Escaping package link: {relative}")
                if not (resolved.is_dir() or resolved.is_file()):
                    raise PreparationError(f"Non-regular package link target: {relative}")
                yield name, b"link", os.fsencode(str(target))
            elif stat.S_ISDIR(mode):
                yield name, b"directory", b""
                yield from visit(path)
            elif stat.S_ISREG(mode):
                yield name, b"file", path.read_bytes()
            else:
                raise PreparationError(f"Non-regular package entry: {relative}")

    yield from visit(root)


def _digest(records: Iterator[tuple[bytes, ...]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        for value in record:
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    return digest.hexdigest()


def _tree_digest(root: Path, *, exclude_marker: bool = False) -> str:
    return _digest(_tree_entries(root, exclude_marker=exclude_marker))


def _validate_mcp(source: Path, manifest: dict[str, JSONValue], name: str) -> None:
    paths = {source / ".mcp.json"} if (source / ".mcp.json").exists() else set()
    declared = manifest.get("mcpServers")
    if isinstance(declared, str):
        paths.add(source / declared)
    elif isinstance(declared, list):
        for item in declared:
            if not isinstance(item, str):
                raise PreparationError(f"{name}: MCP paths must be strings")
            paths.add(source / item)
    elif declared is not None and not isinstance(declared, dict):
        raise PreparationError(f"{name}: MCP definition must be an object or local path")
    for path in sorted(paths):
        if not path.resolve().is_relative_to(source):
            raise PreparationError(f"{name}: MCP path must stay inside its package")
        _object(_read_json(path, f"{name} MCP definition"), f"{name} MCP definition")


def _codex_data_hooks(hooks: dict[str, JSONValue]) -> dict[str, JSONValue]:
    adapted = copy.deepcopy(hooks)
    stop = adapted.get("Stop")
    if not isinstance(stop, list):
        return adapted
    cleanup = "uv run ${CLAUDE_PLUGIN_ROOT}/skills/analyzing-data/scripts/cli.py stop"
    for entry in stop:
        if not isinstance(entry, dict):
            continue
        handlers = entry.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if (isinstance(handler, dict) and handler.get("type") == "command"
                    and handler.get("command") == cleanup):
                handler["command"] = "{\n" + cleanup + "\n} >/dev/null"
    return adapted


def _adapter_additions(source: Path, name: str, version: str,
                       manifest: dict[str, JSONValue]) -> tuple[tuple[str, bytes], ...]:
    additions: dict[str, bytes] = {}
    if name == "astronomer-data":
        hooks = _object(manifest.get("hooks"), "astronomer-data hooks")
        additions[".codex-plugin/plugin.json"] = _json_bytes({
            "name": name, "version": version, "skills": "./skills/", "hooks": "./hooks/hooks.json",
        })
        additions["hooks/hooks.json"] = _json_bytes({"hooks": _codex_data_hooks(hooks)})
    elif name == "humanizer":
        additions[".codex-plugin/plugin.json"] = _json_bytes({
            "name": name, "version": version, "skills": "./skills/",
        })
        additions["skills/humanizer/SKILL.md"] = (source / "SKILL.md").read_bytes()
    missing = []
    for relative, content in additions.items():
        path = source / relative
        for parent in path.parents:
            if parent == source:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise PreparationError(f"{name}: adapter directory conflict at {relative}")
        if path.exists() or path.is_symlink():
            if not path.is_file() or path.read_bytes() != content:
                raise PreparationError(f"{name}: adapter conflicts with packaged file {relative}")
        else:
            missing.append((relative, content))
    return tuple(missing)


def _load_package(registry_id: str, name: str, count: int,
                  records: JSONValue) -> Package:
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise PreparationError(f"{registry_id}: install records must be a list of objects")
    users = [record for record in records if isinstance(record, dict) and record.get("scope") == "user"]
    if len(users) != 1:
        raise PreparationError(f"{registry_id}: expected exactly one user-scope install record")
    install_path = users[0].get("installPath")
    if not isinstance(install_path, str) or not install_path:
        raise PreparationError(f"{registry_id}: installPath must be a nonempty string")
    source = Path(install_path)
    if not source.is_dir():
        raise PreparationError(f"{registry_id}: source directory is missing")
    source = source.resolve()
    source_digest = _tree_digest(source)
    manifest = _object(_read_json(source / ".claude-plugin/plugin.json", f"{name} manifest"),
                       f"{name} manifest")
    if manifest.get("name") != name:
        raise PreparationError(f"{registry_id}: source manifest name must be {name}")
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        raise PreparationError(f"{name}: source manifest version must be a nonempty string")
    skills = [path for path in source.glob("skills/*/SKILL.md") if path.is_file()]
    if name == "humanizer":
        if skills or not (source / "SKILL.md").is_file():
            raise PreparationError("humanizer: expected one root SKILL.md and no nested skills")
    elif len(skills) != count:
        raise PreparationError(f"{name}: expected {count} skills, found {len(skills)}")
    _validate_mcp(source, manifest, name)
    additions = _adapter_additions(source, name, version, manifest)
    return Package(registry_id, name, version, source, source_digest, additions)


def _load_packages(home: Path) -> tuple[Package, ...]:
    registry = _object(_read_json(home / ".claude/plugins/installed_plugins.json",
                                  "installed_plugins.json"), "installed_plugins.json")
    if type(registry.get("version")) is not int or registry["version"] != 2:
        raise PreparationError("installed_plugins.json must use version 2")
    installs = _object(registry.get("plugins"), "installed plugin records")
    settings = _object(_read_json(home / ".claude/settings.json", "settings.json"), "settings.json")
    enabled = _object(settings.get("enabledPlugins"), "enabledPlugins")
    packages = []
    for registry_id, name, count in SELECTION:
        if enabled.get(registry_id) is not True:
            raise PreparationError(f"{registry_id}: plugin must be enabled")
        packages.append(_load_package(registry_id, name, count, installs.get(registry_id)))
    return tuple(packages)


def _source_digest(packages: tuple[Package, ...]) -> str:
    return _digest(iter((package.registry_id.encode(), package.version.encode(),
                         package.source_sha256.encode(),
                         _digest(iter((relative.encode(), content)
                                      for relative, content in sorted(package.additions))).encode())
                        for package in packages))


def _ownership(destination: Path) -> Ownership | None:
    if not destination.exists() and not destination.is_symlink():
        return None
    if destination.is_symlink() or not destination.is_dir():
        raise PreparationError("Destination conflict: expected a managed directory")
    marker = destination / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise PreparationError("Destination conflict: ownership marker is missing or invalid")
    try:
        record = _object(_read_json(marker, "ownership marker"), "ownership marker")
        source = record.get("source_sha256")
        content = record.get("content_sha256")
        if (type(record.get("schema")) is not int or record["schema"] != 1
                or not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{64}", source) is None
                or not isinstance(content, str) or re.fullmatch(r"[0-9a-f]{64}", content) is None):
            raise PreparationError("Destination conflict: invalid ownership marker")
        actual = _tree_digest(destination, exclude_marker=True)
    except (PreparationError, OSError) as error:
        raise PreparationError("Destination conflict: invalid marker or content drift") from error
    if actual != content:
        raise PreparationError("Destination content drift: refusing to overwrite local edits")
    return Ownership(source, content)


def _private_directory(directory: Path) -> None:
    if directory.is_symlink():
        raise PreparationError("Preparation and backup directories cannot be symlinks")
    if directory.exists():
        if not directory.is_dir():
            raise PreparationError("Preparation and backup paths must be directories")
        return
    _private_directory(directory.parent)
    directory.mkdir(mode=0o700)


def _build_snapshot(root: Path, packages: tuple[Package, ...], source_digest: str) -> None:
    root.mkdir(mode=0o700)
    _private_directory(root / "plugins")
    entries: list[JSONValue] = []
    for package in packages:
        copied = root / "plugins" / package.name
        shutil.copytree(package.source, copied, symlinks=True)
        if _tree_digest(copied) != package.source_sha256:
            raise PreparationError(f"{package.name}: source changed while preparing its snapshot")
        for relative, content in package.additions:
            path = copied / relative
            _private_directory(path.parent)
            path.write_bytes(content)
        entries.append({
            "name": package.name,
            "source": {"source": "local", "path": f"./plugins/{package.name}"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
            "category": "Productivity",
        })
    marketplace = root / ".agents/plugins/marketplace.json"
    _private_directory(marketplace.parent)
    marketplace.write_bytes(_json_bytes({"name": "claude-parity", "plugins": entries}))
    marker = root / MARKER
    marker.write_bytes(_json_bytes({
        "schema": 1, "source_sha256": source_digest, "content_sha256": _tree_digest(root),
    }))
    marker.chmod(0o600)


def _install_snapshot(staged: Path, destination: Path, home: Path,
                      original: Ownership | None) -> None:
    if _ownership(destination) != original:
        raise PreparationError("Destination changed while preparing its snapshot")
    if original is None:
        os.replace(staged, destination)
        return
    backup_parent = home / ".claude/backups"
    _private_directory(backup_parent)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = backup_parent / f"codex-plugins-{timestamp}"
    backup.mkdir(mode=0o700)
    if backup.stat().st_dev != destination.stat().st_dev:
        raise PreparationError("Snapshot and backup must be on the same filesystem")
    previous = backup / "claude-parity"
    os.replace(destination, previous)
    try:
        os.replace(staged, destination)
    except BaseException:
        os.replace(previous, destination)
        raise


def prepare_marketplace(home: Path, *, apply: bool = False) -> Path:
    """Validate all sources, then optionally replace one managed local snapshot."""
    home = home.expanduser().resolve()
    destination = home / ".codex/plugin-sources/claude-parity"
    packages = _load_packages(home)
    source_digest = _source_digest(packages)
    original = _ownership(destination)
    if not apply or (original is not None and original.source_sha256 == source_digest):
        return destination
    _private_directory(destination.parent)
    with tempfile.TemporaryDirectory(prefix=".codex-parity-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "claude-parity"
        _build_snapshot(staged, packages, source_digest)
        _install_snapshot(staged, destination, home, original)
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home containing source plugins")
    parser.add_argument("--apply", action="store_true", help="Prepare the validated snapshot")
    args = parser.parse_args(argv)
    try:
        destination = prepare_marketplace(args.home, apply=args.apply)
    except (PreparationError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{'Ready' if args.apply else 'Preview'}: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
