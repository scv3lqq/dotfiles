# Codex subagent model defaults

## Goal
Use gpt-6.1-terra / medium for every non-reviewer child. Keep the main session's
actual settings and the global/project top-level model and effort unchanged.
Pin plan-reviewer and go-code-reviewer to gpt-6.1-sol / high.

## Current behavior
Project and global main config select gpt-6.1-sol / high. Four shared workflow
roles pin Sol/high. The global Go reviewer has no model/effort pins; built-in
children have no configured subagent defaults. Global config is a regular private
file; four installed role symlinks resolve to codex/agents. The active session has
already loaded the old role definitions; saved edits cannot attest a live reload.

## Sources
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- Local codex-cli 0.167.0 strict startup parser accepts agents.default_subagent_model
  and agents.default_subagent_reasoning_effort. Role pins override defaults.

## Acceptance criteria
1. Parse TOML and compare role/default settings with the role matrix below.
2. Compare global parsed config before/after, excluding only the two [agents]
   default keys, and preserve top-level main model/effort and all other settings.
3. Existing global Go reviewer bytes change only by insertion of explicit model
   and effort. Back it and global config up under the existing private convention.
4. Fresh CLI process spawns all eight child roles without model/effort overrides;
   inspect actual child turn_context metadata for the effective matrix. Record
   unavailable fields or runtime limitations honestly; self-report is insufficient.
5. just check passes, plus strict CLI startup config validation.
6. Existing Excalidraw orchestration drawing is updated and visually checked.
7. Scoped commits are reviewed, integrated and pushed per repository rules.

## Shared definitions
| Role | Model | Effort |
| --- | --- | --- |
| main (preserved saved defaults) | gpt-6.1-sol | high |
| default, worker, explorer | gpt-6.1-terra | medium |
| implementer, acceptance-validator, skill-dry-run | gpt-6.1-terra | medium |
| plan-reviewer, go-code-reviewer | gpt-6.1-sol | high |

Use supported [agents] default_subagent_model and
 default_subagent_reasoning_effort, never change top-level model fields.
Do not add built-in role files. Preserve role instructions.

## Constraints and edge cases
macOS/Linux setup behavior must remain equivalent. Preserve first-run behavior,
preview safety, private backups, permissions, comments, CRLF, symlinks and apply
idempotence. Fail closed on unsupported ambiguous TOML before writes. No secrets,
private URLs, personal identities or home paths in public artifacts. Do not run
install.sh. Unrelated dirty work belongs to another active feature and must remain
untouched; branch acquisition requires the existing checkout guard and clean main.
Missing tools or unavailable runtime metadata must be reported, not faked.

## Tasks
T1: setup behavioral change with tests first. Own codex/setup.py and
codex/test_setup.py. Add a pure subagent_config(original: bytes) -> bytes transform
that sets exactly the two supported [agents] defaults and preserves other parsed
settings. Integrate it after theme_config in configure. Keep existing theme_config
contract intact. Support literal [agents] tables, missing tables, quoted keys,
comments, CRLF; reject inline/dotted/ambiguous tables before mutations. Preserve
existing unrelated role files, including Go reviewer. Tests add main effort,
other agent settings, idempotence, preview, backup, symlink and invalid-input cases.
Write tests, capture RED, then implement. Mutation: remove subagent_config call
from configure; targeted new expectations must fail while syntax still parses.
Task gates: python3 -B -m unittest discover -s codex -p test_setup.py.

T2: mechanical role/config/check updates. Own codex/agents/implementer.toml,
codex/agents/acceptance-validator.toml, codex/agents/skill-dry-run.toml,
.codex/config.toml, codex/check.py, codex/test_check.py. Change only model+effort in these three roles;
keep plan-reviewer untouched. Add [agents] defaults to project config, preserve
its two existing top-level fields. Extend structural checks for expected defaults
and role pins without weakening other existing checks. The private Go reviewer
gets explicit pins in its existing canonical file after backup; it remains
user-owned (setup must not replace its instructions). Add optional --reviewer PATH to codex/check.py; when supplied, validate that
TOML name is go-code-reviewer and both explicit pins are Sol/high. No personal
config is read by default. Write synthetic tests first for valid, absent and wrong
pins. Named mutation: omit effort validation; tests must fail. Task gates:
python3 -B codex/check.py and python3 -B -m unittest discover -s codex -p test_check.py.

T3: README documentation. Own only affected README.md Codex section. Explain role
matrix, two subagent defaults, unchanged main fields, setup behavior, explicit
Go reviewer pins, and restart/fresh-process requirement. Use exact plan_edits.py
old/new fences generated from the branch base before dispatch, never retype old
text. Gate: plan_edits.py check against base plus git diff --check.

V1: runtime verification only, not implementation. Use a separate private scratch
probe-plan.md containing a minimal read-only V1 task with a harmless Python print
gate and acceptance criterion; no production files. A fresh probe parent spawns
eight roles in waves <=3, fork_turns none, no explicit model/effort overrides.
Allow each role's mandatory safe reads, gates and report format. Await completion;
inspect actual persisted child turn_context model/effort rather than response text.
No production writes; launch CLI with read-only sandbox and no main model override.

T4: reviewed private probe helper and diagram refresh. Own only task scratch and
the existing orchestration drawing selected by exact ID after summary read.
Before helper execution, independent review checks CLI/API and metadata contracts.
Update existing labels, preserve topology. Non-reviewers Terra/medium, reviewers
Sol/high, main unchanged; distinguish saved config from already-loaded session.
Read back and render actual saved drawing; validate geometry, inspect the PNG.
Archive before/after snapshots privately; no private IDs or hosts in public plan.

