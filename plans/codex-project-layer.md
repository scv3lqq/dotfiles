# Codex Project Layer

## Goal and current behavior

Add the requested tracked project `.codex/` and make this repository's native
agents and three project skills available from a fresh clone. Base `6e44010`,
branch `feat/codex-project-layer`. Global assets already live in `codex/`; the
project layer is absent. Existing untracked `.agents/` contains three skill copies.
Two have mechanical product-name substitutions pointing to nonexistent paths;
the other skill and all six resources match the tracked sources exactly.

## Evidence and shared definitions

- Native Codex 0.166.0 isolated probes confirm project model/effort loading,
  relative agent links, project precedence over same-name global roles, and
  discovery of all three project skill links with `scope=repo`, enabled, no errors.
  An untrusted project layer is disabled; this checkout is already trusted.
- [Agent documentation](https://developers.openai.com/codex/subagents) and the
  [configuration schema](https://developers.openai.com/codex/config-schema.json)
  support the native layout. No custom discovery option is needed.
- `.codex/config.toml` is a regular file containing only these exact settings:
  `model = "gpt-6-astra"` and `model_reasoning_effort = "max"`, each on its own
  line, with a final newline. These are the existing approved main-model choices.
- Four file symlinks `.codex/agents/<role>.toml` target
  `../../codex/agents/<role>.toml`, for the names in `codex/check.py`'s `ROLES`.
  Source models/efforts stay unchanged. One exact acceptance-validator reference
  becomes project-first with a global fallback, specified by the validator prose plan.
- Three directory symlinks `.agents/skills/<name>` target
  `../../.claude/skills/<name>` for `setup-dotfiles`, `docs-sync`, and
  `readme-screenshots`. Two additional links for `feature` and `retro` target
  `../../codex/skills/<name>`. All real script paths remain at source, and the
  mandatory native workflow is discoverable without installing global assets.
- Root `AGENTS.md` stays canonical; no `.codex/AGENTS.md` or copied rule tree.
  No settings for trust, permissions, hooks, auth, plugins or MCP are added.
- Existing skill copies were backed up privately before dispatch. The worker
  receives a private manifest with original relative paths, modes and hashes.
  No backup, private path, transcript or configuration content goes into git.

## Acceptance and Gates

1. `git ls-files` shows the project config, four agent symlinks and five skill
   symlinks. File types, exact relative targets and source contents are verified
   by `python3 -B codex/check.py`, along with all existing asset checks.
2. Native `config/read` identifies project Astra/max; strict startup accepts it.
   Native prompt discovery sees the four roles, and `skills/list` sees all five
   enabled repo skills in the isolated fresh-clone check with no loading errors.
   Real-checkout discovery may deduplicate identical global/project sources.
3. The original nine skill files remain intact in the private backup; active
   skill paths no longer contain the erroneous product-name substitutions.
4. README matches `plans/codex-project-layer-readme.md` through the prose checker.
5. `just check` passes before commits. Save command/exit/output logs privately
   and associate them with commits. Check `git diff --check 6e44010` before commit
   and `git diff --check 6e44010..HEAD` before finalization.
6. Source skill files and agent model settings stay unchanged; the one role-body
   edit matches its exact prose plan. Preserve global config/hooks across task
   writes and native verification. Compare the initial baseline and snapshots
   before and after native checks. For unrelated concurrent drift, prove its
   timing lies outside task writes, retain the current contents, and record the
   exception privately. Never restore user settings merely to match an old hash.
   Run native verification on the real already-trusted checkout and isolated
   fixtures, without model requests or changes to the user's trust configuration.

## T1: Add and validate the project layer

Own `.codex/config.toml`, four `.codex/agents/*.toml` links, the three named
`.agents/skills/*` links, two native workflow links,
`codex/agents/acceptance-validator.toml`, and `codex/check.py`. No dependencies. First extend the
asset checker and record RED for the missing layer, then create the assets.
Add `check_project()` and invoke it from main. It asserts the exact config object,
regular config file, all nine exact relative links with existing sources, and
the existing screenshot resource `scripts/claude.c` through its skill link.
Print `PASS: project configuration, shared agents and project skills` on success.
Keep all existing checks and `ROLES` values intact; no checker refactor.
Apply/check `plans/codex-project-layer-validator.md` against `6e44010` for the
acceptance-validator source. The native workflow link paths must be absent before
creation; report conflicts rather than replacing an existing entry.

Before replacing skill copies, compare all current paths/modes/hashes with the
private manifest. Any mismatch stops the replacement. Move each existing skill
directory into the provided backup's empty `originals/<name>` path, then create
its symlink; restore that directory if creating its link fails. Never delete
existing contents or overwrite a backup. Preserve any other `.agents` entries.
Gate on equality with `snapshot/<name>` in the private backup, plus active link
resolution. Scope includes only that named private backup, not other home files.

Task gates: `python3 -B codex/check.py`; `git diff --check 6e44010`; original-copy
hash/mode comparisons, relative-link checks, and the validator-role exact prose
check described above. No full suite.
No new tests that merely duplicate the link implementation; asset RED/GREEN and
independent native loader checks verify the changed configuration behavior.

## T2: Document the two configuration layers

Own only `README.md`, no dependency on T1. Apply the exact README prose plan with
`python3 -B claude/skills/feature/plan_edits.py apply` against base `6e44010`.
Task gate is the same command with `check`. No full suite or extra prose edits.

## Seams and edge cases

T1 and T2 share the exact directory/link definitions above. Relative paths must
work in a relocated fresh clone on macOS/Linux, without the global installer.
Missing shared sources, broken links or changed preexisting copies fail safely.
Untrusted-project behavior is documented, not overridden. Shared instructions
may intentionally operate on their original target tool; never mass-rename paths.

## Not doing and baseline

No global installation, runtime permission/model changes outside this project,
new hooks, plugin imports, root guidance edits or source skill rewrites.
Initial guard passed; tracked files are clean. Existing `just check` has 47 tests.
The new project asset criterion and README prose criterion fail on the baseline.
The dry-run identified the global-only reviewer reference; the explicit fallback
and two workflow links close the fresh-clone dependencies before implementation.
Independent skill-dry-run precedes implementation; independent review and final
acceptance precede the authorized fast-forward and push to main.
