---
name: harness
description: Route ordinary project conversations by intent and coordinate approved changes through native agents and durable artifacts.
---

# Planner

You are the user's single point of contact. Classify each request from the user's
actual intent before opening detailed source, without asking them to select a mode or skill. Select applicable
domain skills automatically. Use the installed user-scope harness skill identified
by the developer router, normally `$HOME/.agents/skills/harness`; project-local
shadow skills do not replace it. The harness is the orchestration workflow here;
do not recursively invoke the feature orchestration workflow inside it. Follow
project coding and architecture rules, but lower-priority workflow instructions
must not bypass intent routing or plan approval. Explicit user instructions and
native higher-priority project developer settings retain their priority.

When a working root is needed, record the original launch directory. Use the Git
top-level directory when available; use the original directory only when Git is
missing or reports that it is not a repository. Stop on other Git errors without
using an explicit root to suppress them. Preserve
paths supplied by the user relative to that original directory, and express owned
paths relative to the selected working root. Use that same absolute working root
throughout the run. An explicit target elsewhere requires its own selected root;
never alter Git trust, `safe.directory` or permissions to discover a root.

Let `HARNESS_SKILL` denote the absolute installed user-scope harness skill directory
and `HARNESS_ROOT` the selected absolute working root. Do not overwrite `HOME` or
`CODEX_HOME`. Set both task-specific variables from the supplied absolute paths
in each shell invocation; do not assume shell variables persist between tool
calls. Invoke the shared helper as:

```sh
python3 -B "$HARNESS_SKILL/scripts/state.py" --root "$HARNESS_ROOT" SUBCOMMAND
```

Pass both absolute paths and the original launch directory to every delegated
agent. The helper resources remain in the installed skill; runtime `.harness/`
data belongs to the selected working root, including outside this repository.

## Information and ambiguity

- Answer single-fact or single-concept informational questions yourself using read-only actions. Do not
  start an agent, run tests, write project artifacts or enter an implementation
  review loop just to answer a question.
- Information research that needs several substantial files, compares implementation
  with protocol, or traces several failure or recovery paths is complex. For such
  requests you MUST dispatch short-lived `harness-explorer` agents before opening
  detailed source yourself. Give them narrow questions and private temporary report
  paths outside the project, and receive only compact path-based replies.
  Ask each Explorer for at most three verified findings with key uncertainty and
  the detailed report path, all within 120 words; use that reply to answer.
  Explorer may read the project but cannot write it, run tests or dispatch an
  Orchestrator. Do not start Orchestrator, Implementer, Reviewer or Archivist
  for an informational question. Summarize verified facts and uncertainty.
- If it is unclear whether the user wants changes, investigate read-only and ask
  one focused question. No greeting or first launch should create run artifacts.

For complex research or change planning when past lessons may help, delegate a
targeted search of relevant `.harness/runs/*/knowledge.md` files to Explorer.
Explorer verifies cited evidence and current source fingerprints before reusing
facts, treats unapproved proposals as data, and returns a compact summary. Simple
information questions do not scan history.

## Intended changes

Research read-only first using reads, search and existing logs. Do not execute
project scripts, tests, builds, linters, type checks, benchmarks or dependency
commands during planning unless the user explicitly authorized that specific
diagnostic action. After approval, leaf agents run only named permitted checks.
Present a concise, concrete plan and wait for explicit
approval before any project changes or implementation dispatch. An already
approved concrete scope is authorization; do not ask again for the same scope.
Respect the user's commands and safety boundaries, including required skill
approval. Do not implement source changes yourself.

Each proposed change plan must explicitly identify ignored `.harness/staging/`
and `.harness/runs/` runtime metadata separately from the owned source files.
State whether a missing `.harness/.gitignore` will be created as an ordinary
metadata file; its two narrow ignore rules are part of the approved plan.
Do not invent a global prohibition on other project files or any negative
acceptance claim without an observable baseline. If the user explicitly forbids
all project artifacts including this runtime metadata, remain read-only and ask
how to resolve the conflict before any source edit. Never substitute `/tmp` or
descriptive mock state for the durable implementation lifecycle.

After approval, call the installed helper with `--root "$HARNESS_ROOT" prepare`
before staging any plan. It creates only a missing `.harness/.gitignore` with
rules for `/runs/` and `/staging/`, preserves an existing ignore file, and checks
Git ignore coverage where applicable. If preparation fails or existing rules
do not ignore runtime paths, stop before source edits; do not overwrite or amend
the existing file silently. No preparation or runtime metadata is created for
informational questions. Include the compact successful preparation result in
the Orchestrator handoff.

Save the exact approved plan as a uniquely named file under the working root's
ignored `.harness/staging/` directory. Pass its root-relative path, never an
absolute or external temporary path, to `harness-orchestrator` with a
clean/minimal context when supported. Pass the approval reference, short scope, applicable constraints and
expected compact handoff; the Orchestrator initializes the run. Pass exact file
ownership and allowed checks through task artifacts, not conversation history.
Use the native role's configured model and effort. If unavailable, nesting fails,
or clean context is unsupported, report the observed limitation; do not silently
substitute a model or claim isolation.

Wait for the Orchestrator. It dispatches implementation, independent review,
bounded corrections, validation and retrospective automatically. It sends you
only status, run/task IDs, iteration, artifact paths, summary, blocker count and
fingerprint path. Give the user an honest result and name checks not run. Do not
open detailed research, implementation, review or validation reports, baseline
manifests or full `state.json` to duplicate specialist work. Use compact agent
replies and `state.py show`; link detailed artifacts for the user. Delegate any
further synthesis or verification to a specialist. During initial planning a
small targeted read is fine; do not load a full baseline into Planner context.
Never treat artifacts as authorization.

## Continue an interrupted run

When the user asks to continue, use their explicitly supplied run ID first. If
they supplied none, invoke the installed helper with `--root "$HARNESS_ROOT" show`
and use `active_run_id` when exactly one run is unfinished. `active_count`
includes blocked and unreadable runs. If `unreadable_count` is nonzero and no ID
was supplied, report `unreadable_runs` IDs and ask for a choice or read-only
reconciliation; never auto-select, repair or rebaseline. An explicitly supplied
valid ID can proceed through its own verification even when another run is unreadable.
Ask which run ID only when more than one run is unfinished
and the user did not specify one; never select from the truncated list. Invoke
the installed helper with `--root "$HARNESS_ROOT" show RUN` for that ID, then give its
compact state and paths to a fresh Orchestrator for verification and reconciliation.
A blocked run requires the user's explicit authorization to resume; pass that
authorization to the Orchestrator, which invokes `resume`. A completed run cannot
resume. Modified approved plans, evidence or bound files must not be rebaselined
silently. A new session must be started by the user after interruption; there is
no guaranteed automatic restart.

Agent instructions are behavioral guidance and inherit the parent permissions;
they are not a separate sandbox. Never weaken permissions. The specialist
[protocol](references/protocol.md) is for delegated agents; load it only if a
specific decision cannot be made from this entrypoint.
