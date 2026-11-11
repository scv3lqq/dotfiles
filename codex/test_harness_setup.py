"""Focused checks for safe, opt-in global harness provisioning."""

from __future__ import annotations

import contextlib
import copy
import io
import os
from pathlib import Path
import stat
import tempfile
import tomllib
import unittest
from unittest import mock

import setup


ROLES = ("harness-orchestrator", "harness-explorer", "harness-implementer",
         "harness-reviewer", "harness-validator", "harness-archivist")
ROUTER = "You are the Planner. Read the user-scope harness skill."
SECRET = "fixture-private-value"


class GlobalHarnessSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.home = self.base / "home"
        self.config = self.home / ".codex/config.toml"
        self.write(self.repo / ".codex/config.toml",
                   f'developer_instructions = "{ROUTER}"\n')
        self.write(self.repo / "codex/skills/harness/SKILL.md", "fixture skill\n")
        self.write(self.repo / "codex/skills/harness/references/protocol.md", "fixture protocol\n")
        self.write(self.repo / "codex/harness/state.py", "# fixture\n")
        link = self.repo / "codex/skills/harness/scripts/state.py"
        link.parent.mkdir(parents=True)
        link.symlink_to("../../../harness/state.py")
        for name in ROLES:
            self.write(self.repo / f"codex/agents/{name}.toml",
                       f'name = "{name}"\ndescription = "{name} fixture"\n')
        self.write(self.config,
                   f'# keep comment\nmodel = "old" # model comment\n'
                   f'model_reasoning_effort = "high"\n'
                   f'developer_instructions = "Keep this instruction." # keep\n'
                   f'approval_policy = "on-request"\n'
                   f'[agents] # keep agents comment\n'
                   f'default_subagent_model = "old-child"\n'
                   f'[agents.existing]\ndescription = "old role"\n'
                   f'[mcp_servers.example.env]\nTOKEN = "{SECRET}"\n')
        self.config.chmod(0o640)

    @staticmethod
    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")

    def run_setup(self, *, apply: bool = False) -> str:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            setup.configure_harness(self.home, apply=apply, repo_root=self.repo)
        return output.getvalue()

    def link_paths(self) -> list[Path]:
        return [self.home / ".agents/skills/harness"]

    def backups(self) -> list[Path]:
        return sorted((self.home / ".claude/backups").glob("codex-*"))

    def test_preview_is_read_only_and_does_not_disclose_config(self) -> None:
        before = self.config.read_bytes()
        result = self.run_setup()
        self.assertIn("Preview", result)
        self.assertNotIn(SECRET, result)
        self.assertEqual(before, self.config.read_bytes())
        self.assertFalse(any(path.exists() or path.is_symlink() for path in self.link_paths()))
        self.assertEqual([], self.backups())

    def test_preview_reports_managed_role_links_to_remove(self) -> None:
        for name in ROLES[:2]:
            link = self.home / f'.codex/agents/{name}.toml'
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(self.repo / f'codex/agents/{name}.toml')
        before = self.config.read_bytes()
        result = self.run_setup()
        self.assertIn('2 managed role links to remove', result)
        self.assertEqual(before, self.config.read_bytes())
        self.assertTrue(all((self.home / f'.codex/agents/{name}.toml').is_symlink() for name in ROLES[:2]))
        self.assertEqual([], self.backups())

    def test_managed_roles_use_only_registry_after_repeated_setup(self) -> None:
        self.run_setup(apply=True)
        self.run_setup(apply=True)
        agents = tomllib.loads(self.config.read_text())["agents"]
        for role in ROLES:
            self.assertIn("config_file", agents[role])
            self.assertFalse((self.home / f".codex/agents/{role}.toml").exists())

    def test_apply_preserves_settings_comments_mode_and_is_idempotent(self) -> None:
        before = tomllib.loads(self.config.read_text())
        result = self.run_setup(apply=True)
        self.assertNotIn(SECRET, result)
        after = tomllib.loads(self.config.read_text())
        self.assertEqual("gpt-6.1-sol", after["model"])
        self.assertEqual("medium", after["model_reasoning_effort"])
        self.assertIn("Keep this instruction.", after["developer_instructions"])
        self.assertIn(str(self.home / ".agents/skills/harness/SKILL.md"), after["developer_instructions"])
        self.assertIn(ROUTER, after["developer_instructions"])
        self.assertEqual(before["mcp_servers"], after["mcp_servers"])
        self.assertEqual(before["agents"]["existing"], after["agents"]["existing"])
        expected = copy.deepcopy(before)
        expected['model'] = 'gpt-6.1-sol'
        expected['model_reasoning_effort'] = 'medium'
        expected['developer_instructions'] = (
            'Keep this instruction.\n\n[harness managed begin]\n'
            f'Canonical user-scope harness SKILL.md: {self.home / ".agents/skills/harness/SKILL.md"}\n'
            f'{ROUTER}\n[harness managed end]'
        )
        expected['agents'].update({
            'enabled': True, 'max_depth': 2, 'max_concurrent_threads_per_session': 3,
            'default_subagent_model': 'gpt-6.1-terra', 'default_subagent_reasoning_effort': 'medium',
        })
        for name in ROLES:
            expected['agents'][name] = {
                'description': f'{name} fixture',
                'config_file': str(self.repo / f'codex/agents/{name}.toml'),
            }
        self.assertEqual(expected, after)
        self.assertEqual("gpt-6.1-terra", after["agents"]["default_subagent_model"])
        self.assertEqual("medium", after["agents"]["default_subagent_reasoning_effort"])
        self.assertEqual(2, after["agents"]["max_depth"])
        self.assertEqual(3, after["agents"]["max_concurrent_threads_per_session"])
        self.assertTrue(after["agents"]["enabled"])
        self.assertIn('# keep comment', self.config.read_text())
        self.assertIn('# model comment', self.config.read_text())
        self.assertEqual(0o640, stat.S_IMODE(self.config.stat().st_mode))
        self.assertEqual(1, len(self.backups()))
        self.assertEqual(0o600, stat.S_IMODE((self.backups()[0] / 'config.toml').stat().st_mode))
        for name in ROLES:
            source = self.repo / f"codex/agents/{name}.toml"
            self.assertEqual(str(source), after["agents"][name]["config_file"])
        self.assertTrue(all(path.is_symlink() and path.exists() for path in self.link_paths()))
        snapshot = self.config.read_bytes()
        stat_before = self.config.stat().st_mtime_ns
        self.run_setup(apply=True)
        self.assertEqual(snapshot, self.config.read_bytes())
        self.assertEqual(stat_before, self.config.stat().st_mtime_ns)
        self.assertEqual(1, len(self.backups()))

    def test_crlf_and_quoted_keys_preserve_format(self) -> None:
        self.write(self.config, "# retained\r\n'model' = 'old' # c\r\n[agents] # agents\r\n")
        self.run_setup(apply=True)
        result = self.config.read_bytes()
        self.assertNotIn(b'\n', result.replace(b'\r\n', b''))
        self.assertIn(b"'model' = \"gpt-6.1-sol\" # c\r\n", result)
        self.assertIn(b'[agents] # agents\r\n', result)
        tomllib.loads(result.decode())

    def test_managed_block_update_preserves_surrounding_instructions(self) -> None:
        self.run_setup(apply=True)
        first = tomllib.loads(self.config.read_text())["developer_instructions"]
        self.write(self.repo / ".codex/config.toml",
                   'developer_instructions = "Updated user-scope harness routing."\n')
        self.run_setup(apply=True)
        second = tomllib.loads(self.config.read_text())["developer_instructions"]
        self.assertIn("Keep this instruction.", second)
        self.assertIn("Updated user-scope harness routing.", second)
        self.assertNotIn(ROUTER, second)
        self.assertNotEqual(first, second)

    def test_unrecognized_marker_block_does_not_overwrite_user_text(self) -> None:
        self.write(self.config,
                   'developer_instructions = "Before [harness managed begin] user text '
                   '[harness managed end] after"\n')
        original = self.config.read_bytes()
        with self.assertRaises(setup.SetupError):
            self.run_setup(apply=True)
        self.assertEqual(original, self.config.read_bytes())
        self.assertEqual([], self.backups())

    def test_skill_source_and_destination_parent_must_not_escape(self) -> None:
        outside = self.base / 'outside'
        outside.mkdir()
        src = self.repo / 'codex/skills/harness/SKILL.md'
        src.unlink()
        self.write(outside / 'SKILL.md', 'external')
        src.symlink_to(outside / 'SKILL.md')
        with self.assertRaises(setup.SetupError):
            self.run_setup(apply=True)
        src.unlink()
        self.write(src, 'fixture skill')
        (self.home / '.agents').mkdir()
        (self.home / '.agents/skills').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(setup.SetupError):
            self.run_setup(apply=True)
        self.assertEqual([], self.backups())

    def test_foreign_destinations_and_registry_conflict_fail_without_writes(self) -> None:
        for kind in ("skill", "role", "registry"):
            with self.subTest(kind=kind):
                if kind == "skill":
                    self.write(self.home / '.agents/skills/harness/SKILL.md', 'foreign')
                elif kind == "role":
                    self.write(self.home / '.codex/agents/harness-reviewer.toml', 'foreign')
                else:
                    with self.config.open('a') as stream:
                        stream.write('\n[agents.harness-reviewer]\nconfig_file = "/other.toml"\n')
                before = self.config.read_bytes()
                with self.assertRaises(setup.SetupError):
                    self.run_setup(apply=True)
                self.assertEqual(before, self.config.read_bytes())
                self.assertEqual([], self.backups())
                self.assertFalse((self.home / '.codex/agents/harness-orchestrator.toml').exists())
                if kind == "skill":
                    (self.home / '.agents/skills/harness/SKILL.md').unlink()
                    (self.home / '.agents/skills/harness').rmdir()
                elif kind == "role":
                    (self.home / '.codex/agents/harness-reviewer.toml').unlink()

    def test_missing_source_or_legacy_router_is_rejected_before_writes(self) -> None:
        role = self.repo / 'codex/agents/harness-reviewer.toml'
        role.unlink()
        before = self.config.read_bytes()
        with self.assertRaises(setup.SetupError):
            self.run_setup(apply=True)
        self.assertEqual(before, self.config.read_bytes())
        self.assertEqual([], self.backups())
        self.write(role, 'name = "harness-reviewer"\ndescription = "review"\n')
        self.write(self.repo / '.codex/config.toml', 'developer_instructions = "Read codex/skills/harness/SKILL.md"\n')
        with self.assertRaises(setup.SetupError):
            self.run_setup(apply=True)
        self.assertEqual(before, self.config.read_bytes())
        self.assertEqual([], self.backups())

    def test_missing_foreign_or_directory_protocol_fails_before_writes(self) -> None:
        protocol = self.repo / 'codex/skills/harness/references/protocol.md'
        outside = self.base / 'external-protocol.md'
        self.write(outside, 'external')
        for kind in ('missing', 'foreign', 'directory'):
            with self.subTest(kind=kind):
                if protocol.is_symlink() or protocol.is_file():
                    protocol.unlink()
                elif protocol.is_dir():
                    protocol.rmdir()
                if kind == 'foreign':
                    protocol.symlink_to(outside)
                elif kind == 'directory':
                    protocol.mkdir()
                original = self.config.read_bytes()
                with self.assertRaises(setup.SetupError):
                    self.run_setup(apply=True)
                self.assertEqual(original, self.config.read_bytes())
                self.assertEqual([], self.backups())
                self.assertFalse(any(p.is_symlink() for p in self.link_paths()))

    def test_multiline_inline_alias_and_invalid_config_fail_safely(self) -> None:
        cases = ['developer_instructions = """long\ninstruction"""\n',
                 'agents = { max_depth = 1 }\n', '[agents]\nmax_threads = 2\n',
                 'agents.max_depth = 1\n', 'model = [\n']
        for text in cases:
            with self.subTest(text=text):
                self.write(self.config, text)
                before = self.config.read_bytes()
                with self.assertRaises(setup.SetupError):
                    self.run_setup(apply=True)
                self.assertEqual(before, self.config.read_bytes())
                self.assertEqual([], self.backups())

    def test_link_failure_rolls_back_only_owned_links_before_activation(self) -> None:
        original = self.config.read_bytes()
        original_symlink = Path.symlink_to
        def fail_one(path: Path, target: os.PathLike[str] | str, target_is_directory: bool = False) -> None:
            if path.name == 'harness':
                raise OSError('fixture link failure')
            original_symlink(path, target, target_is_directory=target_is_directory)
        with mock.patch.object(Path, 'symlink_to', fail_one):
            with self.assertRaises(OSError):
                self.run_setup(apply=True)
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(any(p.is_symlink() for p in self.link_paths()))

    def test_drift_after_backup_aborts_and_preserves_external_change(self) -> None:
        original_backup = setup.backup_harness_config
        changed = b'model = "concurrent"\n'
        def change_after_backup(home: Path, original: bytes) -> None:
            original_backup(home, original)
            self.config.write_bytes(changed)
        with mock.patch.object(setup, 'backup_harness_config', change_after_backup):
            with self.assertRaises(setup.SetupError):
                self.run_setup(apply=True)
        self.assertEqual(changed, self.config.read_bytes())
        self.assertFalse(any(p.is_symlink() for p in self.link_paths()))

    def test_late_unreadable_config_preserves_original_error_and_rolls_back(self) -> None:
        original = self.config.read_bytes()
        original_read = Path.read_bytes
        reads = 0
        def fail_late(path: Path) -> bytes:
            nonlocal reads
            if path == self.config:
                reads += 1
                if reads >= 2:
                    raise PermissionError('fixture late read denied')
            return original_read(path)
        with mock.patch.object(Path, 'read_bytes', fail_late):
            with self.assertRaisesRegex(PermissionError, 'fixture late read denied'):
                self.run_setup(apply=True)
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(any(p.is_symlink() for p in self.link_paths()))

    def test_uncertain_replace_retains_links_without_masking_original_error(self) -> None:
        original_replace = os.replace
        original_read = Path.read_bytes
        state = {'replaced': False}
        def replace_then_fail(source: os.PathLike[str] | str, target: os.PathLike[str] | str) -> None:
            original_replace(source, target)
            state['replaced'] = True
            raise OSError('fixture uncertain replace')
        def fail_after_replace(path: Path) -> bytes:
            if path == self.config and state['replaced']:
                raise PermissionError('fixture cannot inspect activation')
            return original_read(path)
        stderr = io.StringIO()
        with mock.patch.object(setup.os, 'replace', replace_then_fail), \
             mock.patch.object(Path, 'read_bytes', fail_after_replace), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(OSError, 'fixture uncertain replace'):
                self.run_setup(apply=True)
        self.assertTrue(all(p.is_symlink() and p.exists() for p in self.link_paths()))
        self.assertIn('retained', stderr.getvalue())
        self.assertEqual('gpt-6.1-sol', tomllib.loads(self.config.read_text())['model'])

    def test_existing_activation_keeps_repaired_link_on_setup_failure(self) -> None:
        self.run_setup(apply=True)
        original = self.config.read_bytes()
        skill = self.home / '.agents/skills/harness'
        skill.unlink()
        self.write(self.repo / '.codex/config.toml',
                   'developer_instructions = "Updated user-scope harness routing."\n')
        stderr = io.StringIO()
        with mock.patch.object(setup, 'atomic_harness_write', side_effect=OSError('fixture write failure')), contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(OSError, 'fixture write failure'):
                self.run_setup(apply=True)
        self.assertEqual(original, self.config.read_bytes())
        self.assertTrue(skill.is_symlink())
        self.assertIn('retained', stderr.getvalue())

    def test_symlinked_config_target_is_updated_without_replacing_link(self) -> None:
        target = self.home / 'shared/config.toml'
        target.parent.mkdir(parents=True)
        target.write_bytes(self.config.read_bytes())
        target.chmod(0o640)
        self.config.unlink()
        self.config.symlink_to(target)
        self.run_setup(apply=True)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual('gpt-6.1-sol', tomllib.loads(target.read_text())['model'])
        self.assertEqual(0o640, stat.S_IMODE(target.stat().st_mode))

    def test_cli_dispatch_is_scoped(self) -> None:
        with mock.patch.object(setup, 'configure_harness') as harness, mock.patch.object(setup, 'configure') as normal:
            self.assertEqual(0, setup.main(['--global-harness', '--home', str(self.home), '--apply']))
        harness.assert_called_once_with(self.home, apply=True)
        normal.assert_not_called()

    def test_original_cli_dispatch_remains_unchanged(self) -> None:
        with mock.patch.object(setup, 'configure_harness') as harness, mock.patch.object(setup, 'configure') as normal:
            self.assertEqual(0, setup.main(['--home', str(self.home), '--apply']))
        normal.assert_called_once_with(self.home, apply=True)
        harness.assert_not_called()


if __name__ == '__main__':
    unittest.main()
