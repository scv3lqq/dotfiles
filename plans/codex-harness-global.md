# Global native harness defaults

## Goal and authorization

The user explicitly requested the existing harness as the default in every
directory, not only this dotfiles checkout. Implement this approved scope now;
no additional approval wait for this rollout. Preserve all existing work and
settings except the explicitly requested global Planner/model/agent defaults.
No commit, staging, push, branch change, long test suite, build, linter, typecheck,
benchmark or dependency installation. Native short isolated probes and fast
focused Python stdlib tests remain authorized. No install.sh or broad setup apply.

## Current behavior and evidence

- Codex CLI 0.167.0, native agents and global config are available.
- Project `.codex/config.toml` sets Planner Sol/medium, six harness roles and
  depth 2/capacity 3. Global user config still has Sol/high and four old roles;
  no global developer_instructions or harness skill/roles exist.
- Six roles and skill/protocol assume `codex/...` relative to a target project.
- `codex/setup.py` preserves user config with typed TOML validation/backups;
  normal setup only installs skills enumerated in claude/skills and old roles.
- `state.py` uses Path.cwd() and does not prepare ignore rules in a new project.
- Native precedence: session flags > trusted project config > profile > user
  config. Do not weaken trust or mass-edit unrelated project configs. Existing
  project override inspection found two configs, only our own has a root router
  or model override. Preserve deliberate future overrides and report that limit.
- Sources: https://learn.chatgpt.com/docs/config-file/config-basic and
  https://learn.chatgpt.com/docs/agent-configuration/subagents . Local CLI strict
  validation and actual merged configuration are the acceptance authority.
- A protected original global config backup and a fresh Git/source baseline are
  saved privately before edits. Never print/copy its secret values into logs.

## Shared definitions

### Portable resources and working root

Install the existing skill as the canonical user-scope symlink
`<home>/.agents/skills/harness -> <repo>/codex/skills/harness`.
Add source symlink `codex/skills/harness/scripts/state.py` with exact target
`../../../harness/state.py`; no helper copy and no dependency installation.
Global role registry points at real canonical `<repo>/codex/agents/harness-*.toml`
files; install matching ~/.codex/agents links too using the existing convention.
All roles resolve the user-installed harness skill resource path from their
parent's handoff or the user-scope skill location; never look for codex/... in an
unrelated target project. Read protocol beside installed SKILL.md; invoke the
helper under installed skill/scripts/state.py. User/project skill shadow copies
are not new authority to replace the globally configured workflow.

Add helper global option `--root PATH` before its subcommand. Default working root
is `git rev-parse --show-toplevel` from original cwd when in a Git checkout,
otherwise cwd. Missing Git is allowed and uses cwd; unexpected Git errors stop
clearly without changing trust/safe.directory or permissions. Explicit --root
must name an existing directory. Agents preserve user path meaning relative to
the original launch cwd, then express task-owned paths relative to working root;
use the same chosen root for every lifecycle command. Do not put runtime data
into dotfiles merely because resources are symlinked there.

Add helper `prepare`: only after change-plan approval, safely create target
`.harness/.gitignore` if absent with EXACT content `/runs/\n/staging/\n` and return
a compact result. Preserve an existing ignore file byte-for-byte. In Git, verify
both runtime paths are ignored using read-only `git check-ignore --no-index` on
sentinel paths; on conflict report a blocker, never amend existing rules silently.
In a non-Git folder ignore validation is not required. Refuse ANY symlink on
.harness, .harness/runs and .harness/staging (including internal links), and
foreign non-directory runtime paths or non-file/symlink ignore targets. Match
existing runs_path guards during prepare, before any staging write. Use safe path
guards. `prepare` must not create a run or authorize source edits. Planner calls
it after approval, before staging the approved plan, then Orchestrator init runs.
Never prepare runtime metadata for informational questions.

### Global default activation

Extend existing codex/setup.py with a dedicated `configure_harness(home, *,
apply=False, repo_root=None)` and CLI flag `--global-harness`; this mode configures
ONLY harness, not theme, old guidance, old roles, plugins, permissions or services.
Existing normal configure behavior remains backward-compatible. Document the
one-time provisioning flag; the user does not select a runtime profile or skill.
Running old setup later must not remove the installed harness.

New harness-specific config builder takes original bytes and canonical role
registrations. Set model=gpt-6.1-sol, effort=medium, agents.enabled=true,
agents.max_depth=2, agents.max_concurrent_threads_per_session=3 and existing
Terra/medium child defaults. Register all six harness roles while preserving the
four old roles and all unrelated config. Model/effort are intentional changes.
Read the project router dynamically when configure_harness is invoked, never
embed the old project router while G3 is in progress. G3's portable router must
contain the exact identifying phrase `user-scope harness` and not depend on
target-relative codex/skills resources; G1 validates this before any live write.
Synthetic G1 fixtures supply their own valid portable router. Live apply occurs
only after G3 finishes and review passes. In the user config include the absolute
installed user skill path (derived from home) inside a uniquely delimited managed
developer-instruction block. Preserve preexisting developer instructions outside
the block. Updates replace only that block; repeated apply is idempotent.
No home paths in tracked source; only rendered private global config has them.

