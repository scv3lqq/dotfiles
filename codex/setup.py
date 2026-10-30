#!/usr/bin/env python3
"""Link the Codex dotfiles and select the CLI theme without replacing user config."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tempfile
import tomllib
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES = ("implementer", "plan-reviewer", "acceptance-validator", "skill-dry-run")
THEME = "ayu-claude"


class SetupError(ValueError):
    """A setup input cannot be changed safely."""


@dataclass(frozen=True)
class Link:
    source: Path
    destination: Path


def theme_config(original: bytes) -> bytes:
    """Change one simple TOML value, then prove the remaining data is unchanged."""
    try:
        text = original.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("config.toml is not valid UTF-8 TOML") from error

    headers = list(re.finditer(r"^[ \t]*\[tui\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)", text, re.M))
    tui = parsed.get("tui")
    if (tui is not None and (not isinstance(tui, dict) or len(headers) != 1)) or len(headers) > 1:
        raise SetupError("config.toml: use a literal [tui] table; inline or dotted tui is unsupported")
    if headers and tui is None:
        raise SetupError("config.toml: ambiguous [tui] text; no changes made")
    newline = "\r\n" if "\r\n" in text else "\n"
    assignment = f'theme = "{THEME}"{newline}'

    if not headers:
        prefix = text + (newline if text and not text.endswith("\n") else "")
        candidate = prefix + (newline if text else "") + f"[tui]{newline}" + assignment
    else:
        header = headers[0]
        section_end = re.search(r"^[ \t]*\[", text[header.end():], re.M)
        end = header.end() + section_end.start() if section_end else len(text)
        section = text[header.end():end]
        if "theme" not in tui:
            separator = "" if header.group().endswith("\n") else newline
            candidate = text[:header.end()] + separator + assignment + text[header.end():]
        else:
            if not isinstance(tui["theme"], str):
                raise SetupError("config.toml: tui.theme must be a string")
            lines = list(re.finditer(r"^[ \t]*(?:theme|'theme'|\"theme\")[ \t]*=[^\r\n]*", section, re.M))
            if len(lines) != 1:
                raise SetupError("config.toml: tui.theme needs one simple string assignment")
            line = lines[0]
            value = re.fullmatch(
                r"(?P<prefix>[ \t]*(?:theme|'theme'|\"theme\")[ \t]*=[ \t]*)"
                r"(?:\"(?:[^\"\\]|\\.)*\"|'[^']*')(?P<suffix>[ \t]*(?:#.*)?)",
                line.group(),
            )
            if value is None:
                raise SetupError("config.toml: multiline tui.theme is unsupported")
            if tui["theme"] == THEME:
                return original
            start = header.end() + line.start()
            finish = header.end() + line.end()
            replacement = value["prefix"] + f'"{THEME}"' + value["suffix"]
            candidate = text[:start] + replacement + text[finish:]

    expected = copy.deepcopy(parsed)
    expected.setdefault("tui", {})["theme"] = THEME
    try:
        actual = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as error:
        raise SetupError("config.toml: unsupported table layout; no changes made") from error
    if actual != expected:
        raise SetupError("config.toml: theme edit would change other settings; no changes made")
    return candidate.encode("utf-8")


def desired_links(home: Path, repo: Path, system: str) -> list[Link]:
    links = [Link(repo / f"codex/agents/{role}.toml", home / f".codex/agents/{role}.toml")
             for role in ROLES]
    links.append(Link(repo / f"codex/themes/{THEME}.tmTheme", home / f".codex/themes/{THEME}.tmTheme"))
    skills = repo / "claude/skills"
    if not skills.is_dir():
        raise SetupError("The repository has no claude/skills directory")
    for source in sorted(skills.iterdir()):
        if not source.is_dir() or (system != "Darwin" and source.name.startswith("mac-")):
            continue
        adapter = repo / "codex/skills" / source.name
        if adapter.is_dir():
            source = adapter
        if not (source / "SKILL.md").is_file():
            raise SetupError(f"Missing SKILL.md for {source.name}")
        links.append(Link(source, home / ".agents/skills" / source.name))
    for link in links:
        if not link.source.exists():
            raise SetupError(f"Missing source: {link.source.relative_to(repo)}")
    return links


def is_correct_link(link: Link) -> bool:
    return link.destination.is_symlink() and link.destination.resolve() == link.source.resolve()


def backup_files(home: Path, paths: list[Path]) -> None:
    if not paths:
        return
    parent = home / ".claude/backups"
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = parent / f"codex-{timestamp}"
    backup.mkdir(mode=0o700)
    for path in paths:
        target = backup / path.name
        if path.is_symlink() and not path.exists():
            target.symlink_to(path.resolve())
        else:
            target.write_bytes(path.read_bytes())
            target.chmod(0o600)
    print(f"Backup: {backup}")


def atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".codex-config-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(home: Path, *, apply: bool = False, repo_root: Path | None = None,
              system: str | None = None) -> None:
    home = home.expanduser().resolve()
    repo = (repo_root or REPO_ROOT).resolve()
    config = home / ".codex/config.toml"
    config_target = config.resolve()
    if config_target.exists() and not config_target.is_file():
        raise SetupError("config.toml must be a regular file or a file symlink")
    original = config_target.read_bytes() if config_target.exists() else b""
    updated = theme_config(original)
    mode = stat.S_IMODE(config_target.stat().st_mode) if config_target.exists() else 0o600
    links = desired_links(home, repo, system or platform.system())
    guidance = Link(repo / "codex/AGENTS.md", home / ".codex/AGENTS.md")
    if not guidance.source.is_file():
        raise SetupError("Missing source: codex/AGENTS.md")
    if guidance.destination.exists() and not guidance.destination.is_file():
        raise SetupError("AGENTS.md must be a regular file or a file symlink")
    ready = []
    for link in links:
        if is_correct_link(link):
            continue
        if link.destination.exists() or link.destination.is_symlink():
            print(f"Skipping existing destination: {link.destination}")
        else:
            ready.append(link)
    replace_guidance = not is_correct_link(guidance)
    change_config = original != updated
    label = "Apply" if apply else "Preview"
    print(f"{label}: {len(ready)} links, guidance {'update' if replace_guidance else 'unchanged'}, "
          f"CLI theme {'update' if change_config else 'unchanged'}")
    if not apply:
        return

    backups = []
    if change_config and config_target.exists():
        backups.append(config)
    if replace_guidance and (guidance.destination.exists() or guidance.destination.is_symlink()):
        backups.append(guidance.destination)
    backup_files(home, backups)
    if change_config:
        atomic_write(config_target, updated, mode)
    if replace_guidance:
        guidance.destination.parent.mkdir(parents=True, exist_ok=True)
        if guidance.destination.exists() or guidance.destination.is_symlink():
            guidance.destination.unlink()
        guidance.destination.symlink_to(guidance.source)
    for link in ready:
        link.destination.parent.mkdir(parents=True, exist_ok=True)
        link.destination.symlink_to(link.source, target_is_directory=link.source.is_dir())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Destination home directory")
    parser.add_argument("--apply", action="store_true", help="Apply the previewed setup")
    args = parser.parse_args(argv)
    try:
        configure(args.home, apply=args.apply)
    except (SetupError, OSError) as error:
        print(f"Codex setup failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
