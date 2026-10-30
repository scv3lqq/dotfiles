"""Validate repository Codex assets without loading personal configuration."""

from pathlib import Path
import plistlib
import re
import tomllib


ROOT = Path(__file__).resolve().parent
ROLES = (
    ("implementer", "max"),
    ("plan-reviewer", "max"),
    ("acceptance-validator", "xhigh"),
    ("skill-dry-run", "high"),
)
PALETTE = frozenset({
    "#0B0E14", "#E8E6DD", "#CDA1FA", "#D2A6FF", "#303030", "#E6B450",
    "#11151C", "#EA6C73", "#7FD962", "#F9AF4F", "#53BDFA", "#90E1C6",
    "#C7C7C7", "#686868", "#F07178", "#AAD94C", "#FFB454", "#59C2FF",
    "#95E6CB", "#FFFFFF",
})


def check_agents() -> None:
    for name, effort in ROLES:
        path = ROOT / "agents" / f"{name}.toml"
        agent = tomllib.loads(path.read_text())
        assert agent.get("name") == name, f"{path}: wrong agent name"
        for field in ("description", "developer_instructions"):
            value = agent.get(field)
            assert isinstance(value, str) and value.strip(), f"{path}: missing {field}"
        assert agent.get("model_reasoning_effort") == effort, f"{path}: wrong effort"
        assert "model" not in agent, f"{path}: model must be inherited"
    print("PASS: four native agents and inherited models")


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
    check_theme()
    check_skills()
