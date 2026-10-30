# Agent Config Parity Global

Base: `034acd6`. Apply and check with the canonical prose helper.

**E1.** (lines 1-1)

```md E1-old
# Global Codex instructions
```

```md E1-new
# Global agent instructions
```

**E2.** (lines 50-51)

```md E2-old
- Native roles inherit the parent's model; their TOML files set reasoning effort.
  Never pass Claude model IDs to Codex. Do not change model defaults implicitly.
```

```md E2-new
- Native roles use the model and reasoning effort in their approved runtime
  definitions; absent settings inherit the parent. Use only model IDs supported
  by the active runtime. Do not change model defaults implicitly.
```

**E3.** (lines 77-90)

```md E3-old
- Codex guidance lives in `AGENTS.md`, native agent definitions in
  `~/.codex/agents/*.toml`, and personal skills in `~/.agents/skills/`.
  These managed files link to dotfiles; edit their source and commit scoped paths.
- Shared Claude skills keep their real script/data paths. A skill about Claude
  settings, sessions or tmux still operates on Claude; never mass-rewrite its paths.
- Interpret Claude tool vocabulary through available Codex tools: Read/Grep/Glob
  are focused file/shell reads, Edit/Write are file edits, Agent is native spawn,
  SendMessage is message/follow-up, and TodoWrite is task tracking if available.
  Tool names in imported frontmatter do not grant tools or change permissions.
- Read applicable `.claude/rules` explicitly after checking their path scopes.
  Do not assume Claude rule auto-injection, hook enforcement, or model aliases.
  Existing project `AGENTS.md` takes precedence; its CLAUDE.md symlink is valid.
- context7 supplies current library docs; firecrawl supplies page research when
  available. Use official source/schema evidence for exact behavior.
```

```md E3-new
- Shared guidance lives in `AGENTS.md`; runtime configuration defines native
  roles, scoped rule directories and skill discovery locations. Managed files
  link to dotfiles: resolve links, edit their source and commit scoped paths.
- Shared skills keep their real script/data paths and their stated target tool.
  Never mass-rewrite paths merely because another runtime invokes a skill.
- Interpret imported tool vocabulary through available capabilities: file reads
  and searches, edits, native agent spawning, messages and task tracking.
  Frontmatter tool names do not grant tools or change permissions.
- Read configured project rules explicitly after checking their path scopes.
  Do not assume rule auto-injection, hook enforcement or model aliases.
  Project `AGENTS.md` takes precedence; resolve any instruction-file aliases
  and edit the canonical target.
- context7 supplies current library docs; firecrawl supplies page research when
  available. Use official source/schema evidence for exact behavior.
```

