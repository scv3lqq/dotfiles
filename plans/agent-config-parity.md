# Agent Configuration Parity

## Goal

Finish the verified gaps after the initial migration: canonical neutral guidance,
explicitly approved role models, and 37 missing plugin skills with their resources.
Use the requested `migrate-to-codex` skill for diagnostics and isolated conversion;
reconcile its output with existing reviewed adapters instead of replacing live
configuration wholesale. Base: `034acd6`; branch: `feat/agent-config-parity`.

## Current behavior and evidence

Root `AGENTS.md` is a symlink to a product-specific regular instruction file.
Four native roles load but inherit the parent model. The active skill inventory
has 37 missing plugin skills, despite all personal/project names being present.
Native CLI 0.166.0 probes confirm the adapters and repeated local plugin installs.
The checkout guard passed before branch creation. Untracked `.agents/` belongs
to existing user work and must remain unchanged and uncommitted.

Official references, refreshed 2026-10-31:

- [Native agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Hooks](https://learn.chatgpt.com/docs/hooks)
- [Plugin format](https://developers.openai.com/plugins/build/plugins)
- [Skills](https://learn.chatgpt.com/docs/build-skills)

## Shared definitions

- Models: implementer and plan-reviewer use `gpt-6.1-sol` / `max`;
  acceptance-validator uses `gpt-6-astra` / `xhigh`; skill-dry-run uses
  `gpt-6-astra` / `high`. The user's main model and all other role settings stay.
- Canonical instructions: root regular `AGENTS.md`, root `CLAUDE.md` symlink
  with relative target `AGENTS.md`. Both root and `codex/AGENTS.md` contain no
  case-insensitive matches for `claude|codex|anthropic|openai|opus|sonnet`.
  Root instructions remain under 200 lines. Client details belong in README
  and the runtime skill adapter.
- Neutral guard alias: `bin/wait-free-checkout.sh` is a symlink to
  `../.claude/bin/wait-free-checkout.sh`; do not change the existing guard.
- Prose specifications: sibling `agent-config-parity-{root,global,feature,readme}.md`.
  Apply/check using `python3 claude/skills/feature/plan_edits.py` and base `034acd6`.
  For root prose, apply to regular `CLAUDE.md` first, then reverse the link.
  The final check still names `CLAUDE.md`, whose symlink reads the canonical body.
- Plugin selection (all must be enabled, with exactly one user-scope record):

| Registry ID | Native name | Skill count |
| --- | --- | --- |
| `data@claude-plugins-official` | `astronomer-data` | 34 |
| `0bull@anthropic-plugin-directory` | `0bull` | 1 |
| `frontend-design@anthropic-plugin-directory` | `frontend-design` | 1 |
| `humanizer-blader@anthropic-plugin-directory` | `humanizer` | 1 |

- Source: home-relative `.claude/plugins/installed_plugins.json` v2, and
  `.claude/settings.json` `enabledPlugins`. Do not guess duplicate precedence.
  Each source `installPath` must be an existing directory with a manifest
  `.claude-plugin/plugin.json` whose `name` equals the native name above.
- Destination: home-relative `.codex/plugin-sources/claude-parity`, containing
  `plugins/<native name>` complete copies and `.agents/plugins/marketplace.json`.
  Marketplace shape is `{"name":"claude-parity","plugins":[...]}`. Each entry
  has `name`, `source: {"source":"local","path":"./plugins/<name>"}`,
  `policy: {"installation":"AVAILABLE","authentication":"ON_USE"}`, and
  `category: "Productivity"`, in the table order. No third-party content is committed.
- Preserve every package file, license, script and internal relative symlink.
  Reject broken symlinks, absolute symlinks and symlinks resolving outside the
  source package before mutations. The observed Data symlinks are internal.
- Data adapter: `.codex-plugin/plugin.json` contains name, source version,
  skills `./skills/`, hooks `./hooks/hooks.json`; that hook file wraps the source
  manifest's `hooks` in `{"hooks": ...}`. Preserve commands byte for byte.
- Humanizer adapter: copy root `SKILL.md` byte for byte into
  `skills/humanizer/SKILL.md`; native manifest contains name, source version and
  skills `./skills/`. The other two packages use their existing manifests.
- Helper is preparation only; native CLI registration/install is an explicit
  subsequent step. CLI repeat `marketplace add` and `plugin add` update local
  source/cache idempotently, confirmed in an isolated no-network probe.

## Acceptance criteria

1. `python3 -B codex/check.py` proves all role models, efforts, instruction file
   types, neutral bodies, length, guard alias and original theme/skill checks.
   Baseline: old checks pass but all new properties fail before implementation.
2. All four prose helper checks pass byte for byte. Baseline: all four fail,
   as the requested text is new.
3. `python3 -B -m unittest discover -s codex -p 'test_plugins.py'` proves preview,
   complete resources, adapters, preservation and recovery. Baseline: file absent.
4. Real native `plugin/read` and `skills/list(forceReload=true)` prove all 37
   expected names enabled with no load errors; Data has SessionStart/Stop hooks,
   and 0bull exposes its MCP definition. Baseline: 37 missing.
5. Native startup/config role discovery loads all four approved definitions;
   the primary model, approval policy and sandbox configuration are preserved.
   Do not claim end-to-end model execution from discovery alone.
6. Requested migration scan/plan/doctor/dry-run and target validation run in
   private scratch; real conversion runs only against a prepared isolated target.
   Its actionable items for this scope are resolved or documented precisely.
   Never overwrite managed live links with the converter's older defaults.
7. `just check` passes before every commit. No private input/report, credentials,
   machine path, unrelated `.agents` work or third-party source is staged.
8. Independent per-task review and final acceptance complete, then fast-forward
   main and push under the repository workflow. No CI is configured at base.

## Gates

`just check` (shell syntax, all isolated Python tests, assets).
New helper checks: `uvx ruff check codex/plugins.py codex/test_plugins.py` and
`uvx mypy --strict codex/plugins.py`.

## Tasks

### T1: Native instructions and role models

Own root `AGENTS.md`, `CLAUDE.md`, `bin/wait-free-checkout.sh`, `codex/AGENTS.md`,
the four `codex/agents/*.toml`, `codex/skills/feature/SKILL.md`, `codex/check.py`.
No dependencies. Apply the three exact prose plans; reverse the root symlink
only after applying root prose. Add model keys matching Shared definitions;
preserve every other TOML field and role body. Create only the neutral guard link.
Extend `check_agents` to verify the table, and add `check_guidance` invoked by main
for the file types/relative links, identical root reads, neutral text and length.
Keep the existing palette/frontmatter/resource checks. Use assertion messages
that name the violated property. No behavioral change to guard or setup helper.
Scoped gates: `python3 -B codex/check.py`, three prose helper checks, and
`/bin/bash -n bin/wait-free-checkout.sh`. No full suite. Done when those pass.

### T2: Prepare complete local plugin packages

Own `codex/plugins.py` and `codex/test_plugins.py`. No dependency on T1.
Use Python 3.11 standard library to match the existing setup helper. Public API:
`prepare_marketplace(home: Path, *, apply: bool = False) -> Path`; returns the
destination path. CLI accepts `--home` and `--apply`, default is read-only preview.
CLI prints `Preview: <path>` or `Ready: <path>`; validation/I/O errors print
`ERROR: <reason>` to stderr and exit 1. Never print configuration or hook bodies.

Read and validate all four packages before creating anything. Validate exact
skill counts from `skills/*/SKILL.md` (Humanizer root is its one skill), original
MCP JSON when present, Data hooks object, source manifest names and versions.
Malformed/disabled/missing/ambiguous sources fail before mutations. Copies use
internal symlinks as symlinks. Reject non-regular files and external links.
Source configs and packages are never changed. Do not run hooks or external CLIs.

Ownership marker `.codex-parity.json` has `schema: 1`, `source_sha256` and
`content_sha256`. Hash deterministic relative paths plus file bytes or link target,
excluding only this root marker from destination content hashing. Include source
versions/registry IDs in the source digest; do not persist personal source paths.
An existing destination without a valid marker or with content drift is a conflict
and fails without overwrite. If source and content hashes match, leave all files
unchanged. A valid managed snapshot with changed source is backed up by rename to
`.claude/backups/codex-plugins-<UTC timestamp>/claude-parity` before replacement.
Build a complete snapshot in a private temporary directory before the rename;
use a same-filesystem atomic rename, restore the old snapshot if replacement fails,
and remove only this invocation's temporary directory. Backups and preparation
directories use mode 0700. Existing unrelated config/cache paths are untouched.

Write meaningful tests first, then source. Fixture cases with literal expectations:
preview makes zero writes; apply yields four marketplace entries and 37 skills;
Data hook commands preserved exactly; Humanizer body preserved exactly; MCP,
license and nested resource preserved; internal symlinks preserved; repeat apply
leaves destination bytes and mtimes unchanged; changed source produces a backup
with old bytes; edited destination and unmanaged destination are refused; disabled,
duplicate user records, missing source/manifest, invalid JSON, wrong skill count,
and escaping/broken links fail without target creation; simulated replacement
failure restores the previous snapshot. Global config bytes remain unchanged.
Named reviewer mutations: remove conflict/content-drift guard (conflict test fails),
omit Data hooks export (hook test fails), and skip restoration after failed rename
(rollback test fails). Run each on a separate scratch copy, never this checkout.
Mutation command: `python3 -B -m unittest discover -s codex -p 'test_plugins.py'`.
Scoped gates: that test command plus the two new-helper lint/type commands in Gates.
Done when tests and gates pass. No full suite.

### T3: Document and apply the completed migration

Depends on committed T1 and T2. Own `README.md` exact prose plan only. Main agent
owns private migration snapshots and live installation, not repository source edits.
Run helper preview, apply, repeat apply; register marketplace then all four plugins
using the documented CLI commands. Back up live config/registry bytes before CLI
mutation, compare unrelated semantic fields afterward, and retain private backups.
Use native RPC assertions for all 37 names and metadata; do not auto-trust hooks
or manufacture OAuth credentials. Record remaining genuine external prerequisites.
Apply/check README exact prose. Scoped gate: its prose check. No full suite.

## Seams

| Producer | Consumer | Shared contract |
| --- | --- | --- |
| T1 | T3 | Approved model table, canonical instruction/link direction |
| T2 | T3 | Destination, marketplace/name IDs, preview/apply interface |
| T1 and T2 | Native verification | CLI reads existing links plus installed packages |

## Edge cases

Respect macOS/Linux link behavior, Python 3.11 minimum and absent source plugins.
Preview never installs dependencies. Missing CLI or external OAuth/tool dependencies
are reported honestly; skill visibility is not external workflow validation.
Only planned files are staged; existing untracked project skills remain untouched.
Source upgrades are explicit snapshot updates; local edits are never overwritten.
No full installer, shell switch, package manager or broad cleanup is run.

## Not doing

No changes to the main model, permissions, auth, unrelated MCP, source plugins,
canonical source skill paths, themes already verified, histories or transcripts.
No project-local `.codex` duplicate of globally managed assets. No whole-app GUI
automation where access was denied. Do not claim lifecycle-hook or external-service
parity from static conversion; report remaining unsupported/untested behavior.

## Baseline

Before implementation, the repository `just check` passed (15 isolated tests).
All four exact prose checks were run on base and failed as expected; planned
root/global bodies are neutral and 195/91 lines. New property checks are expected
to fail on base; the plugin test file and helper do not exist. The read-only native plugin probes establish the expected
adapter counts and repeat-install behavior without user configuration changes.

## Migration diagnostic findings

The requested migrator was run against isolated user/project targets. Both actual
staged conversions, target validators and repeat dry-runs completed. Global default
planning hits a missing source frontmatter name; narrow component planning succeeds.
The global target validator scans the whole home and was bounded by a timeout;
focused validation and native strict startup both pass. Its validator does not prove
model or hook compatibility. No additional MCP names are missing.

A fixture confirms that live merge can write through skill directory symlinks into
source files. Generated config replaces unrelated settings, and generated roles use
old model defaults or unsupported aliases. These artifacts will not replace the
existing managed setup. Source files remain unchanged. No private reports are stored
in git. This is why the requested skill is used for diagnostics/staging and checked
changes are applied through repository-owned helpers.

## Implementation results

T1 and T2 independent reviews passed. The three required mutations each failed
the intended test on isolated archived copies. The full gate passed 43 tests.
Helper preview, apply and repeated apply succeeded against the selected sources.
Native installation succeeded for the local marketplace and all four plugins.
Native RPC loaded all 37 exact expected skill names with zero errors, Data's
SessionStart/Stop hooks and the 0bull MCP definition. Only the selected marketplace
and plugin registrations changed in config; existing global hooks were byte-identical.
Role discovery loaded the four approved definitions; no model request was needed.
Hook execution, OAuth-dependent iPhone actions and external Data services were not
claimed as tested. Hook trust and service authentication remain runtime actions.
