"""Validate repository Codex assets without loading personal configuration."""

import argparse
from pathlib import Path
import plistlib
import re
import tomllib


ROOT = Path(__file__).resolve().parent
ROLES = (
    ("implementer", "gpt-6.1-terra", "medium"),
    ("plan-reviewer", "gpt-6.1-sol", "high"),
    ("acceptance-validator", "gpt-6.1-terra", "medium"),
    ("skill-dry-run", "gpt-6.1-terra", "medium"),
)
HARNESS_ROLES = (
    ("harness-orchestrator", "gpt-6.1-terra", "medium"),
    ("harness-explorer", "gpt-6-luna", "low"),
    ("harness-implementer", "gpt-6.1-terra", "medium"),
    ("harness-reviewer", "gpt-6.1-sol", "high"),
    ("harness-validator", "gpt-6.1-terra", "medium"),
    ("harness-archivist", "gpt-6.1-terra", "medium"),
)
PALETTE = frozenset({
    "#0B0E14", "#E8E6DD", "#CDA1FA", "#D2A6FF", "#303030", "#E6B450",
    "#11151C", "#EA6C73", "#7FD962", "#F9AF4F", "#53BDFA", "#90E1C6",
    "#C7C7C7", "#686868", "#F07178", "#AAD94C", "#FFB454", "#59C2FF",
    "#95E6CB", "#FFFFFF",
})


def check_agents() -> None:
    for name, model, effort in ROLES:
        path = ROOT / "agents" / f"{name}.toml"
        agent = tomllib.loads(path.read_text())
        assert agent.get("name") == name, f"{path}: wrong agent name"
        for field in ("description", "developer_instructions"):
            value = agent.get(field)
            assert isinstance(value, str) and value.strip(), f"{path}: missing {field}"
        assert agent.get("model_reasoning_effort") == effort, f"{path}: wrong effort"
        assert agent.get("model") == model, f"{path}: wrong approved model"
    print("PASS: four native agents with approved models and efforts")


def check_reviewer(path: Path) -> None:
    reviewer = tomllib.loads(path.read_text())
    assert reviewer.get("name") == "go-code-reviewer", f"{path}: wrong reviewer name"
    assert reviewer.get("model") == "gpt-6.1-sol", f"{path}: wrong reviewer model"
    assert reviewer.get("model_reasoning_effort") == "high", f"{path}: wrong reviewer effort"
    print("PASS: external Go reviewer pins")


def check_guidance() -> None:
    canonical = ROOT.parent / "AGENTS.md"
    compatibility = ROOT.parent / "CLAUDE.md"
    global_guidance = ROOT / "AGENTS.md"
    assert canonical.is_file() and not canonical.is_symlink(), (
        f"{canonical}: canonical guidance must be a regular file"
    )
    assert compatibility.is_symlink(), f"{compatibility}: compatibility guidance must be a symlink"
    assert compatibility.readlink() == Path("AGENTS.md"), (
        f"{compatibility}: compatibility symlink must have relative target AGENTS.md"
    )
    assert compatibility.read_bytes() == canonical.read_bytes(), (
        f"{compatibility}: root guidance reads must be identical"
    )
    assert global_guidance.is_file() and not global_guidance.is_symlink(), (
        f"{global_guidance}: global guidance must be a regular file"
    )
    for path in (canonical, global_guidance):
        assert not re.search(r"claude|codex|anthropic|openai|opus|sonnet", path.read_text(), re.I), (
            f"{path}: guidance must have no product, provider or model-family references"
        )
    assert len(canonical.read_text().splitlines()) < 200, (
        f"{canonical}: canonical guidance must remain under 200 lines"
    )
    guard = ROOT.parent / "bin/wait-free-checkout.sh"
    assert guard.is_symlink(), f"{guard}: checkout guard alias must be a symlink"
    assert guard.readlink() == Path("../.claude/bin/wait-free-checkout.sh"), (
        f"{guard}: checkout guard alias must have the existing relative target"
    )
    assert guard.is_file(), f"{guard}: checkout guard alias must resolve to a regular file"
    print("PASS: neutral guidance, canonical file and compatibility links")


def check_project() -> None:
    project = ROOT.parent / ".codex"
    config = project / "config.toml"
    assert config.is_file() and not config.is_symlink(), (
        f"{config}: project config must be a regular file"
    )
    registrations = {
        name: {
            "description": tomllib.loads((ROOT / "agents" / f"{name}.toml").read_text())["description"],
            "config_file": f"../codex/agents/{name}.toml",
        }
        for name, _model, _effort in (*ROLES, *HARNESS_ROLES)
    }
    actual = tomllib.loads(config.read_text())
    developer_instructions = actual.get("developer_instructions")
    assert isinstance(developer_instructions, str) and developer_instructions.strip(), (
        f"{config}: missing planner instructions"
    )
    assert "user-scope harness" in developer_instructions, (
        f"{config}: planner must route to the harness skill"
    )
    assert "codex/skills/harness/SKILL.md" not in developer_instructions, (
        f"{config}: planner routing must not depend on the target project"
    )
    assert actual == {
        "model": "gpt-6.1-sol", "model_reasoning_effort": "medium",
        "developer_instructions": developer_instructions,
        "agents": {
            "enabled": True,
            "max_depth": 2,
            "max_concurrent_threads_per_session": 3,
            "default_subagent_model": "gpt-6.1-terra",
            "default_subagent_reasoning_effort": "medium",
            **registrations,
        },
    }, f"{config}: project config must contain only approved settings"
    for name, registration in registrations.items():
        source = ROOT / "agents" / f"{name}.toml"
        assert (project / registration["config_file"]).resolve() == source.resolve(), (
            f"{config}: registry must resolve to the canonical source for {name}"
        )
        assert source.is_file(), f"{source}: canonical agent source must exist"
    for name, _model, _effort in (*ROLES, *HARNESS_ROLES):
        path = project / "agents" / f"{name}.toml"
        assert not path.exists() and not path.is_symlink(), (
            f"{path}: duplicate standalone role registration"
        )
    for name, source in (
        ("setup-dotfiles", ".claude"),
        ("docs-sync", ".claude"),
        ("readme-screenshots", ".claude"),
        ("feature", "codex"),
        ("retro", "codex"),
        ("harness", "codex"),
    ):
        path = ROOT.parent / ".agents/skills" / name
        assert path.is_symlink(), f"{path}: project skill must be a symlink"
        assert path.readlink() == Path(f"../../{source}/skills/{name}"), (
            f"{path}: project skill must have the exact relative source target"
        )
        assert path.is_dir(), f"{path}: project skill source must exist"
    resource = ROOT.parent / ".agents/skills/readme-screenshots/scripts/claude.c"
    assert resource.is_file(), f"{resource}: linked screenshot resource must exist"
    print("PASS: project configuration, shared agents and project skills")


