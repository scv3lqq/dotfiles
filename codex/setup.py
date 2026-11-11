#!/usr/bin/env python3
"""Link the Codex dotfiles and select the CLI theme without replacing user config."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES = ("implementer", "plan-reviewer", "acceptance-validator", "skill-dry-run")
THEME = "ayu-claude"
SUBAGENT_DEFAULTS = (("default_subagent_model", "gpt-6.1-terra"),
                     ("default_subagent_reasoning_effort", "medium"))
HARNESS_ROLES = ("harness-orchestrator", "harness-explorer", "harness-implementer",
                 "harness-reviewer", "harness-validator", "harness-archivist")
HARNESS_BEGIN = "[harness managed begin]"
HARNESS_END = "[harness managed end]"


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


def analytics_config(original: bytes) -> bytes:
    """Disable optional analytics without altering unrelated configuration."""
    try:
        text = original.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("config.toml is not valid UTF-8 TOML") from error
    headers = list(re.finditer(r"^[ \t]*\[analytics\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)", text, re.M))
    analytics = parsed.get("analytics")
    if (analytics is not None and (not isinstance(analytics, dict) or len(headers) != 1)) or len(headers) > 1:
        raise SetupError("config.toml: analytics requires a literal table")
    newline = "\r\n" if "\r\n" in text else "\n"
    if not headers:
        prefix = text + (newline if text and not text.endswith("\n") else "")
        candidate = prefix + (newline if text else "") + "[analytics]" + newline + "enabled = false" + newline
    else:
        header = headers[0]
        section_end = re.search(r"^[ \t]*\[", text[header.end():], re.M)
        end = header.end() + section_end.start() if section_end else len(text)
        section = text[header.end():end]
        if "enabled" not in analytics:
            separator = "" if header.group().endswith("\n") else newline
            section = separator + "enabled = false" + newline + section
        else:
            if not isinstance(analytics["enabled"], bool):
                raise SetupError("config.toml: analytics.enabled must be a boolean")
            lines = list(re.finditer(r"^[ \t]*(?:enabled|'enabled'|\"enabled\")[ \t]*=[^\r\n]*", section, re.M))
            if len(lines) != 1:
                raise SetupError("config.toml: analytics.enabled needs one simple assignment")
            match = re.fullmatch(r"(?P<prefix>[ \t]*(?:enabled|'enabled'|\"enabled\")[ \t]*=[ \t]*)(?:true|false)(?P<suffix>[ \t]*(?:#.*)?)", lines[0].group())
            if match is None:
                raise SetupError("config.toml: analytics.enabled needs a simple boolean")
            section = section[:lines[0].start()] + match["prefix"] + "false" + match["suffix"] + section[lines[0].end():]
        candidate = text[:header.end()] + section + text[end:]
    expected = copy.deepcopy(parsed)
    expected.setdefault("analytics", {})["enabled"] = False
    try:
        actual = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as error:
        raise SetupError("config.toml: unsupported analytics layout") from error
    if actual != expected:
        raise SetupError("config.toml: analytics edit would change other settings")
    return candidate.encode("utf-8")


def subagent_config(original: bytes) -> bytes:
    """Set child defaults while preserving all other TOML values and text."""
    try:
        text = original.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("config.toml is not valid UTF-8 TOML") from error

    headers = list(re.finditer(r"^[ \t]*\[agents\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)", text, re.M))
    agents = parsed.get("agents")
    if (agents is not None and (not isinstance(agents, dict) or len(headers) != 1)) or len(headers) > 1:
        raise SetupError("config.toml: use a literal [agents] table; inline or dotted agents is unsupported")
    if headers and agents is None:
        raise SetupError("config.toml: ambiguous [agents] text; no changes made")
    newline = "\r\n" if "\r\n" in text else "\n"
    if not headers:
        prefix = text + (newline if text and not text.endswith("\n") else "")
        text = prefix + (newline if text else "") + "[agents]" + newline
        headers = list(re.finditer(r"^[ \t]*\[agents\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)", text, re.M))
        agents = {}

    header = headers[0]
    section_end = re.search(r"^[ \t]*\[", text[header.end():], re.M)
    end = header.end() + section_end.start() if section_end else len(text)
    section = text[header.end():end]
    insertions = []
    for key, desired in SUBAGENT_DEFAULTS:
        if key not in agents:
            insertions.append(f'{key} = "{desired}"{newline}')
            continue
        if not isinstance(agents[key], str):
            raise SetupError(f"config.toml: agents.{key} must be a string")
        pattern = rf"^[ \t]*(?:{key}|'{key}'|\"{key}\")[ \t]*=[^\r\n]*"
        lines = list(re.finditer(pattern, section, re.M))
        if len(lines) != 1:
            raise SetupError(f"config.toml: agents.{key} needs one simple string assignment")
        line = lines[0]
        value = re.fullmatch(
            rf"(?P<prefix>[ \t]*(?:{key}|'{key}'|\"{key}\")[ \t]*=[ \t]*)"
            r"(?:\"(?:[^\"\\]|\\.)*\"|'[^']*')(?P<suffix>[ \t]*(?:#.*)?)",
            line.group(),
        )
        if value is None:
            raise SetupError(f"config.toml: multiline agents.{key} is unsupported")
        if agents[key] != desired:
            replacement = value["prefix"] + f'"{desired}"' + value["suffix"]
            section = section[:line.start()] + replacement + section[line.end():]
    if insertions:
        separator = "" if header.group().endswith("\n") else newline
        section = separator + "".join(insertions) + section
    candidate = text[:header.end()] + section + text[end:]
    expected = copy.deepcopy(parsed)
    expected.setdefault("agents", {}).update(dict(SUBAGENT_DEFAULTS))
    try:
        actual = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as error:
        raise SetupError("config.toml: unsupported table layout; no changes made") from error
    if actual != expected:
        raise SetupError("config.toml: subagent edit would change other settings; no changes made")
    return candidate.encode("utf-8")



def agent_registry_config(original: bytes, registrations: tuple[tuple[str, str, str], ...]) -> bytes:
    """Append missing managed registrations without changing existing metadata."""
    try:
        text = original.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("config.toml is not valid UTF-8 TOML") from error
    expected = copy.deepcopy(parsed)
    agents = expected.get("agents", {})
    if not isinstance(agents, dict):
        raise SetupError("config.toml: agents must be a table")
    newline = "\r\n" if "\r\n" in text else "\n"
    additions = []
    for name, path, description in registrations:
        if name in agents:
            entry = agents[name]
            if not isinstance(entry, dict) or entry.get("config_file") != path:
                raise SetupError(f"config.toml: conflicting registry for {name}")
            continue
        agents[name] = {"description": description, "config_file": path}
        additions.append(f'[agents.{name}]{newline}description = {json.dumps(description, ensure_ascii=False)}{newline}'
                         f'config_file = {json.dumps(path, ensure_ascii=False)}{newline}')
    if not additions:
        return original
    expected["agents"] = agents
    separator = newline if text and not text.endswith("\n") else ""
    candidate = text + separator + "".join(newline + entry for entry in additions)
    try:
        actual = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as error:
        raise SetupError("config.toml: unsupported registry layout; no changes made") from error
    if actual != expected:
        raise SetupError("config.toml: registry edit would change other settings; no changes made")
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


def migrate_role_links(home: Path, links: list[Link]) -> None:
    """Back up and remove only exact managed links, restoring them on failure."""
    managed = [link for link in links if is_correct_link(link)]
    if not managed:
        return
    snapshots = []
    for link in managed:
        info = link.destination.lstat()
        target = link.destination.readlink()
        if (link.destination.parent / target).resolve() != link.source.resolve():
            raise SetupError(f'role link changed during setup: {link.destination}')
        snapshots.append((link, info, target))
    parent = home / '.claude/backups'
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = parent / f"codex-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}"
    backup.mkdir(mode=0o700)
    for link, _, target in snapshots:
        (backup / link.destination.name).symlink_to(target)
    removed: list[tuple[Link, Path]] = []
    try:
        for link, info, target in snapshots:
            current = link.destination.lstat()
            if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino) or link.destination.readlink() != target:
                raise SetupError(f'role link changed during setup: {link.destination}')
            link.destination.unlink()
            removed.append((link, target))
    except (OSError, SetupError):
        for link, target in reversed(removed):
            if not link.destination.exists() and not link.destination.is_symlink():
                link.destination.symlink_to(target)
        raise


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


def managed_harness_instructions(existing: str, router: str, skill: Path) -> str:
    """Replace just the managed block; preserve any independent instructions."""
    block = (f"{HARNESS_BEGIN}\n"
             f"Canonical user-scope harness SKILL.md: {skill}\n"
             f"{router}\n{HARNESS_END}")
    begins, ends = existing.count(HARNESS_BEGIN), existing.count(HARNESS_END)
    if begins == ends == 0:
        return existing + ("\n\n" if existing else "") + block
    if begins != 1 or ends != 1:
        raise SetupError("config.toml: ambiguous harness instruction markers")
    start = existing.index(HARNESS_BEGIN)
    end = existing.index(HARNESS_END)
    if end < start:
        raise SetupError("config.toml: reversed harness instruction markers")
    owner = f"{HARNESS_BEGIN}\nCanonical user-scope harness SKILL.md: {skill}\n"
    if not existing[start:].startswith(owner):
        raise SetupError("config.toml: unrecognized harness instruction block")
    return existing[:start] + block + existing[end + len(HARNESS_END):]


def set_simple_values(section: str, old: dict[str, object], values: dict[str, object],
                      newline: str, label: str) -> str:
    """Replace supported literal assignments without altering unrelated text."""
    insertions: list[str] = []
    for key, desired in values.items():
        literal = json.dumps(desired, ensure_ascii=False)
        if key not in old:
            insertions.append(f"{key} = {literal}{newline}")
            continue
        if type(old[key]) is not type(desired):
            raise SetupError(f"config.toml: {label}{key} has an unsupported type")
        pattern = rf"^[ \t]*(?:{key}|'{key}'|\"{key}\")[ \t]*=[^\r\n]*"
        matches = list(re.finditer(pattern, section, re.M))
        if len(matches) != 1:
            raise SetupError(f"config.toml: {label}{key} needs one simple assignment")
        line = matches[0]
        value = re.fullmatch(
            rf"(?P<prefix>[ \t]*(?:{key}|'{key}'|\"{key}\")[ \t]*=[ \t]*)"
            r"(?:\"(?:[^\"\\]|\\.)*\"|'[^']*'|true|false|[+-]?\d+)"
            r"(?P<suffix>[ \t]*(?:#.*)?)", line.group(),
        )
        if value is None:
            raise SetupError(f"config.toml: {label}{key} needs a simple literal")
        if old[key] != desired:
            replacement = value['prefix'] + literal + value['suffix']
            section = section[:line.start()] + replacement + section[line.end():]
    return section + ("" if not insertions or not section or section.endswith("\n") else newline) + "".join(insertions)


def global_harness_config(original: bytes, router: str, skill: Path,
                          registrations: tuple[tuple[str, str, str], ...]) -> bytes:
    """Apply the approved global defaults and prove no other TOML value changed."""
    try:
        text = original.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("config.toml is not valid UTF-8 TOML") from error
    existing = parsed.get('developer_instructions', '')
    if not isinstance(existing, str):
        raise SetupError("config.toml: developer_instructions must be a string")
    agents = parsed.get('agents', {})
    if not isinstance(agents, dict) or 'max_threads' in agents:
        raise SetupError("config.toml: unsupported agents layout or legacy max_threads")
    newline = "\r\n" if "\r\n" in text else "\n"
    root_values: dict[str, object] = {
        'model': 'gpt-6.1-sol', 'model_reasoning_effort': 'medium',
        'developer_instructions': managed_harness_instructions(existing, router, skill),
    }
    agent_values: dict[str, object] = {
        'enabled': True, 'max_depth': 2, 'max_concurrent_threads_per_session': 3,
        'default_subagent_model': 'gpt-6.1-terra', 'default_subagent_reasoning_effort': 'medium',
    }
    first_header = re.search(r'^[ \t]*\[', text, re.M)
    root_end = first_header.start() if first_header else len(text)
    root = set_simple_values(text[:root_end], parsed, root_values, newline, '')
    text = root + text[root_end:]
    headers = list(re.finditer(r'^[ \t]*\[agents\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)', text, re.M))
    if len(headers) > 1 or (agents and not headers):
        raise SetupError("config.toml: agents must use one literal [agents] table")
    if headers:
        header = headers[0]
        next_header = re.search(r'^[ \t]*\[', text[header.end():], re.M)
        end = header.end() + next_header.start() if next_header else len(text)
        section = text[header.end():end]
        separator = '' if header.group().endswith('\n') else newline
        text = text[:header.end()] + separator + set_simple_values(section, agents, agent_values, newline, 'agents.') + text[end:]
    else:
        separator = '' if not text or text.endswith('\n') else newline
        text += separator + (newline if text else '') + '[agents]' + newline
        text += set_simple_values('', {}, agent_values, newline, 'agents.')
    expected = copy.deepcopy(parsed)
    expected.update(root_values)
    expected.setdefault('agents', {}).update(agent_values)
    try:
        if tomllib.loads(text) != expected:
            raise SetupError("config.toml: unsupported layout would alter other settings")
    except tomllib.TOMLDecodeError as error:
        raise SetupError("config.toml: unsupported layout; no changes made") from error
    return agent_registry_config(text.encode('utf-8'), registrations)


def harness_links_and_registry(home: Path, repo: Path) -> tuple[list[Link], tuple[tuple[str, str, str], ...], str]:
    skill = repo / 'codex/skills/harness'
    script = skill / 'scripts/state.py'
    protocol = skill / 'references/protocol.md'
    if not (skill / 'SKILL.md').is_file() or not script.is_symlink() or script.readlink() != Path('../../../harness/state.py') or not script.is_file():
        raise SetupError("harness skill or canonical state helper link is missing")
    if not skill.resolve().is_relative_to(repo) or not (skill / 'SKILL.md').resolve().is_relative_to(repo):
        raise SetupError("harness skill must resolve inside the repository")
    if not protocol.is_file() or not protocol.resolve().is_relative_to(repo):
        raise SetupError("harness protocol must be a file inside the repository")
    if not script.resolve().is_relative_to(repo):
        raise SetupError("harness state helper must resolve inside the repository")
    try:
        project = tomllib.loads((repo / '.codex/config.toml').read_text(encoding='utf-8'))
        router = project['developer_instructions']
    except (OSError, KeyError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("project's portable harness router is unavailable") from error
    if not isinstance(router, str) or 'user-scope harness' not in router or 'codex/skills/harness' in router:
        raise SetupError("project's harness router is not portable")
    links = [Link(skill, home / '.agents/skills/harness')]
    registrations: list[tuple[str, str, str]] = []
    for name in HARNESS_ROLES:
        source = repo / f'codex/agents/{name}.toml'
        if not source.is_file() or not source.resolve().is_relative_to(repo):
            raise SetupError(f"missing canonical harness role: {name}")
        try:
            data = tomllib.loads(source.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise SetupError(f"invalid harness role: {name}") from error
        description = data.get('description')
        if data.get('name') != name or not isinstance(description, str) or not description.strip():
            raise SetupError(f"missing name or description for harness role: {name}")
        links.append(Link(source, home / f'.codex/agents/{name}.toml'))
        registrations.append((name, str(source.resolve()), description))
    for link in links:
        if not link.destination.parent.resolve().is_relative_to(home):
            raise SetupError(f"harness destination escapes home: {link.destination}")
        if (link.destination.exists() or link.destination.is_symlink()) and not is_correct_link(link):
            raise SetupError(f"conflicting harness destination: {link.destination}")
    return links, tuple(registrations), router


def backup_harness_config(home: Path, original: bytes) -> None:
    """Use a private backup directory without changing an existing parent's mode."""
    parent = home / '.claude/backups'
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = parent / f'codex-{timestamp}'
    backup.mkdir(mode=0o700)
    descriptor = os.open(backup / 'config.toml', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(original)
    print(f'Backup: {backup}')


def atomic_harness_write(config: Path, target: Path, original: bytes, existed: bool,
                         mode: int, updated: bytes,
                         replace: Callable[[str, Path], None]) -> None:
    """Check observed drift immediately before replacing the prepared file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.codex-harness-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if config.resolve() != target or target.exists() != existed:
            raise SetupError('config.toml changed during harness setup')
        if existed and (not target.is_file() or target.read_bytes() != original or stat.S_IMODE(target.stat().st_mode) != mode):
            raise SetupError('config.toml changed during harness setup')
        replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure_harness(home: Path, *, apply: bool = False, repo_root: Path | None = None) -> None:
    """Provision only the global harness after complete, non-mutating preflight."""
    home = home.expanduser().resolve()
    repo = (repo_root or REPO_ROOT).resolve()
    config = home / '.codex/config.toml'
    target = config.resolve()
    existed = target.exists()
    if existed and not target.is_file():
        raise SetupError('config.toml must be a regular file or a file symlink')
    original = target.read_bytes() if existed else b''
    mode = stat.S_IMODE(target.stat().st_mode) if existed else 0o600
    links, registrations, router = harness_links_and_registry(home, repo)
    updated = global_harness_config(original, router, home / '.agents/skills/harness/SKILL.md', registrations)
    role_links = links[1:]
    links = links[:1]
    ready = [link for link in links if not is_correct_link(link)]
    removals = sum(is_correct_link(link) for link in role_links)
    print(f"{'Apply' if apply else 'Preview'} harness: {len(ready)} links, "
          f"{removals} managed role links to remove, config {'update' if updated != original else 'unchanged'}")
    if not apply or (not ready and updated == original and not any(is_correct_link(link) for link in role_links)):
        return
    if updated != original and existed:
        backup_harness_config(home, original)
    created: list[tuple[Link, int, int]] = []
    prior_instructions = tomllib.loads(original.decode('utf-8')).get('developer_instructions', '')
    active_before = isinstance(prior_instructions, str) and HARNESS_BEGIN in prior_instructions
    replacement_attempted = False

    def replace(source: str, destination: Path) -> None:
        nonlocal replacement_attempted
        replacement_attempted = True
        os.replace(source, destination)

    try:
        for link in ready:
            link.destination.parent.mkdir(parents=True, exist_ok=True)
            link.destination.symlink_to(link.source, target_is_directory=link.source.is_dir())
            info = link.destination.lstat()
            created.append((link, info.st_dev, info.st_ino))
        if not all(is_correct_link(link) for link in links):
            raise SetupError('harness links changed during setup')
        if updated != original:
            atomic_harness_write(config, target, original, existed, mode, updated, replace)
        migrate_role_links(home, role_links)
    except (OSError, SetupError):
        active = active_before
        uncertainty_reported = False
        if replacement_attempted:
            try:
                active = config.read_bytes() == updated or active_before
            except FileNotFoundError:
                active = active_before
            except OSError:
                active = True
                print('Harness activation could not be inspected; created links retained for safety.', file=sys.stderr)
                uncertainty_reported = True
        if active and created and not uncertainty_reported:
            print('Harness may already be active; created links retained for safety.', file=sys.stderr)
        if not active:
            for link, device, inode in reversed(created):
                try:
                    info = link.destination.lstat()
                    if (info.st_dev, info.st_ino) == (device, inode) and is_correct_link(link):
                        link.destination.unlink()
                except OSError:
                    print(f'Could not remove an owned harness link: {link.destination}', file=sys.stderr)
        raise


def normalize_generated_catalogs(home: Path, repo: Path, *, apply: bool) -> bool:
    """Run the compatibility adapter when at least one generated catalog exists."""
    catalogs = (
        home / ".codex/.tmp/marketplaces/claude-plugins-official/.claude-plugin/marketplace.json",
        home / ".codex/.tmp/plugins/plugins/ngs-analysis/.codex-plugin/plugin.json",
    )
    if not any(path.exists() for path in catalogs):
        print("Catalog normalization skipped: generated catalogs are absent")
        return False
    command = [sys.executable, "-B", str(repo / "codex/plugins.py"),
               "--home", str(home), "--normalize-catalogs"]
    if apply:
        command.append("--apply")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        raise SetupError("Catalog normalization failed") from error
    return True


def configure(home: Path, *, apply: bool = False, repo_root: Path | None = None,
              system: str | None = None) -> None:
    home = home.expanduser().resolve()
    repo = (repo_root or REPO_ROOT).resolve()
    config = home / ".codex/config.toml"
    config_target = config.resolve()
    if config_target.exists() and not config_target.is_file():
        raise SetupError("config.toml must be a regular file or a file symlink")
    original = config_target.read_bytes() if config_target.exists() else b""
    updated = analytics_config(subagent_config(theme_config(original)))
    mode = stat.S_IMODE(config_target.stat().st_mode) if config_target.exists() else 0o600
    links = desired_links(home, repo, system or platform.system())
    role_links = links[:len(ROLES)]
    registrations = []
    for link in links[:len(ROLES)]:
        if (link.destination.exists() or link.destination.is_symlink()) and not is_correct_link(link):
            continue
        role = link.source.stem
        try:
            role_data = tomllib.loads(link.source.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise SetupError(f"Missing description for {role}") from error
        description = role_data.get("description")
        if not isinstance(description, str) or not description.strip():
            raise SetupError(f"Missing description for {role}")
        registrations.append((role, str(link.source.resolve()), description))
    updated = agent_registry_config(updated, tuple(registrations))
    links = links[len(ROLES):]
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
    removals = sum(is_correct_link(link) for link in role_links)
    print(f"{label}: {len(ready)} links, {removals} managed role links to remove, "
          f"guidance {'update' if replace_guidance else 'unchanged'}, "
          f"config {'update' if change_config else 'unchanged'}")
    catalogs_ready = normalize_generated_catalogs(home, repo, apply=False)
    if not apply:
        return
    if catalogs_ready:
        normalize_generated_catalogs(home, repo, apply=True)

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
    migrate_role_links(home, role_links)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Destination home directory")
    parser.add_argument("--apply", action="store_true", help="Apply the previewed setup")
    parser.add_argument("--global-harness", action="store_true", help="Configure only the global harness")
    args = parser.parse_args(argv)
    try:
        if args.global_harness:
            configure_harness(args.home, apply=args.apply)
        else:
            configure(args.home, apply=args.apply)
    except (SetupError, OSError) as error:
        print(f"Codex setup failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
