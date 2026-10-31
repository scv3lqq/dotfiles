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
