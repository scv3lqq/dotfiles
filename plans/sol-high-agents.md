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
