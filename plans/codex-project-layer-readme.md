# Codex Project Layer README Edits

Base: `6e44010`. Apply to `README.md` with the shared prose helper.

**E1.** (lines 168-170)

````md E1-old
The root `AGENTS.md` is the canonical, provider-neutral instruction file;
`CLAUDE.md` links to it. Global Codex assets live in tracked `codex/`, not a
project-local `.codex/`: the setup helper links them into the user's home.
````

````md E1-new
The root `AGENTS.md` is the canonical, provider-neutral instruction file;
`CLAUDE.md` links to it. The tracked `.codex/` is this repository's project layer:
its config selects Astra with max reasoning, and its four agent definitions link
to the shared sources in `codex/agents/`. Project settings load for trusted projects.
The tracked `.agents/skills/` links the three project skills and their resources
to `.claude/skills/`, plus the native `feature` and `retro` workflows from
`codex/skills/`. The `codex/` directory remains the source for global setup.
````

**E2.** (lines 181-181)

````md E2-old
The main model is unchanged. The `feature` and `retro` skills have Codex adapters;
````

````md E2-new
The global setup preserves the current main model. The `feature` and `retro`
skills have Codex adapters;
````

**E3.** (lines 371-371)

````md E3-old
| `.claude/skills/` | | Claude Code skills of this repo: `/setup-dotfiles`, `docs-sync` |
````

````md E3-new
| `.claude/skills/` | | shared project skill sources: `setup-dotfiles`, `docs-sync`, `readme-screenshots` |
| `.agents/skills/` | | relative links to three shared project skills and the native `feature`/`retro` workflows |
| `.codex/` | | project configuration and relative links to shared native agents |
````
