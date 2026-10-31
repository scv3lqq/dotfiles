# Sol high agent configuration

## Goal and current behavior

The project selects Astra/max. Four shared roles mix Sol/max and Astra/high or
xhigh. The global main model already selects Sol/high; the third-party Go
reviewer has no model override and inherits it.

## Shared definitions

Every configured project model and shared role must use `gpt-6.1-sol` and
`model_reasoning_effort = "high"`. Preserve agent instructions and symlinks.
Base: `64a72f9d6fd3e67d4ed42e3a8b7a951225225204`.

## Acceptance criteria and Gates

- `python3 -B codex/check.py` verifies all four roles and the project config.
- `just check` passes the complete repository checks.
- `git diff --check` passes.
- Parse installed agent TOML files: each explicit model/effort override must
  match the shared definitions; missing overrides inherit the global Sol/high.
- README model table and project description match the configured values.

## T1: align model settings and checks

Ownership: `codex/agents/implementer.toml`, `codex/agents/plan-reviewer.toml`,
`codex/agents/acceptance-validator.toml`, `codex/agents/skill-dry-run.toml`,
`.codex/config.toml`, `codex/check.py`, `README.md`.

First change the existing model/effort assertions in `codex/check.py` to the
shared definitions and run `python3 -B codex/check.py`: it must fail on the
old configurations. Then change only model/effort fields in the five TOML files.
Update the README project model sentence and four role-table rows. Preserve
all other behavior, tests, setup policy, role instructions and documentation.
Task gates: `python3 -B codex/check.py` and `git diff --check`.
Done: red/green evidence, exact settings, scoped diff and passing task gates.

## Seams

One task owns all shared settings and their assertions; no cross-task seams.

## Edge cases

- macOS/Linux: no platform-specific behavior changes.
- Missing tools: report a failed gate; do not install packages.
- Dirty worktree: preserve concurrent unrelated changes; baseline was clean.
- First run: shared source files apply through existing installed symlinks.
- Global configuration already matches; do not rewrite it or third-party agents.
- Current session role definitions may be cached: use default agents with an
  explicit supported Sol/high override for this workflow, carrying role duties.

## Not doing

No setup logic, instructions, historical plans, installed third-party files,
model discovery, credentials, or unrelated configuration changes.

## Baseline

`bin/wait-free-checkout.sh`: exit 0, free after two checks.
The pre-change complete check result is recorded in private task evidence.

## README exact edits

Use `python3 claude/skills/feature/plan_edits.py apply plans/sol-high-agents.md README.md 64a72f9d6fd3e67d4ed42e3a8b7a951225225204`, then the same command with `check` as an additional task gate.

**E1.** (lines 170-170)

````md E1-old
its config selects Astra with max reasoning, and its four agent definitions link
````

````md E1-new
its config selects Sol with high reasoning, and its four agent definitions link
````

**E2.** (lines 180-183)

````md E2-old
| `implementer` | `gpt-6.1-sol` | `max` |
| `plan-reviewer` | `gpt-6.1-sol` | `max` |
| `acceptance-validator` | `gpt-6-astra` | `xhigh` |
| `skill-dry-run` | `gpt-6-astra` | `high` |
````

````md E2-new
| `implementer` | `gpt-6.1-sol` | `high` |
| `plan-reviewer` | `gpt-6.1-sol` | `high` |
| `acceptance-validator` | `gpt-6.1-sol` | `high` |
| `skill-dry-run` | `gpt-6.1-sol` | `high` |
````

## Installed settings gate

```bash
python3 - <<'PYCODE'
from pathlib import Path
import tomllib
root = Path.home() / '.codex'
config = tomllib.loads((root / 'config.toml').read_text())
assert config['model'] == 'gpt-6.1-sol'
assert config['model_reasoning_effort'] == 'high'
for path in (root / 'agents').glob('*.toml'):
    agent = tomllib.loads(path.read_text())
    assert agent.get('model', config['model']) == 'gpt-6.1-sol', path.name
    assert agent.get('model_reasoning_effort', config['model_reasoning_effort']) == 'high', path.name
print('PASS: installed agents use Sol/high')
PYCODE
```

README exact-edit check above proves the documented settings. On the base the
installed gate fails for the Astra role; the README exact-edit check fails for
the unchanged prose. The baseline full suite passes.
