# Codex Stop hook output

## Goal

Prevent the Astronomer kernel cleanup hook from returning plain text to Codex
while preserving cleanup, stderr diagnostics, and its exit status.

## Current behavior and evidence

The Astronomer Stop command prints `Kernel not running` when no kernel exists.
Codex rejects that stdout as invalid Stop JSON. The adapter in `codex/plugins.py`
copies upstream hooks verbatim, and `_source_digest` excludes generated additions,
so an adapter-only change currently leaves a prepared marketplace unchanged.
Official contract: <https://learn.chatgpt.com/docs/hooks#stop>, Stop stdout must
be JSON or empty. The existing cleanup command is defined below.

Base: `3be1c54`. Baseline `just check`: PASS (43 Codex tests, four plan tests).
Scoped baseline: `python3 -B -m unittest discover -s codex -p 'test_plugins.py'`
is covered by that successful baseline run. No applicable Python path rules.

## Shared definitions

- Original cleanup command:
  `uv run ${CLAUDE_PLUGIN_ROOT}/skills/analyzing-data/scripts/cli.py stop`
- Adapt only command handlers under Astronomer's `Stop` event whose command
  equals that exact string. Preserve all other commands and event metadata.
- Adapted command is a shell group: `{\n<original>\n} >/dev/null` with real
  newlines. Grouping suppresses stdout from the complete command, retaining
  stderr and the original exit code. Never discard unrelated Stop JSON.
- Deep-copy the hooks object before adaptation; never mutate upstream data.
- Include a deterministic digest of relative paths and bytes of each package's
  generated additions in `_source_digest`, retaining current registry, version,
  source digest and location-independent semantics. Do not change marker schema.

## Acceptance criteria

1. A synthetic `uv` prints `Kernel not running` to stdout, `fixture diagnostic`
   to stderr and exits 7. Executing the generated cleanup command with `/bin/sh`
   yields stdout `""`, stderr `"fixture diagnostic\n"`, and return code 7.
2. SessionStart, an unrelated Stop JSON command, handler metadata, upstream
   manifest bytes, and other packages remain unchanged.
3. Preparing an old unadapted snapshot then regenerating with the new adapter
   and unchanged upstream updates its hooks, creates one backup, and a second
   apply changes neither snapshot nor backups. Existing drift guards still pass.
4. Installed Astronomer `hooks/hooks.json` equals the regenerated marketplace
   version after `codex plugin add astronomer-data@claude-parity --json`.
5. The live config still passes native strict configuration validation. Installed
   cache changes are limited to generated hook assets/CLI install metadata;
   upstream Claude plugin sources remain untouched.

## T1: Adapt cleanup and refresh generated content

Ownership: `codex/plugins.py`, `codex/test_plugins.py`. No dependencies. Implement
tests first, demonstrate RED on the new behavioral regression cases, then implement.
Add `_codex_data_hooks(hooks: dict[str, JSONValue]) -> dict[str, JSONValue]`
for copy/adaptation using `copy.deepcopy`; traverse only
list/dict structures defensively, leaving unrelated or malformed entries unchanged
for existing validation/runtime handling. Apply the helper in `_adapter_additions`.
Update the existing exact-hook preservation test for the targeted exception and
add explicit assertions for unrelated Stop JSON preservation and input immutability.
Use synthetic temporary homes and a fake executable `uv`; never run real cleanup
or download dependencies. Test adapter-only refresh by preparing once with the
adaptation helper patched to return unmodified hooks, then preparing normally.
Assert one backup, then idempotence. Keep source-location independence tests.

Task gate: `python3 -B -m unittest discover -s codex -p 'test_plugins.py'`.
Named mutation: in a scratch copy replace the helper's adapted command assignment
with the original command; run the task gate and require the stdout regression
test to fail. No full suite in implementer/reviewer turns.
Definition of done: acceptance criteria 1-3 and task gate pass with RED evidence.

## T2: Apply and verify live installation

Ownership: main agent, private generated marketplace and installed Astronomer cache
only. Dependency: T1 reviewed green. The cache is already backed up privately under
the existing backup convention; the generator backs up its managed snapshot.
Run `python3 codex/plugins.py --apply`, then
`codex plugin add astronomer-data@claude-parity --json`. Preserve unrelated settings.
Compare installed hook bytes with generated hooks and diff cache against the
private backup. Check CLI output for hook trust requirements; use supported trust
review if available, never edit trust storage or bypass its protections.
Validate `codex app-server --strict-config --print-startup-config`, keeping raw
output privately. Verify synthetic stdout behavior against the installed command.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 generated hooks and digest | T2 live installation | Exact cleanup command and grouped stdout suppression |

## Gates

- `just check`
- `git diff --check 3be1c54`
- T2 installed/generated byte equality, private cache diff, and strict config check

Run `just check` before each commit; save command evidence privately. Commit this
plan, T1, and any reviewed fixes with explicit pathspecs. After final validator PASS,
follow repository fast-forward-to-main and push rules. No CI is configured.

## Edge cases

- macOS/Linux: portable `/bin/sh` grouping; no desktop tools in regression tests.
- Missing tools: fail checks honestly; no installs. No real kernel is required.
- Dirty checkout: initially clean; preserve any concurrent unrelated changes.
- First run: absent marketplace still builds; existing snapshot uses normal backup.
- No matching cleanup or other Stop output: leave commands untouched.
- Source relocation: generated additions contain no machine-specific paths.

## Not doing

No status-line changes, global hook disabling, upstream plugin edits, kernel
implementation changes, dependency installs, documentation rewrites or trust bypass.
