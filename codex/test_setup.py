"""Behavior checks for setup using synthetic sources and isolated homes."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import stat
import tempfile
import tomllib
import unittest
from unittest import mock

import setup as codex_setup


SKILLS = (
    "anki", "anki-addon", "anki-grammar", "cc-settings", "feature",
    "git-history-rewrite", "mac-audit", "mac-space", "obsidian-sr-flashcards",
    "obsidian-theme", "page-shot", "public-repo", "refactor-proof",
    "repo-knowledge-base", "retro", "session-handoff", "system-design-diagram",
    "tech-note-review", "telegram-theme", "tmux-cleanup", "vpn-xray", "zen-browser",
)
ROLES = ("implementer", "plan-reviewer", "acceptance-validator", "skill-dry-run")


class SetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "source"
        self.home = self.root / "home"
        self.config = self.home / ".codex/config.toml"
        self.write(self.repo / "codex/AGENTS.md", "Fixture guidance\n")
        self.write(self.repo / "codex/themes/ayu-claude.tmTheme", "Fixture theme\n")
        for role in ROLES:
            self.write(self.repo / f"codex/agents/{role}.toml", f'name = "{role}"\n')
        for skill in SKILLS:
            self.write(self.repo / f"claude/skills/{skill}/SKILL.md", f"Source {skill}\n")
        for skill in ("feature", "retro"):
            self.write(self.repo / f"codex/skills/{skill}/SKILL.md", f"Adapter {skill}\n")

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())

    def configure(self, *, apply: bool = True, system: str = "Darwin") -> str:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            codex_setup.configure(self.home, apply=apply, repo_root=self.repo, system=system)
        return output.getvalue()

    def snapshot(self) -> dict[str, tuple[int, int, bytes | str]]:
        if not self.home.exists():
            return {}
        result = {}
        for path in sorted(self.home.rglob("*")):
            info = path.lstat()
            if path.is_symlink():
                content = str(path.readlink())
            elif path.is_file():
                content = path.read_bytes()
            else:
                content = b""
            result[str(path.relative_to(self.home))] = (info.st_mode, info.st_mtime_ns, content)
        return result

    def backups(self) -> list[Path]:
        return sorted((self.home / ".claude/backups").glob("codex-*"))

    def test_preview_does_not_create_home(self) -> None:
        output = self.configure(apply=False)
        self.assertFalse(self.home.exists())
        self.assertIn("Preview", output)

    def test_preview_preserves_existing_state_and_does_not_print_config(self) -> None:
        self.write(self.config, 'model = "fixture-model"\nopaque = "fixture-private-value"\n')
        before = self.snapshot()
        output = self.configure(apply=False)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("fixture-private-value", output)

    def test_first_run_installs_exact_sources_and_private_config(self) -> None:
        self.configure()
        self.assertEqual(tomllib.loads(self.config.read_text()), {"tui": {"theme": "ayu-claude"}})
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        self.assertEqual((self.home / ".codex/AGENTS.md").resolve(), self.repo / "codex/AGENTS.md")
        for role in ROLES:
            self.assertEqual((self.home / f".codex/agents/{role}.toml").resolve(),
                             self.repo / f"codex/agents/{role}.toml")
        self.assertEqual((self.home / ".codex/themes/ayu-claude.tmTheme").resolve(),
                         self.repo / "codex/themes/ayu-claude.tmTheme")
        skills = self.home / ".agents/skills"
        self.assertEqual({path.name for path in skills.iterdir()}, set(SKILLS))
        for name in SKILLS:
            owner = "codex" if name in ("feature", "retro") else "claude"
            self.assertEqual((skills / name).resolve(), self.repo / owner / "skills" / name)
        self.assertEqual(self.backups(), [])

    def test_existing_config_changes_only_theme_bytes_and_semantics(self) -> None:
        before = ('# User comment\r\nmodel = "fixture-model"\r\n'
                  'approval_policy = "on-request"\r\n\r\n[tui] # Appearance\r\n'
                  'theme = "old" # Keep this comment\r\nanimations = false\r\n'
                  '[tui.model_availability_nux]\r\nfixture = 4\r\n'
                  '[other]\r\ntheme = "keep"\r\n')
        self.write(self.config, before)
        self.config.chmod(0o640)
        self.configure()
        self.assertEqual(self.config.read_bytes(), before.replace('theme = "old"',
                                                                  'theme = "ayu-claude"').encode())
        expected = tomllib.loads(before)
        expected["tui"]["theme"] = "ayu-claude"
        self.assertEqual(tomllib.loads(self.config.read_text()), expected)
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o640)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual((self.backups()[0] / "config.toml").read_bytes(), before.encode())

    def test_adds_theme_to_existing_table_without_changing_other_lines(self) -> None:
        before = 'model = "fixture-model"\n[tui]\nanimations = false\n[other]\nx = 1\n'
        self.write(self.config, before)
        self.configure()
        self.assertEqual(self.config.read_text(), before.replace('[tui]\n',
                                                                 '[tui]\ntheme = "ayu-claude"\n'))

    def test_adds_missing_table_and_preserves_original_without_final_newline(self) -> None:
        before = 'model = "fixture-model"\napproval_policy = "on-request"'
        self.write(self.config, before)
        self.configure()
        self.assertEqual(self.config.read_text(), before + '\n\n[tui]\ntheme = "ayu-claude"\n')

    def test_quoted_theme_key_is_supported(self) -> None:
        before = "[tui]\n  'theme' = 'old' # keep\n"
        self.write(self.config, before)
        self.configure()
        self.assertEqual(self.config.read_text(), "[tui]\n  'theme' = \"ayu-claude\" # keep\n")

    def test_repeat_apply_is_byte_and_metadata_identical(self) -> None:
        self.write(self.config, 'model = "fixture-model"\n')
        self.write(self.home / ".codex/AGENTS.md", "Prior guidance\n")
        self.configure()
        before = self.snapshot()
        self.configure()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.backups()), 1)

    def test_guidance_and_config_are_backed_up_privately_before_replacement(self) -> None:
        self.write(self.config, 'model = "fixture-model"\n')
        guidance = self.home / ".codex/AGENTS.md"
        self.write(guidance, "Prior guidance\n")
        real_replace = codex_setup.os.replace

        def check_backup_before_config_replace(source: str, destination: Path) -> None:
            backups = self.backups()
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "AGENTS.md").read_text(), "Prior guidance\n")
            self.assertEqual((backups[0] / "config.toml").read_text(), 'model = "fixture-model"\n')
            real_replace(source, destination)

        with mock.patch.object(codex_setup.os, "replace", side_effect=check_backup_before_config_replace):
            self.configure()
        backup = self.backups()[0]
        for directory in (backup.parent, backup):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        for file in backup.iterdir():
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
        self.assertTrue(guidance.is_symlink())

    def test_conflicting_destinations_and_unrelated_entries_are_preserved(self) -> None:
        skill = self.home / ".agents/skills/feature/SKILL.md"
        agent = self.home / ".codex/agents/implementer.toml"
        unrelated = self.home / ".codex/agents/go-code-reviewer.toml"
        self.write(skill, "user-owned")
        self.write(agent, "user-agent")
        self.write(unrelated, "existing-reviewer")
        other_theme = self.home / "other.tmTheme"
        self.write(other_theme, "user-theme")
        theme = self.home / ".codex/themes/ayu-claude.tmTheme"
        theme.parent.mkdir(parents=True)
        theme.symlink_to(other_theme)
        output = self.configure()
        self.assertEqual(skill.read_text(), "user-owned")
        self.assertFalse(skill.parent.is_symlink())
        self.assertEqual(agent.read_text(), "user-agent")
        self.assertFalse(agent.is_symlink())
        self.assertEqual(unrelated.read_text(), "existing-reviewer")
        self.assertEqual(theme.readlink(), other_theme)
        self.assertEqual(other_theme.read_text(), "user-theme")
        self.assertIn("Skipping", output)

    def test_existing_config_symlink_is_preserved(self) -> None:
        target = self.home / "config-source/live.toml"
        self.write(target, 'model = "fixture-model"\n')
        target.chmod(0o640)
        self.config.parent.mkdir(parents=True)
        self.config.symlink_to(target)
        self.configure()
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(self.config.readlink(), target)
        self.assertEqual(tomllib.loads(target.read_text())["tui"]["theme"], "ayu-claude")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
        self.assertEqual((self.backups()[0] / "config.toml").read_text(), 'model = "fixture-model"\n')

    def test_replaced_guidance_symlink_does_not_edit_its_original_target(self) -> None:
        target = self.home / "prior-guidance.md"
        self.write(target, "Prior linked guidance\n")
        guidance = self.home / ".codex/AGENTS.md"
        guidance.parent.mkdir(parents=True)
        guidance.symlink_to(target)
        self.configure()
        self.assertEqual(target.read_text(), "Prior linked guidance\n")
        self.assertEqual((self.backups()[0] / "AGENTS.md").read_text(), "Prior linked guidance\n")
        self.assertEqual(guidance.resolve(), self.repo / "codex/AGENTS.md")

    def test_invalid_and_unsupported_config_fail_before_any_writes(self) -> None:
        for config in ('model = [', 'model = "a"\nmodel = "b"\n',
                       'tui = {theme = "old"}\n', 'tui.theme = "old"\n',
                       '[tui]\ntheme = """old\ntheme"""\n'):
            with self.subTest(config=config):
                self.write(self.config, config)
                before = self.snapshot()
                with self.assertRaises(codex_setup.SetupError):
                    self.configure()
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.backups(), [])

    def test_invalid_config_cli_returns_nonzero_without_writes(self) -> None:
        self.write(self.config, "model = [")
        before = self.snapshot()
        with mock.patch.object(codex_setup, "REPO_ROOT", self.repo), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            result = codex_setup.main(["--home", str(self.home), "--apply"])
        self.assertNotEqual(result, 0)
        self.assertIn("config.toml", errors.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_linux_excludes_only_mac_skills(self) -> None:
        self.configure(system="Linux")
        names = {path.name for path in (self.home / ".agents/skills").iterdir()}
        self.assertEqual(len(names), 20)
        self.assertEqual(names, set(SKILLS) - {"mac-audit", "mac-space"})


if __name__ == "__main__":
    unittest.main()
