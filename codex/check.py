"""Validate repository Codex assets without loading personal configuration."""

from pathlib import Path
import plistlib
import re
import tomllib


ROOT = Path(__file__).resolve().parent
ROLES = (
    ("implementer", "gpt-6.1-sol", "max"),
    ("plan-reviewer", "gpt-6.1-sol", "max"),
    ("acceptance-validator", "gpt-6-astra", "xhigh"),
    ("skill-dry-run", "gpt-6-astra", "high"),
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
    check_agents()
    check_guidance()
    check_theme()
    check_skills()