Preserve TOML comments/layout/newlines and all unrelated values. Support literal
root and [agents] simple settings as existing builders do; reject ambiguous,
duplicate, inline/dotted or unsupported multiline layouts before any writes.
Do not silently lose arbitrary user instructions or legacy alias settings: handle
them deliberately or fail before changes with a clear error. Compare full parsed
candidate TOML to original plus the exact allowed semantic changes.

Preflight every required source, role description, destination and registry.
Existing correct links are reused; foreign required destination or role registry
conflicts fail before any write. Back up changed global config in existing private
backup convention, preserve resolved target and file mode, never print config.
Create mandatory links first, verify them, then activate global config atomically
as the final step with an original-byte drift check immediately before replacement.
This detects observed concurrent changes, not an atomic compare-and-swap against
uncooperative writers; preserve a private backup and acknowledge the residual
check/rename window. Apply without intentional concurrent config editing.
On failure remove only
links created by this invocation; never replace/delete user-owned files. Preserve
concurrent config changes detected up to the final byte check; abort on observed
drift rather than overwriting it. The residual race described above remains.
A successful
second apply makes no changes or backup. Preview writes nothing.

### Behavior and priority

Keep the previous routing, approval, independent review, max-three-wave,
state integrity, compact-parent context and retrospective/proposal guardrails.
Global Planner follows project coding/architecture rules but does not let a
lower-priority feature/auto-implementation instruction bypass harness intent or
approval phases. Explicit user commands and native higher-priority project
developer/model settings retain their documented priority. Do not add a shell
wrapper, daemon or controller, weaken permissions or promise universal override
of explicitly conflicting local configuration or automatic session restart.

## Tasks and exclusive ownership

### G1: safe global installer

Implementer owns ONLY codex/setup.py and new codex/test_harness_setup.py.
Add dedicated builder/configure_harness/CLI mode per shared definitions; reuse
existing registry, backup and atomic-write utilities where suitable. Do not run
normal configure/apply or change old fixtures just to bypass behavior coverage.
Test first: isolated fake home/source with complete harness role/skill fixtures;
preview/no-secret-output; allowed-settings-only preservation; mode/newlines/
comments; idempotence; preserving other developer text; source missing; foreign
destinations/registries; link failure before activation; concurrent config drift;
rollback owned links; symlinked config canonical target; CLI flag dispatch.
Run RED and save it before implementation, then GREEN.
Gate: python3 -B -m unittest discover -s codex -p test_harness_setup.py.
Static AST check only, no linter/typecheck. Do not live-apply until reviewed.

### G2: working-root and metadata preparation

Implementer owns ONLY codex/harness/state.py, codex/harness/test_state.py and
codex/skills/harness/scripts/state.py symlink. Implement --root/default root and
prepare per shared definitions, preserving existing state format/transitions and
compact output. New command returns working_root, ignore_created and ignored
status; no unrelated file scan or run creation. Use Python stdlib subprocess for
read-only Git queries. Fast tests first: nested Git cwd, plain non-Git cwd, explicit
root, missing Git, escaping/foreign .harness/ignore, fresh prepare, preserving
existing ignore byte-for-byte, conflicting negation/ignore rules fail safely,
no run created and original lifecycle regression suite. Scratch Git init is
permitted in tests only, no commits or target repo mutations.
Gate: python3 -B -m unittest discover -s codex/harness -p test_state.py.
Do not change report schema, state transitions or model logic.

### G3: portable workflow instructions and static integration

Implementer owns ONLY .codex/config.toml, six codex/agents/harness-*.toml,
codex/skills/harness/SKILL.md, codex/skills/harness/references/protocol.md,
codex/check.py, .harness/README.md, README.md. Preserve existing content/changes.
Update all resource references and commands to installed user-scope skill and
portable helper, root policy and post-approval prepare; root routing retains all
previous acceptance/intent/context constraints. Make global and project routers
consistent without hardcoded private paths. Clarify native project precedence
and new sessions (existing sessions do not retroactively reload all instructions).
Document --global-harness provisioning and normal everyday codex usage. Adapt
scoped checker to portable resources/new helper symlink without broad checks.
Do not edit global/project AGENTS, old skills/roles, install.sh or shell wrappers.
Gate: python3 -B codex/check.py --harness; AST/TOML/link parses and scoped diff check.