def check_harness() -> None:
    check_project()
    for name, model, effort in HARNESS_ROLES:
        path = ROOT / "agents" / f"{name}.toml"
        role = tomllib.loads(path.read_text())
        assert role.get("name") == name, f"{path}: wrong agent name"
        assert role.get("model") == model, f"{path}: wrong model"
        assert role.get("model_reasoning_effort") == effort, f"{path}: wrong effort"
        for field in ("description", "developer_instructions"):
            value = role.get(field)
            assert isinstance(value, str) and value.strip(), f"{path}: missing {field}"
        assert "user-scope harness" in role["developer_instructions"], (
            f"{path}: missing user-scope skill reference"
        )
        assert "references/protocol.md" in role["developer_instructions"], (
            f"{path}: missing protocol reference"
        )
        assert "codex/skills/harness/" not in role["developer_instructions"], (
            f"{path}: protocol reference must not depend on the target project"
        )
    skill = ROOT / "skills/harness/SKILL.md"
    text = skill.read_text()
    sections = text.split("---", 2)
    assert text.startswith("---\n") and len(sections) == 3, f"{skill}: no frontmatter"
    assert re.search(r"^name: harness$", sections[1], re.M), f"{skill}: wrong name"
    assert re.search(r"^description: \S.+$", sections[1], re.M), f"{skill}: no description"
    for target in re.findall(r"\]\(([^)]+)\)", sections[2]):
        assert (skill.parent / target).resolve().is_file(), f"{skill}: missing {target}"
    helper = skill.parent / "scripts/state.py"
    assert helper.is_symlink(), f"{helper}: helper must be a shared symlink"
    assert helper.readlink() == Path("../../../harness/state.py"), (
        f"{helper}: helper must point to the canonical source"
    )
    assert helper.is_file(), f"{helper}: canonical helper source must exist"
    harness = ROOT.parent / ".harness"
    assert (harness / "README.md").is_file(), f"{harness}: missing guide"
    ignore = (harness / ".gitignore").read_text().splitlines()
    assert ignore == ["*", "!.gitignore", "!README.md"], f"{harness}: unsafe ignore rules"
    print("PASS: harness roles, skill and runtime artifact layout")


def check_theme() -> None:
    with (ROOT / "themes/ayu-claude.tmTheme").open("rb") as source:
        theme = plistlib.load(source)
    assert theme["name"] == "Ayu Claude", "wrong theme name"
    assert theme["settings"][0]["settings"] == {
        "background": "#0B0E14", "foreground": "#E8E6DD",
        "caret": "#E6B450", "selection": "#303030",
    }, "wrong base palette"
    colors = set()
    for entry in theme["settings"]:
        for key, value in entry["settings"].items():
            if key != "fontStyle":
                assert value in PALETTE, f"unsupported Ayu color: {value}"
                colors.add(value)
    assert {"#CDA1FA", "#D2A6FF"} <= colors, "missing lilac accents"
    print("PASS: Ayu plist theme and palette")


def check_skills() -> None:
    for name in ("feature", "retro"):
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text()
        sections = text.split("---", 2)
        assert text.startswith("---\n") and len(sections) == 3, f"{path}: no frontmatter"
        frontmatter = sections[1]
        assert re.search(rf"^name: {re.escape(name)}$", frontmatter, re.M), f"{path}: wrong name"
        assert re.search(r"^description: \S.+$", frontmatter, re.M), f"{path}: no description"
        for target in re.findall(r"\]\(([^)]+)\)", sections[2]):
            assert (path.parent / target).resolve().is_file(), f"{path}: missing {target}"
    assert (ROOT.parent / "claude/skills/feature/plan_edits.py").is_file()
    assert (ROOT / "agents/plan-reviewer.toml").is_file()
    print("PASS: adapter frontmatter and shared resources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", type=Path, help="explicit path to the Go reviewer TOML")
    parser.add_argument("--harness", action="store_true", help="validate only project harness assets")
    args = parser.parse_args()
    if args.harness:
        check_harness()
        raise SystemExit(0)
    if args.reviewer is not None:
        check_reviewer(args.reviewer)
    check_agents()
    check_guidance()
    check_project()
    check_theme()
    check_skills()
    check_harness()
