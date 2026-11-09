# Supplemental T6 README exact edits

Base: 096bd52. Scope and gates: T6 in codex-terra-subagents.md.

**E1.** (lines 198-202)

````md E1-old
Global config changes are limited to `tui.theme` and the two subagent defaults.
Conflicting files are reported; replaced guidance and configuration are backed
up privately outside the repo. Restart Codex to load saved defaults and role
pins: an already-running session can retain its loaded settings. Verify actual
child selection in fresh subagents, rather than inferring it from saved files.
````

````md E1-new
Global config changes are limited to `tui.theme`, the two subagent defaults
and explicit declarations for managed roles. CLI 0.167.0 can discover a symlinked
role yet reject its spawn. Each `[agents.<role>]` declaration supplies a supported
`config_file` pointing to the canonical TOML, keeping the shared symlinks intact.
Project paths are relative to the declaring config; global setup resolves them.
Existing conflicting role files are skipped; conflicting explicit declarations
fail before writes. Replaced guidance and configuration are backed up privately.
Restart Codex to load saved defaults and declarations: an already-running
session can retain its loaded settings. Verify actual child selection in fresh
subagents, rather than inferring it from saved files.
````