### G4: safe activation and native acceptance

Root owns live apply of reviewed --global-harness mode, protected private backups,
scratch probes and user-facing outputs. Use the previously reviewed filtered
native app-server probe client, extending it in separately reviewed scratch scope
only if needed for actual global config mode (no fixture overlay or profile).
Before model calls require effective global Planner/Solmedium, six role paths and
enabled user-scope harness skill. Never log raw config/MCP env or credentials.
Use two isolated targets outside dotfiles: a plain directory and a new scratch
Git repository, plus a nested cwd read-only check. Ordinary queries use only
global settings; no copied project .codex config, role definitions or local skills.
Inspect real merged config and discovered skill first, then bounded native live
information/approval/implementation probes. Include project AGENTS requesting
feature/immediate implementation to verify global developer routing wins that
lower-priority workflow, while preserving coding constraints and no test runs.
One small approved byte change should reach durable completed with portable helper,
independent ACCEPT/PASS and retrospective, with no source in target codex/ directory.
Prove no source edits/metadata before approval, no agents for simple information,
Explorer for complex research and current global real models through native events.
Recheck intentional project override as a documented limit; never modify that
project's config to force behavior. Do not perform a broad host-wide rollout.
Save post-install intended global config hash privately. Native tests can create
task-specific trust entries; after all probe processes stop remove ONLY those
exact task-owned entries and prove the resulting config equals the post-install
intended hash, not the pre-install hash (which would erase authorized defaults).
Preserve all Git refs/index/unrelated work. Refresh the user-facing diff/evidence
artifacts so they include global rollout source changes, no runtime reports/secrets.

## Acceptance criteria

### G4 private probe-client contract

Extend only existing chat-workspace work/probe_runner.py with --installed-global,
mutually exclusive with --fixture-config and permitted for isolated scenarios
under that work directory. Keep old modes and secret filtering intact. This mode
passes NO model, developer, agent, profile or project-trust override to Codex;
only existing optional hooks/apps/plugins/MCP process isolation remains. Before
inference validate effective root Sol/medium, developer text equals selected
fields from the actual current user config and contains portable Planner routing,
required depth/capacity, six canonical real-source role registrations, and enabled
USER-scope harness skill pointing at installed ~/.agents/skills/harness/SKILL.md.
Validate selected canonical role files/pins against reviewed source as before.
Model-test target must have no copied .codex config, role files or local harness
skill; no shadowing resource injection. A negative local project override test
is inspect-only or must fail before inference. Record installed_global=true in
evidence, fixture_config_overlay=false. Do not persist raw global config/env/keys,
modify permissions/trust settings, or read/copy authentication files. Native
thread sandbox remains the existing restricted test condition. Root will remove
only native-added task-specific trust rows after processes finish and compare
against the intended POST-install global config hash. No inference until the
extended client is independently reviewed. AST/sentinel/inspect-only checks are
allowed before that review, not model turns.

1. Global config has requested root defaults, old settings/roles/permissions remain,
   user-scope resources are discoverable and correct, repeat apply is no-op.
2. Fresh native config/prompt from non-dotfiles plain/Git/nested directories resolves
   Planner and six roles without project copies, overlay or manual skill selection.
3. Informational and unapproved change requests have no source/metadata writes;
   complex research uses short-lived Explorer and compact handoffs.
4. Approved change in a foreign project uses the shared installed helper, correct
   working root, safe ignore preparation, real nested agents, review/validation and
   automatic retrospective, and produces completed state.
5. Focused new installer and helper tests pass; static CLI config parses. No slow
   suites/builds/lints/typechecks/benchmarks or dependency installation were run.
6. Independent workflow dry-run, source reviewer and acceptance validator bind
   verdicts to current hashes. Global change is authorized and preserved; unrelated
   config, trust entries, Git state and existing work are not overwritten.

## Gates and seams

Only G1/G2 focused tests, G3 scoped static checks and G4 bounded live probes.
Never just check or full project tests. Installer-owned live links depend on G2's
script symlink and G3's role/skill references; live apply follows both and review.
G1 canonical router comes from G3 project config. G3 commands must match G2 exact
option/command syntax. Parent paths remain concise; detailed reports stay with
specialists. Parallel writers have disjoint file sets and preserve each other.

## Edge cases and exclusions

Existing custom developer instructions/local project overrides are preserved,
and their actual priority is reported. Conflicting mandatory resources stop safely.
Read-only or arbitrary non-Git directories remain useful for information; no
artifact writes until change approval. Nested source paths retain original-cwd
meaning. No mass rewriting private repositories, global AGENTS or skills. No
external controller/auto restart, credential generation, dependency installs,
permissions weakening, commit, push or history changes. Public source has no
private user paths, hosts, credential values or transcript excerpts.
