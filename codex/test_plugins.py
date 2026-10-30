"""Behavior checks for preparing complete packages in synthetic homes."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import plugins as codex_plugins

SELECTION = (
    ("data@claude-plugins-official", "astronomer-data"),
    ("0bull@anthropic-plugin-directory", "0bull"),
    ("frontend-design@anthropic-plugin-directory", "frontend-design"),
    ("humanizer-blader@anthropic-plugin-directory", "humanizer"),
)
HOOK_COMMAND = '"${CLAUDE_PLUGIN_ROOT}/scripts/session.sh" start --note \'quoted\'\n'
HUMANIZER_BODY = b"---\r\nname: humanizer\r\n---\r\nKeep exact bytes: \xc3\xa9.\r\n"


class PluginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / "home"
        self.destination = self.home / ".codex/plugin-sources/claude-parity"
        self.registry = self.home / ".claude/plugins/installed_plugins.json"
        self.settings = self.home / ".claude/settings.json"
        self.sources: dict[str, Path] = {}
        records: dict[str, list[dict[str, str]]] = {}
        for registry_id, name in SELECTION:
            source = self.home / "source-packages" / name
            self.sources[name] = source
            manifest: dict[str, object] = {"name": name, "version": "2.3.4"}
            if name == "astronomer-data":
                manifest["hooks"] = {
                    "SessionStart": [{"hooks": [{"type": "command", "command": HOOK_COMMAND}]}],
                    "Stop": [{"hooks": [{"type": "command", "command": "fixture-stop --exact"}]}],
                }
                for index in range(34):
                    self.write(source / f"skills/data-{index:02d}/SKILL.md", f"Skill {index}\n")
            elif name == "humanizer":
                self.write(source / "SKILL.md", HUMANIZER_BODY)
            else:
                self.write(source / f"skills/{name}/SKILL.md", f"Skill {name}\n")
            self.write_json(source / ".claude-plugin/plugin.json", manifest)
            self.write(source / "LICENSE", f"Fixture license: {name}\n")
            records[registry_id] = [{"scope": "user", "installPath": str(source)}]
        data = self.sources["astronomer-data"]
        self.write(data / "scripts/session.sh", "#!/bin/sh\nprintf fixture\n")
        (data / "scripts/session.sh").chmod(0o750)
        self.write(data / "resources/nested/example.sql", "SELECT 'fixture';\n")
        (data / "skills/data-00/example.sql").symlink_to("../../resources/nested/example.sql")
        (data / "linked-resources").symlink_to("resources", target_is_directory=True)
        self.write_json(self.sources["0bull"] / ".mcp.json", {
            "mcpServers": {"0bull": {"command": "fixture-server", "args": ["--fixture"]}},
        })
        self.write_json(self.registry, {"version": 2, "plugins": records})
        self.write_json(self.settings, {
            "enabledPlugins": dict.fromkeys((item[0] for item in SELECTION), True),
            "opaque": "fixture-private-value",
        })
        self.write(self.home / ".codex/config.toml", 'model = "fixture-model"\n')
        self.write(self.home / ".codex/plugins/cache/keep", "Unrelated cache\n")
        self.write(self.home / ".agents/skills/keep/SKILL.md", "Unrelated skill\n")

    @staticmethod
    def write(path: Path, content: str | bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def write_json(self, path: Path, content: object) -> None:
        self.write(path, json.dumps(content, indent=2) + "\n")

    @staticmethod
    def read_json(path: Path) -> dict[str, object]:
        result = json.loads(path.read_bytes())
        assert isinstance(result, dict)
        return result

    @staticmethod
    def snapshot(root: Path) -> dict[str, tuple[int, int, bytes | str]]:
        result = {}
        if not root.exists():
            return result
        for path in sorted(root.rglob("*")):
            info = path.lstat()
            if path.is_symlink():
                content: bytes | str = str(path.readlink())
            elif stat.S_ISREG(info.st_mode):
                content = path.read_bytes()
            else:
                content = b""
            result[path.relative_to(root).as_posix()] = (
                info.st_mode, info.st_mtime_ns, content,
            )
        return result

    def backups(self) -> list[Path]:
        return sorted((self.home / ".claude/backups").glob("codex-plugins-*"))

    def prepare(self, *, apply: bool = True) -> Path:
        return codex_plugins.prepare_marketplace(self.home, apply=apply)

    def assert_rejected_without_writes(self) -> None:
        before = self.snapshot(self.home)
        with self.assertRaises((ValueError, OSError)):
            self.prepare()
        self.assertEqual(self.snapshot(self.home), before)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.backups(), [])

    def test_preview_validates_without_any_writes(self) -> None:
        before = self.snapshot(self.home)
        self.assertEqual(self.prepare(apply=False), self.destination)
        self.assertEqual(self.snapshot(self.home), before)
        self.assertFalse(self.destination.parent.exists())

    def test_apply_yields_exact_marketplace_and_37_skills(self) -> None:
        self.assertEqual(self.prepare(), self.destination)
        marketplace = self.read_json(self.destination / ".agents/plugins/marketplace.json")
        self.assertEqual(marketplace, {
            "name": "claude-parity",
            "plugins": [
                {
                    "name": name,
                    "source": {"source": "local", "path": f"./plugins/{name}"},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                    "category": "Productivity",
                }
                for _, name in SELECTION
            ],
        })
        skills = list((self.destination / "plugins").glob("*/skills/*/SKILL.md"))
        self.assertEqual(len(skills), 37)
        self.assertEqual({path.parent.name for path in skills}, {
            *(f"data-{index:02d}" for index in range(34)),
            "0bull", "frontend-design", "humanizer",
        })

    def test_data_adapter_preserves_hook_commands_exactly(self) -> None:
        self.prepare()
        data = self.destination / "plugins/astronomer-data"
        self.assertEqual(self.read_json(data / ".codex-plugin/plugin.json"), {
            "name": "astronomer-data", "version": "2.3.4",
            "skills": "./skills/", "hooks": "./hooks/hooks.json",
        })
        hooks = self.read_json(data / "hooks/hooks.json")
        self.assertEqual(hooks, {"hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": HOOK_COMMAND}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "fixture-stop --exact"}]}],
        }})

    def test_humanizer_adapter_preserves_body_and_existing_manifests(self) -> None:
        self.prepare()
        humanizer = self.destination / "plugins/humanizer"
        self.assertEqual((humanizer / "skills/humanizer/SKILL.md").read_bytes(), HUMANIZER_BODY)
        self.assertEqual((humanizer / "SKILL.md").read_bytes(), HUMANIZER_BODY)
        self.assertEqual(self.read_json(humanizer / ".codex-plugin/plugin.json"), {
            "name": "humanizer", "version": "2.3.4", "skills": "./skills/",
        })
        for name in ("0bull", "frontend-design"):
            with self.subTest(name=name):
                package = self.destination / "plugins" / name
                self.assertFalse((package / ".codex-plugin").exists())
                self.assertEqual((package / ".claude-plugin/plugin.json").read_bytes(),
                                 (self.sources[name] / ".claude-plugin/plugin.json").read_bytes())

    def test_complete_resources_mcp_and_internal_symlinks_are_preserved(self) -> None:
        before = self.snapshot(self.home / "source-packages")
        self.prepare()
        self.assertEqual(self.snapshot(self.home / "source-packages"), before)
        for _, name in SELECTION:
            self.assertEqual((self.destination / f"plugins/{name}/LICENSE").read_text(),
                             f"Fixture license: {name}\n")
        data = self.destination / "plugins/astronomer-data"
        self.assertEqual((data / "resources/nested/example.sql").read_text(), "SELECT 'fixture';\n")
        self.assertEqual((data / "scripts/session.sh").read_bytes(),
                         b"#!/bin/sh\nprintf fixture\n")
        self.assertEqual(stat.S_IMODE((data / "scripts/session.sh").stat().st_mode), 0o750)
        for relative, target in (
            ("skills/data-00/example.sql", "../../resources/nested/example.sql"),
            ("linked-resources", "resources"),
        ):
            self.assertTrue((data / relative).is_symlink())
            self.assertEqual((data / relative).readlink(), Path(target))
        self.assertEqual((self.destination / "plugins/0bull/.mcp.json").read_bytes(),
                         (self.sources["0bull"] / ".mcp.json").read_bytes())

    def test_global_config_registry_and_unrelated_cache_are_unchanged(self) -> None:
        preserved = [self.settings, self.registry, self.home / ".codex/config.toml",
                     self.home / ".codex/plugins/cache/keep",
                     self.home / ".agents/skills/keep/SKILL.md"]
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in preserved}
        self.prepare()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns)
                          for path in preserved}, before)

    def test_marker_is_versioned_hashed_and_contains_no_source_paths(self) -> None:
        self.prepare()
        marker = self.read_json(self.destination / ".codex-parity.json")
        self.assertEqual(set(marker), {"schema", "source_sha256", "content_sha256"})
        self.assertEqual(marker["schema"], 1)
        for field in ("source_sha256", "content_sha256"):
            self.assertRegex(str(marker[field]), r"^[0-9a-f]{64}$")
        self.assertNotIn(str(self.home), (self.destination / ".codex-parity.json").read_text())

    def test_repeat_apply_leaves_all_bytes_and_mtimes_unchanged(self) -> None:
        self.prepare()
        before = self.snapshot(self.home)
        self.prepare()
        self.assertEqual(self.snapshot(self.home), before)
        self.assertEqual(self.backups(), [])

    def test_source_location_is_not_part_of_the_source_digest(self) -> None:
        self.prepare()
        before = self.snapshot(self.destination)
        source = self.sources["0bull"]
        moved = source.with_name("moved-package")
        source.rename(moved)
        registry = self.read_json(self.registry)
        registry["plugins"]["0bull@anthropic-plugin-directory"][0]["installPath"] = str(moved)
        self.write_json(self.registry, registry)
        self.prepare()
        self.assertEqual(self.snapshot(self.destination), before)
        self.assertEqual(self.backups(), [])

    def test_changed_source_is_backed_up_before_atomic_replacement(self) -> None:
        self.prepare()
        old = self.snapshot(self.destination)
        old_marker = self.read_json(self.destination / ".codex-parity.json")
        self.write(self.sources["0bull"] / "LICENSE", "Updated fixture license\n")
        real_replace = codex_plugins.os.replace

        def assert_backup_first(source: Path, destination: Path) -> None:
            if Path(destination) == self.destination:
                backups = self.backups()
                self.assertEqual(len(backups), 1)
                backup = backups[0]
                self.assertRegex(backup.name, r"^codex-plugins-\d{8}T\d{6}\.\d{6}Z$")
                self.assertEqual(self.snapshot(backup / "claude-parity"), old)
                for directory in (backup, backup / "claude-parity", Path(source).parent):
                    self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
                self.assertEqual((Path(source) / "plugins/0bull/LICENSE").read_text(),
                                 "Updated fixture license\n")
                self.assertEqual(Path(source).stat().st_dev, self.destination.parent.stat().st_dev)
            real_replace(source, destination)

        with mock.patch.object(codex_plugins.os, "replace", side_effect=assert_backup_first):
            self.prepare()
        self.assertEqual((self.destination / "plugins/0bull/LICENSE").read_text(),
                         "Updated fixture license\n")
        marker = self.read_json(self.destination / ".codex-parity.json")
        self.assertNotEqual(marker["source_sha256"], old_marker["source_sha256"])
        self.assertNotEqual(marker["content_sha256"], old_marker["content_sha256"])

    def test_preview_with_changed_source_creates_no_backup_or_temporary_directory(self) -> None:
        self.prepare()
        self.write(self.sources["0bull"] / "LICENSE", "Updated fixture license\n")
        before = self.snapshot(self.home)
        self.prepare(apply=False)
        self.assertEqual(self.snapshot(self.home), before)

    def test_failed_replacement_restores_the_previous_snapshot(self) -> None:
        self.prepare()
        self.write(self.destination.parent / "unrelated.json", "Keep source metadata\n")
        old = self.snapshot(self.destination)
        self.write(self.sources["0bull"] / "LICENSE", "Updated fixture license\n")
        real_replace = codex_plugins.os.replace
        replacement_failed = False

        def fail_first_install(source: Path, destination: Path) -> None:
            nonlocal replacement_failed
            if Path(destination) == self.destination and not replacement_failed:
                replacement_failed = True
                self.assertEqual(self.snapshot(self.backups()[0] / "claude-parity"), old)
                self.assertTrue((Path(source) / ".agents/plugins/marketplace.json").is_file())
                self.assertTrue((Path(source) / ".codex-parity.json").is_file())
                raise OSError("fixture replacement failure")
            real_replace(source, destination)

        with mock.patch.object(codex_plugins.os, "replace", side_effect=fail_first_install), \
                self.assertRaisesRegex(OSError, "fixture replacement failure"):
            self.prepare()
        self.assertTrue(replacement_failed)
        self.assertEqual(self.snapshot(self.destination), old)
        self.assertEqual({path.name for path in self.destination.parent.iterdir()},
                         {"claude-parity", "unrelated.json"})
        self.assertFalse((self.backups()[0] / "claude-parity").exists())

    def test_edited_destination_is_refused_without_overwrite(self) -> None:
        self.prepare()
        self.write(self.destination / "plugins/0bull/LICENSE", "Local edit\n")
        before = self.snapshot(self.home)
        with self.assertRaisesRegex(ValueError, "drift|conflict"):
            self.prepare()
        self.assertEqual(self.snapshot(self.home), before)
        self.assertEqual(self.backups(), [])

    def test_unmanaged_destination_is_refused_without_overwrite(self) -> None:
        self.write(self.destination / "keep", "User-owned directory\n")
        before = self.snapshot(self.home)
        with self.assertRaisesRegex(ValueError, "marker|managed|conflict"):
            self.prepare()
        self.assertEqual(self.snapshot(self.home), before)

    def test_invalid_ownership_marker_is_refused(self) -> None:
        self.prepare()
        marker = self.destination / ".codex-parity.json"
        for invalid in ({"schema": 2}, [], {"schema": 1, "source_sha256": "bad",
                                          "content_sha256": "bad"}):
            with self.subTest(invalid=invalid):
                self.write_json(marker, invalid)
                before = self.snapshot(self.home)
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertEqual(self.snapshot(self.home), before)

    def test_disabled_plugin_is_rejected(self) -> None:
        settings = self.read_json(self.settings)
        settings["enabledPlugins"]["humanizer-blader@anthropic-plugin-directory"] = False
        self.write_json(self.settings, settings)
        self.assert_rejected_without_writes()

    def test_duplicate_user_records_are_rejected(self) -> None:
        registry = self.read_json(self.registry)
        records = registry["plugins"]["0bull@anthropic-plugin-directory"]
        records.append(dict(records[0]))
        self.write_json(self.registry, registry)
        self.assert_rejected_without_writes()

    def test_missing_user_record_is_rejected(self) -> None:
        registry = self.read_json(self.registry)
        registry["plugins"]["0bull@anthropic-plugin-directory"][0]["scope"] = "project"
        self.write_json(self.registry, registry)
        self.assert_rejected_without_writes()

    def test_one_user_record_remains_unambiguous_with_another_scope(self) -> None:
        registry = self.read_json(self.registry)
        registry["plugins"]["0bull@anthropic-plugin-directory"].append({
            "scope": "project", "installPath": str(self.home / "unselected-project-source"),
        })
        self.write_json(self.registry, registry)
        self.prepare()
        self.assertEqual((self.destination / "plugins/0bull/LICENSE").read_text(),
                         "Fixture license: 0bull\n")

    def test_missing_source_or_manifest_is_rejected(self) -> None:
        source = self.sources["humanizer"]
        manifest = source / ".claude-plugin/plugin.json"
        original = manifest.read_bytes()
        manifest.unlink()
        self.assert_rejected_without_writes()
        self.write(manifest, original)
        registry = self.read_json(self.registry)
        registry["plugins"]["humanizer-blader@anthropic-plugin-directory"][0]["installPath"] = str(
            self.home / "missing-source")
        self.write_json(self.registry, registry)
        self.assert_rejected_without_writes()

    def test_invalid_json_is_rejected_before_target_creation(self) -> None:
        paths = [self.registry, self.settings,
                 self.sources["humanizer"] / ".claude-plugin/plugin.json",
                 self.sources["0bull"] / ".mcp.json"]
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                self.write(path, '{"fixture-private-value": [')
                self.assert_rejected_without_writes()
                self.write(path, original)

    def test_invalid_registry_shape_and_version_are_rejected(self) -> None:
        float_version = self.read_json(self.registry)
        float_version["version"] = 2.0
        for registry in ({"version": 1, "plugins": {}}, {"version": 2, "plugins": []},
                         float_version, []):
            with self.subTest(registry=registry):
                self.write_json(self.registry, registry)
                self.assert_rejected_without_writes()

    def test_non_finite_json_values_are_rejected(self) -> None:
        original = self.settings.read_bytes()
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                self.write(self.settings, original.replace(b'"fixture-private-value"', value.encode()))
                self.assert_rejected_without_writes()

    def test_wrong_manifest_name_or_version_is_rejected(self) -> None:
        path = self.sources["humanizer"] / ".claude-plugin/plugin.json"
        for manifest in ({"name": "wrong", "version": "2.3.4"},
                         {"name": "humanizer", "version": ""},
                         {"name": "humanizer", "version": 2}):
            with self.subTest(manifest=manifest):
                self.write_json(path, manifest)
                self.assert_rejected_without_writes()

    def test_wrong_skill_count_and_non_object_hooks_are_rejected(self) -> None:
        skill = self.sources["astronomer-data"] / "skills/data-33/SKILL.md"
        original = skill.read_bytes()
        skill.unlink()
        self.assert_rejected_without_writes()
        self.write(skill, original)
        path = self.sources["astronomer-data"] / ".claude-plugin/plugin.json"
        manifest = self.read_json(path)
        manifest["hooks"] = []
        self.write_json(path, manifest)
        self.assert_rejected_without_writes()

    def test_absolute_escaping_broken_and_cyclic_links_are_rejected(self) -> None:
        source = self.sources["humanizer"]
        link = source / "resource-link"
        for target in (str(self.settings), "../../.claude/settings.json", "missing", "resource-link"):
            with self.subTest(target=target):
                link.symlink_to(target)
                self.assert_rejected_without_writes()
                link.unlink()

    def test_non_regular_package_file_is_rejected(self) -> None:
        os.mkfifo(self.sources["humanizer"] / "fixture-pipe")
        self.assert_rejected_without_writes()

    def test_cli_prints_only_status_and_errors_without_configuration(self) -> None:
        for arguments, label in (([], "Preview"), (["--apply"], "Ready")):
            with self.subTest(label=label), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(codex_plugins.main(["--home", str(self.home), *arguments]), 0)
                self.assertEqual(output.getvalue(), f"{label}: {self.destination}\n")
        self.write(self.settings, '{"fixture-private-value": [')
        before = self.snapshot(self.home)
        with contextlib.redirect_stderr(io.StringIO()) as errors, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(codex_plugins.main(["--home", str(self.home), "--apply"]), 1)
        self.assertTrue(errors.getvalue().startswith("ERROR: "))
        self.assertNotIn("fixture-private-value", errors.getvalue())
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(self.snapshot(self.home), before)


if __name__ == "__main__":
    unittest.main()
