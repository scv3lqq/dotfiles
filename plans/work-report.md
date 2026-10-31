# Standard final report: `work-report` skill

## Goal

Every agent session (both runtimes) ends finished work with the same short report:
a status title, one-sentence outcome, **Changed**, **Checked**, **Next**, **Your call**.
The format lives in a new shared skill `claude/skills/work-report/SKILL.md` (Codex gets it
through `codex/setup.py`, which links every `claude/skills/*` dir into `~/.agents/skills`
unless a `codex/skills/<name>` adapter exists). A short "## Final report" section in both
global instruction files (`claude/CLAUDE.md`, `codex/AGENTS.md`) points to the skill and
carries a fallback shape.

Current behavior: no global final-report format; only per-skill ones (`feature`,
`session-handoff`, `mac-audit`, ...) and subagent-to-orchestrator formats in agent definitions.

Source: two user-supplied drafts (`SKILL.md`, `final-report-rules.md`), adapted to the global
rules: no em dashes (colons instead), report language follows the reply language, at most one
**Your call** question (global "one clarifying question" rule), explicit carve-outs for
colleague text and subagent reports, precedence for a skill's own report items, and a YAML-safe
`description` (no inner `: `, the Codex notes parser rejects malformed frontmatter).

## Gates

Helpers used by the gates and criteria (bash or zsh, repo root `$HOME/dotfiles`). Shell
functions do not survive between tool calls: paste this block at the top of every call that
uses `blk`, `sect`, `$R`, `$P` or `$NOTE`. Any Bash command whose text names
`.../work-report/SKILL.md` (even `test -f`, `diff`) makes the `skill-note-sync` hook print
"Not in the skills index yet" until T1 step 2 lands: expected noise, not a failure.

```bash
R="$HOME/dotfiles"; P="$R/plans/work-report.md"
NOTE="$(cat "$HOME/.claude/private/vault")/meta/claude-code/Claude Code Skills.md"
blk() { [ "$(grep -cxF -e "<!-- $1 begin -->" -e "<!-- $1 end -->" "$P")" = 2 ] || { echo "markers $1 missing"; return 2; }
        awk -v b="<!-- $1 begin -->" -v e="<!-- $1 end -->" '$0==b{f=1;next} $0==e{f=0} f' "$P" | sed '1d;$d'; }
sect() { awk '$0=="## Final report"{f=1;print;next} f&&/^## /{exit} f' "$1"; }
```

Full Gates (orchestrator after the wave, validator in phase 5):

```bash
(cd "$HOME/dotfiles" && just check)
git -C "$HOME/dotfiles" diff -U0 main...HEAD | grep '^+' | grep -c "$(printf '\342\200\224')"   # expect 0
```

