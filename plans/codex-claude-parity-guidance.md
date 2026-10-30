# Codex repository guidance edits

Apply with `claude/skills/feature/plan_edits.py` against base `9e75c74`.

```md E1-old
No database, no migrations, no service/API, no CI, no test suite.
```

```md E1-new
No database, migrations, service/API or CI. `just check` validates shell and Codex setup.
```

```md E2-old
- `plans/`: PLANNER's implementation plans (`<task-name>.md`).
```

```md E2-new
- `codex/`: native agents, guidance, skill adapters, Ayu theme and isolated setup checks.
- `plans/`: PLANNER's implementation plans (`<task-name>.md`).
```

```md E3-old
- `everything.md`: Russian cheatsheet of the whole stack and keymaps, derived
  from the configs, so it lags them.
```

```md E3-new
- `everything.md`: Russian stack/keymap cheatsheet, derived from configs and sometimes stale.
```

```md E4-old
- `.claude/skills/`: project skills `setup-dotfiles` (`/setup-dotfiles`), `docs-sync`,
  `readme-screenshots`.
```

```md E4-new
- `.claude/skills/`: project skills `setup-dotfiles`, `docs-sync`, `readme-screenshots`.
```
