# Global Codex instructions

## Communication

- Respond in Russian; write code, comments, docs and commits in English.
- Be concise, skip stock preambles and unsolicited alternatives. Push back when
  evidence contradicts the request. Use at most one clarification question per reply.
- Avoid the em dash character; use a colon, comma, parentheses or a rewrite.
- Text intended for colleagues: at most five lines, warm tone, lead with the link
  or location, no advice unless requested. Expand only when asked.
- Plan before non-trivial edits. Explain design decisions and tradeoffs, clarify
  material ambiguity, and identify missing required inputs before dependent work.
- Automate authorized steps around passwords, OAuth and GUI login; leave the user
  one short list of steps that require their participation.

## Code quality

- TDD: write meaningful tests first for behavioral changes, then implement.
- Clean Code: meaningful names, small functions, single responsibility and DRY.
- Comments explain why. Consider edge cases and prefer self-documenting structure.
- Clean Architecture: separate concerns; inner layers never depend on outer layers.
- Go is the default for a new standalone service or tool. Use zerolog, pgx v5,
  sqlc, goose, table-driven tests and golangci-lint v2. Wrap errors with
  `fmt.Errorf("operation: %w", err)`. No gorm, ent, slog or raw database/sql.
- Go layout: `cmd/`, `internal/{domain,usecase,handler,repository,app}/`, `pkg/`,
  `api/`. Avoid global mutable state.
- Python 3.11+, type hints, mypy strict, ruff for lint/format, uv for dependencies,
  pydantic v2 or dataclasses for structured data. No unexplained `Any`, untyped
  lambdas or module-level mutable state. Outside a uv project use `uvx ruff` and
  `uvx mypy`; preserve a project's existing dependency workflow when out of scope.
- Data work: prefer Iceberg V2, Spark SQL before PySpark, dbt for Impala,
  Airflow TaskFlow and sensors/deferrable operators instead of task sleeps.
  Use Spark or Polars instead of pandas above one million rows. Make S3 retry
  and quota handling explicit; state Kafka delivery semantics.

## Orchestration

- Beyond a micro task, use agents. Main plans, dispatches, decides and reports;
  agents investigate, implement and review. A micro task is at most two short
  calls on known targets or an edit of at most three already-decided lines.
- For non-trivial changes use `$feature`: `implementer` owns scoped edits,
  `plan-reviewer` independently reviews, `acceptance-validator` proves completion,
  and `skill-dry-run` checks instruction workflows before implementation.
- Give each agent explicit file ownership, a self-contained task, plan path,
  exact scoped gates and a bounded report. Tell workers they share the checkout
  and must preserve other agents' edits. Verify required paths/tools first.
- Parallelize only independent file sets, in waves limited by available runtime
  slots. Run heavy/full suites serially. Reuse an agent for fixes with exact
  findings and gates: message a running agent, follow up to resume an idle one.
- Native roles inherit the parent's model; their TOML files set reasoning effort.
  Never pass Claude model IDs to Codex. Do not change model defaults implicitly.
- Trust command evidence. Avoid duplicate exploration and raw log dumps; send
  unresolved findings to an independent reviewer. Stay active until all required
  agent results have been integrated and the task is complete or truly blocked.

## Git and verification

- Use Conventional Commits, English imperative subjects, at most 72 characters.
  Use context7 for the spec if unsure. No generated/AI attribution or trailers.
- Run `just check` before each commit; use the project's documented equivalent
  where no justfile exists, and report a missing verification command honestly.
- Preserve configured commit signing. Use explicit file pathspecs, never stage
  unrelated changes. Prefer small, reviewable commits and trunk-based work.
- Commit and push finished, verified authorized changes without asking again,
  following project branch rules; check CI when present. Never force-push or
  rewrite history unless explicitly requested.
- Check fresh git status and recent commits before planning commit scope.
- Public repo artifacts contain no personal identities, hosts, private URLs,
  home paths, credentials or transcript excerpts. Do not copy private memories.
- Clean up only resources created for the task by name; never broad Docker prune.

## Local workflow and shared skills

- Use `rg`, focused reads and the tool's workdir. Shell is zsh: quote globs and
  variables, use `${name}:path` rather than `$name:path`, and use `python3`.
  macOS system Bash is 3.2; avoid associative arrays and newer Bash-only syntax.
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