Base result (main @ plan commit's parent): `just check` exit 0; em dash count on added lines 0.

## Acceptance criteria

Each is a command; expected result in the comment. Base: A1 to A7 fail (content does not
exist yet), A8 and A9 pass.

```bash
test -f "$R/claude/skills/work-report/SKILL.md"                                          # A1 exit 0
diff <(blk S1) "$R/claude/skills/work-report/SKILL.md"                                   # A2 exit 0, no output
diff <(blk S2 | grep -v '^$') <(sect "$R/claude/CLAUDE.md" | grep -v '^$')               # A3 exit 0
diff <(blk S2 | grep -v '^$') <(sect "$R/codex/AGENTS.md" | grep -v '^$')                # A4 exit 0
[ "$(readlink "$HOME/.claude/skills/work-report")" = "$R/claude/skills/work-report" ] && \
[ "$(readlink "$HOME/.agents/skills/work-report")" = "$R/claude/skills/work-report" ]    # A5 exit 0
grep -cF '`/work-report' "$NOTE"                                                         # A6 prints 1
grep -cF 'Codex shares 23 personal skills' "$R/README.md"                                # A7 prints 1
(cd "$R" && just check)                                                                  # A8 exit 0
git -C "$R" diff -U0 main...HEAD | grep '^+' | grep -c "$(printf '\342\200\224')"        # A9 prints 0
sed -n '/^description: /p' "$R/claude/skills/work-report/SKILL.md" | cut -c14- | grep -c ': '  # A10 prints 0
```

## Shared definitions

- Skill name: `work-report` (dir `claude/skills/work-report/`, frontmatter `name: work-report`).
- S1: the full `SKILL.md` content, byte for byte, between the S1 markers (the outer
  four-backtick fence is not part of the file). The file ends with one newline after the
  last line.
- S2: the "## Final report" section, inserted into both global files. Blank lines are
  per-file style (see T2, T3); the non-blank lines are exactly these.

<!-- S1 begin -->
````md
---
name: work-report
description: Format the final message after finished work (what changed, what was checked, what to do next). Use whenever a task edited files, ran commands or found problems, right before writing the closing summary. Not for questions, explanations or one-line fixes.
---

# Work report

The final report is the part of a session people actually read. Keep it short, honest and easy to scan.

## When to use

Use it when the task edited files, ran tests or builds, or turned up problems.

Skip it for questions, explanations and one-line fixes: answer those in one or two plain sentences. Also skip it for text the user will paste to colleagues (it has its own rule) and for a subagent's report to its orchestrator (its brief or agent definition fixes that format).

A skill with its own report: keep every item it asks for and put each one into the matching section below. Required items that fit no section (a `diff --stat`, decisions made without the user) follow **Your call** as one short labeled block. Only an exact layout the skill spells out (a fixed heading, numbered findings) replaces this template.

## Language

Write the report in the language of your replies, section labels included. Keep the icons, the section order and everything in backticks as is.

## Template

Skip any section that would be empty. Never write "None" or "N/A".

```markdown
### ✅ <What is true now, 3 to 7 words>

<One sentence: the outcome for the user or the system, not the process.>

**Changed**
- `path/to/file.ts:42`: what changed and why

**Checked**
- ✅ `command`: result, in numbers
- ⚠️ `command`: not run, reason
- ❌ `command`: what failed

**Next**
- 🔴 Must do: reason
- 🟡 Worth doing: reason
- ⚪ Nice to have: reason

**Your call**
- One decision or question only the user can answer
```

Status icon in the title:

- ✅ done and verified
- ⚠️ done, but something is unverified or only partly works
- ❌ blocked or failed; the first sentence says what blocks it

## Section rules

**Title.** The result, not the activity: "Login survives expired tokens", not "Implemented token refresh logic".

**Changed.** Up to 5 lines. With more files, list the important ones and add a line such as "+ 4 small edits in `tests/`". Add line numbers where they help someone jump to the code.

**Checked.** Only real commands with real results. ✅ means it ran in this session, by you or by an agent you dispatched, and you saw it pass in its output or in that agent's report. A check you did not run gets ⚠️ and the reason. Mark old failures "pre-existing" so nobody chases them.

**Next.** At most 3 items, highest priority first, each concrete enough to act on without asking you. Include problems you noticed but did not fix: bugs, risks, tech debt. Drop generic advice such as "add more tests" or "improve documentation".

**Your call.** At most one open decision, phrased so the user can answer in a few words. Other open points go to **Next**.

## Writing rules

- Write like a senior engineer's own work log: plain, specific, no ceremony.
- The whole report fits on one screen: about 15 lines, never over 20. Cut until it does.
- One line per bullet. No nested bullets, no paragraphs inside lists.
- Numbers beat adjectives: "128 passed", "3 files", "p95 420 → 180 ms".
- Active voice. Past tense for what you did, present tense for how things are now.
- Paths, commands, functions and env vars go in backticks. Never combine bold and backticks.
- Separate a bullet's subject from its note with a colon. No em dashes.
- Do not restate the request or narrate the steps ("First I looked at...").
- Do not paste file contents or long diffs: point to the path.
- No opener ("Great!", "I've successfully...") and no closer ("Let me know if...", "Hope this helps").

Cut these words and their equivalents in the reply language. They add length and sound machine-written:
successfully, comprehensive, robust, seamless, leverage, utilize, ensure, enhance, streamline, delve, crucial, notably, "it's worth noting", "in order to", various, "a number of", "as requested".

## Example

Before:

> I have successfully implemented a comprehensive token refresh mechanism to ensure a seamless user experience. First, I analyzed the authentication flow, then I modified several files. All tests are passing. Let me know if you need anything else!

After:

```markdown
### ✅ Login survives expired tokens

Users stay signed in when the access token expires: the app refreshes it and retries the request once.

**Changed**
- `src/auth/session.ts:42`: refresh on 401, then retry once
- `src/api/client.ts:88`: backoff 1s → 4s instead of instant retries

**Checked**
- ✅ `npm test`: 128 passed
- ⚠️ `npm run e2e`: not run, needs staging credentials

**Next**
- 🔴 `.env.example` holds a real API key: rotate it
- 🟡 Add an e2e test for the refresh flow

**Your call**
- Remove the old `/v1/login` endpoint, or keep it for mobile 2.x?
```

## Final check

Before sending, confirm:

1. The first line says what is true now.
2. Every ✅ matches a command run in this session, by you or a dispatched agent.
3. Skips and failures are listed, not hidden.
4. No empty sections, each bullet fits on one line, no em dashes.
5. A teammate could act on **Next** without asking you anything.
````
<!-- S1 end -->

<!-- S2 begin -->
````md
## Final report
- After a task that edited files, ran checks or found problems, end with a short report: load the `work-report` skill and follow its template and rules
- Without the skill, use this shape and skip empty sections: status icon (✅ done and verified, ⚠️ partly unverified, ❌ blocked) + a title saying what is true now, a one-sentence outcome, then **Changed**, **Checked**, **Next**, **Your call**; labels in the reply language
- Lead with the outcome, not the process: the whole report fits on one screen (~15 lines, 20 max), one line per bullet, paths and commands in backticks (a path with its line number where it helps), no opener or closing offer
- ✅ only for a check run in this session (by you or a dispatched agent) and seen passing; list skipped checks with the reason
- **Next**: at most 3 concrete items, ranked 🔴 must / 🟡 should / ⚪ nice; **Your call**: at most one question
- An active skill's own report items go into these sections (items that fit none follow as one short block); a layout the skill spells out replaces this shape
- No template for questions, explanations, one-line fixes, text for colleagues (rule above) or a subagent's report to its orchestrator (its brief's or agent definition's format)
````
<!-- S2 end -->

## Tasks

All tasks run in one parallel wave (disjoint files). No task runs the full Gates.

### T1: create the skill and make it live

Files: `claude/skills/work-report/SKILL.md` (new); outside git: the vault skills index `$NOTE`,
links `~/.claude/skills/work-report`, `~/.agents/skills/work-report`.

Steps, in this order (the `skill-note-sync` PostToolUse hook nags with exit 2 when a
`SKILL.md` is written before its index line exists):

1. Back up the index: `cp "$NOTE" "$S/skills-index.bak"` (`$S` = the scratchpad dir given in
   the dispatch prompt). If `$NOTE` does not exist, skip steps 1 and 2 and say so in the report.
2. Insert the one index line given verbatim in the dispatch prompt (it is non-English, so it
   is not spelled out in this public plan; it starts with ``- `/work-report` *: ``, the `*`
   because the skill is model-invocable) on a new line right after the line that starts with
   ``- `/vpn-xray` `` (the end of the personal group's main list). Change nothing else.
3. `mkdir -p "$R/claude/skills/work-report"`, then in the same call (helpers pasted on top)
   `blk S1 > "$R/claude/skills/work-report/SKILL.md"`. Do not retype S1.
4. Make it live (changes `$HOME`; run only these, in order):

```sh
ln -s "$HOME/dotfiles/claude/skills/work-report" "$HOME/.claude/skills/work-report"
python3 -B "$HOME/dotfiles/codex/setup.py"            # preview: must report exactly 1 link, guidance unchanged
python3 -B "$HOME/dotfiles/codex/setup.py" --apply    # only if the preview matched
```

If the preview reports anything other than one new link with guidance and theme unchanged,
do not apply: stop and report BLOCKED with the preview line.

Must not change: any other skill, any other line of `$NOTE`, any other link.

Task gates:

```bash
diff <(blk S1) "$R/claude/skills/work-report/SKILL.md"                     # exit 0
diff "$S/skills-index.bak" "$NOTE" | grep -c '^>'                          # prints 1
diff "$S/skills-index.bak" "$NOTE" | grep -c '^<'                          # prints 0
grep -cF '`/work-report' "$NOTE"                                           # prints 1
[ "$(readlink "$HOME/.claude/skills/work-report")" = "$R/claude/skills/work-report" ] && \
[ "$(readlink "$HOME/.agents/skills/work-report")" = "$R/claude/skills/work-report" ]  # exit 0
```

Done: gates pass; commit only `claude/skills/work-report/SKILL.md`
(`feat(skills): add work-report final report format`). The vault note is not committed.

### T2: global section in `claude/CLAUDE.md`

One Edit. `old_string`: `## Code style: Go` (line 17, unique). `new_string`: block S2
verbatim (no blank line after its header, matching this file's sections), then one blank line,
then `## Code style: Go`. Result: the S2 section sits between `## Response style` and
`## Code style: Go`, each separated by one blank line.

Must not change: any other line.

Task gates:

```bash
diff <(blk S2 | grep -v '^$') <(sect "$R/claude/CLAUDE.md" | grep -v '^$')   # exit 0
git -C "$R" diff --numstat -- claude/CLAUDE.md                               # 9 added, 0 deleted
```

Done: gates pass; commit only `claude/CLAUDE.md` (`docs(claude): add final report rule`).

### T3: global section in `codex/AGENTS.md`

One Edit. `old_string`: `## Code quality` (line 16, unique). `new_string`: the S2 header
line, one blank line (this file's sections have a blank after the header), the S2 bullets
verbatim, one blank line, then `## Code quality`.

Must not change: any other line. The file must stay free of product names (checked by
`codex/check.py`).

Task gates:

```bash
diff <(blk S2 | grep -v '^$') <(sect "$R/codex/AGENTS.md" | grep -v '^$')    # exit 0
git -C "$R" diff --numstat -- codex/AGENTS.md                                # 10 added, 0 deleted
python3 -B "$R/codex/check.py"                                               # exit 0
```

Done: gates pass; commit only `codex/AGENTS.md` (`docs(codex): add final report rule`).

### T4: README skill count

One Edit in `README.md:176`: `old_string` `Codex shares 22 personal skills`, `new_string`
`Codex shares 23 personal skills`. Nothing else.

Task gates:

```bash
grep -cF 'Codex shares 23 personal skills' "$R/README.md"                    # prints 1
git -C "$R" diff --numstat -- README.md                                      # 1 added, 1 deleted
```

Done: gates pass; commit only `README.md` (`docs(readme): count work-report skill`).

## Seams

| Producer | Consumer | Shared definition |
|---|---|---|
| T1 (skill dir `work-report`) | T2, T3 (section names the skill) | Skill name |
| T1 (new `claude/skills/*` dir) | T4 (README count 22 to 23) | Skill name |
| T2 | T3 | S2 (same non-blank lines in both files) |

## Edge cases

- macOS vs Linux: the skill is OS-neutral; `install.sh:378` links every `claude/skills/*`
  dir on both OSes (only `mac-*` is skipped off Darwin), `install.sh:451` runs
  `codex/setup.py --apply`. No OS branching needed.
- Missing tools: none new. A missing vault note (fresh machine) only silences the hook; T1
  skips its index steps.
- Dirty worktree: only the untracked `.DS_Store`, outside every task.
- First run on a new machine: `install.sh` creates both links; nothing manual.
- Running sessions may need a restart to list the new skill.

## Not doing

- Rewriting report sections of other skills (`feature`, `session-handoff`, `mac-audit`,
  `retro`, ...): the skill's precedence rule covers them.
- Agent definitions' report formats (`claude/agents/*`, `codex/agents/*`).
- A Codex adapter `codex/skills/work-report/`; changes to `codex/check.py` or
  `codex/test_setup.py`.
- The root `AGENTS.md` (project guidance) and its 200-line budget.
- Re-wrapping S2 to the 80-column, period-terminated style of `codex/AGENTS.md`: one
  identical block in both files keeps the A3/A4 checks a plain diff.
- Committing the vault note.
