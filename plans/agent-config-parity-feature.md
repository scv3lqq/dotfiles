# Agent Config Parity Feature

Base: `034acd6`. Apply and check with the canonical prose helper.

**E1.** (lines 17-19)

```md E1-old
- Read project `AGENTS.md`; follow a linked `CLAUDE.md` when that is its source.
  Explicitly read applicable `.claude/rules` after inspecting their `paths`.
  Neither file reads nor subagent spawns imply Claude rule auto-injection.
```

```md E1-new
- Read project `AGENTS.md`; resolve instruction-file aliases and edit the
  canonical target. Explicitly read applicable `.claude/rules` after inspecting
  their `paths`. Neither reads nor spawns imply Claude rule auto-injection.
```

**E2.** (lines 21-25)

```md E2-old
- Use native roles `implementer`, `plan-reviewer`, `acceptance-validator` and
  `skill-dry-run`. For research use available `explorer` or `default` agents.
  The custom role TOML files own reasoning settings; inherit the parent model.
  Ignore every canonical Claude model/effort dispatch or tier-switch directive,
  including failure retries and repeated-finding escalation. Never pass
```

```md E2-new
- Use native roles `implementer`, `plan-reviewer`, `acceptance-validator` and
  `skill-dry-run`. For research use available `explorer` or `default` agents.
  The custom role TOML files own approved model and reasoning settings. When the
  current runtime cannot select a configured role, use an available agent with
  the same instructions and approved model; disclose that fallback.
  Ignore every canonical Claude model/effort dispatch or tier-switch directive,
  including failure retries and repeated-finding escalation. Never pass
```
