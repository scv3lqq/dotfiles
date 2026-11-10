# Project agent workflow

Start Codex normally in the desired directory with `codex`. The user-scope
Planner identifies questions and change requests automatically and selects
relevant skills. Simple
questions are answered read-only; complex research can use a short-lived Explorer
with temporary reports. Change requests receive a plan for approval before the
implementation team starts. You continue to communicate with Planner only.

After approval, the Planner prepares runtime metadata and native agents
coordinate implementation, independent review, a bounded correction loop,
validation and a retrospective. The working root is the Git top-level directory
when available, otherwise the launch directory. User paths remain relative to the
original launch directory before conversion to working-root paths. Run state and
reports are held in that root's ignored `.harness/runs/<run-id>/`; this guide and
`.gitignore` are intended for version control. A missing ignore file is created
with narrow runtime rules after approval; conflicting existing rules stop the run
without being overwritten. An Archivist proposes skill improvements but does not
apply them without your approval.

The shared protocol and state helper come from the installed user-scope harness
skill, not from the working project. A trusted project's explicit Codex developer
instructions or model settings can override user defaults. Start a new session to
load changed defaults; an existing session may retain its earlier configuration.

To continue after an interruption, start Codex normally and ask it to continue
the run. Include the run ID if more than one run is unfinished. A blocked run
requires explicit permission to resume and intact approved evidence. State checks
detect changed plans, reports and bound source files; review findings and command
results still need human or agent judgment. The process does not restart itself.

Agents inherit the session's permissions. Read-only behavior and approval gates
are instructions and state checks, not separate operating-system restrictions.
External service availability, context inheritance and model access can limit a
run; the final report should distinguish observed evidence from unrun checks.