## Seams
T1 -> T2: shared [agents] key names and matrix above.
T1/T2 -> T3: documented setup defaults and role pins above.
T1/T2 -> V1/T4: saved config is input, turn_context is runtime evidence.

## Gates
- just check
- codex app-server --strict-config --print-startup-config (save output privately)
- git diff --check
- V1 fresh-runtime evidence matrix and before/after private preservation assertions
- Excalidraw readback, validate and screenshot inspection

## Not doing
No main-session model switch, role instruction rewrite, unrelated feature commits,
permission changes, credential changes, installer execution or history rewriting.

## Baseline evidence
Base commit: 5a7cc328188f1d37737988bb56dc6b5ad265c5e6.
Initial just check passed (83 tests plus four plan-edit tests), recorded privately.
Strict startup validation passed before changes. The user authorized a named stash for unrelated work and restoration afterwards.
The checkout guard passed on clean main; task branch is feat/codex-terra-subagents.
Keep the stash until restored and byte-verified after finishing the task.

## Dry-run findings integrated
Remove forced PROBE_OK/no-tools contract, enforce external reviewer pins through
an optional checker with synthetic negative tests, and fix setup preview wording.
Native custom-role spawn was unavailable in this loaded session; use approved
model/effort and the full canonical role instructions with an available default
agent, fork_turns none. This is a workflow fallback, not runtime config evidence.

## README exact edits (T3)

**E1.** (lines 169-193)

````md E1-old
`CLAUDE.md` links to it. The tracked `.codex/` is this repository's project layer:
its config selects Sol with high reasoning, and its four agent definitions link
to the shared sources in `codex/agents/`. Project settings load for trusted projects.
The tracked `.agents/skills/` links the three project skills and their resources
to `.claude/skills/`, plus the native `feature` and `retro` workflows from
`codex/skills/`. The `codex/` directory remains the source for global setup.

Codex shares 23 personal skills and has four native roles:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| `implementer` | `gpt-6.1-sol` | `high` |
| `plan-reviewer` | `gpt-6.1-sol` | `high` |
| `acceptance-validator` | `gpt-6.1-sol` | `high` |
| `skill-dry-run` | `gpt-6.1-sol` | `high` |

The global setup preserves the current main model. The `feature` and `retro`
skills have Codex adapters;
existing third-party skills and the Go reviewer are preserved.
The installer configures these assets when Python 3.11+ is available.
Preview with `python3 codex/setup.py`; apply with `python3 codex/setup.py --apply`.
This links guidance and agents into `~/.codex/`, personal skills into
`~/.agents/skills/`, and the Ayu syntax theme into `~/.codex/themes/`.
Only `tui.theme` is changed in the global config. Conflicting files are reported;
replaced guidance and configuration are backed up privately outside the repo.
````

````md E1-new
`CLAUDE.md` links to it. The tracked `.codex/` is this repository's project layer:
its top-level settings keep the main session on Sol/high, and its four agent
links share sources in `codex/agents/`. Project settings load for trusted projects.
The tracked `.agents/skills/` links the three project skills and their resources
to `.claude/skills/`, plus the native `feature` and `retro` workflows from
`codex/skills/`. The `codex/` directory remains the source for global setup.

Codex shares 23 personal skills. The saved role policy is:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| Main session (existing global/project settings preserved) | `gpt-6.1-sol` | `high` |
| `default`, `worker`, `explorer` | `gpt-6.1-terra` | `medium` |
| `implementer`, `acceptance-validator`, `skill-dry-run` | `gpt-6.1-terra` | `medium` |
| `plan-reviewer`, `go-code-reviewer` | `gpt-6.1-sol` | `high` |

The supported `[agents]` keys `default_subagent_model` and
`default_subagent_reasoning_effort` set Terra/medium for built-in children.
Explicit custom-role model/effort pins take precedence over these defaults.
The four managed roles pin both fields. The existing user-owned Go reviewer
must explicitly pin `model = "gpt-6.1-sol"` and `model_reasoning_effort = "high"`;
setup preserves its file and instructions. Validate its resolved TOML with
`python3 codex/check.py --reviewer <path-to-go-reviewer.toml>`.

The global setup preserves the main model/effort and all unrelated settings.
The `feature` and `retro` skills have Codex adapters; existing third-party skills
are preserved. The installer configures these assets with Python 3.11+.
Preview with `python3 codex/setup.py`; apply with `python3 codex/setup.py --apply`.
This links guidance, managed agents, personal skills and the Ayu syntax theme.
Global config changes are limited to `tui.theme` and the two subagent defaults.
Conflicting files are reported; replaced guidance and configuration are backed
up privately outside the repo. Restart Codex to load saved defaults and role
pins: an already-running session can retain its loaded settings. Verify actual
child selection in fresh subagents, rather than inferring it from saved files.
````

## T4 private helper contract
The implementer writes runtime_probe.py under task scratch, never live config.
It launches codex exec --strict-config --json --sandbox read-only -C <repo> with
no model/config/profile overrides. Parent prompt spawns exact eight roles, waves
<=3, fork_turns none and V1 scratch plan. Capture stdout/stderr privately and
parse root thread.started.thread_id. Find child session_meta whose source.subagent
.thread_spawn.parent_thread_id matches root; role from agent_role. Use their own
turn_context.payload.model and .effort. Require eight unique roles and expected
matrix, root Sol/high, completed root process and no config hash drift. Save a
compact JSON evidence report, no full config text. Fixture tests cover malformed
JSON, missing/duplicate roles, wrong effort and mismatched parent IDs. Scoped
gates: compile helper and run synthetic parser fixtures. Independent reviewer
checks exact helper hash before live execution. Existing session role-availability
rejection must not be interpreted as fresh CLI capability evidence.
