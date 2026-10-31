# Project Reviewer Reference

Base: `6e44010`. Apply to `codex/agents/acceptance-validator.toml`.

**E1.** (lines 41-43)

````md E1-old
"Mutation copy" paragraph of `~/.codex/agents/plan-reviewer.toml` on `HEAD` (baseline,
count-checked replace, `(cd <dir> && <mutation command>)`); to settle a red baseline,
copy the working tree instead, without its virtualenv:
````

````md E1-new
"Mutation copy" paragraph of the project's `.codex/agents/plan-reviewer.toml`,
falling back to `~/.codex/agents/plan-reviewer.toml` when the project file is absent.
Run on `HEAD` (baseline, count-checked replace, `(cd <dir> && <mutation command>)`);
to settle a red baseline, copy the working tree instead, without its virtualenv:
````
