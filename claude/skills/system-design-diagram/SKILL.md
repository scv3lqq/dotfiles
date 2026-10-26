---
name: system-design-diagram
description: >
  Design a system AND draw its architecture in one pass, with no clarifying questions.
  Use when a single request asks for both: "спроектируй X и нарисуй архитектуру",
  "design X and diagram it", "HLD + Excalidraw", "спроектируй систему типа Uber и нарисуй
  high-level архитектуру", "architect this and give me a diagram", "design a URL shortener
  and draw it in Excalidraw". Covers scale estimates, component choice, data stores, and
  produces a rendered .excalidraw + .png. Do NOT use when the request is design-only
  (use system-design) or diagram-only (use excalidraw-diagram).
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# System Design to Excalidraw (one pass)

The user wants a designed architecture and a rendered diagram from a single message.
Never ask clarifying questions. Decide, state the assumptions, deliver both artifacts.

## Inputs to load first

1. `~/.claude/skills/system-design/references/knowledge-base.md` : the 5-step framework,
   formulas, case studies, red flags. Load it every time.
2. `~/.claude/skills/excalidraw-diagram/SKILL.md` : diagram methodology and the render loop.
   On this path read it from the container section onward, 19 KB instead of 26 KB:
   `awk '/^## Container vs/,0' ~/.claude/skills/excalidraw-diagram/SKILL.md`
   (still in ≤25 KB chunks). The skipped 7 KB (depth assessment, research mandate,
   evidence artifacts, multi-zoom) decides what Step 3 below already decides, and
   pulls an HLD toward code snippets it should not have.
3. `~/.claude/skills/excalidraw-diagram/references/color-palette.md` and
   `element-templates.md` : colors and JSON templates.

These reads are independent of each other: issue the chunks as parallel Bash calls in one
message, not one round trip per chunk.

## Step 1: Assumptions, not questions

The request will be underspecified. Fill every gap yourself and open the answer with a
short assumptions block: user count and DAU split, read/write ratio, peak QPS, payload
sizes, retention, consistency requirements, regions, latency budget. Derive numbers with
the back-of-envelope formulas from the knowledge base rather than inventing round figures.

Close the block with one line: these assumptions drive the design, say which to change.

## Step 2: Design

Run the 5-step framework from the knowledge base. Keep it text, keep it tight:
functional scope, scale math, high-level components, data model and stores, then the
deep dive on whatever actually makes this system hard (matching, geo-index, fan-out,
dedup, hot partitions). Name concrete technologies and justify each with a trade-off.
Start from RDBMS and argue your way off it, never assume NoSQL.

## Step 3: Diagram

Build the `.excalidraw` JSON from the design in Step 2. Defaults for this path:

- Scope: the high-level architecture, not a low-level class diagram.
- Depth: conceptual to mid. Skip evidence artifacts (code snippets, JSON payloads)
  unless the user asked for a technical deep-dive diagram.
- Target 12 to 25 **nodes** (boxes and stores), not JSON elements: a finished HLD of that
  size is 70 to 100 elements once bound texts, arrows and labels are counted. A design that
  needs 60 nodes is two diagrams; split it and say so.
- Group by tier (edge, service, data, async) and label the arrows with the protocol.
- Colors come from `color-palette.md`. Semantic, not decorative.
- User asks for a multi-frame board (requirements, estimates, HLD, deep dives, ADRs) or a
  spec/generator they can regenerate: use `~/.claude/skills/excalidraw-diagram/references/board/`
  (see excalidraw-diagram "Large / Comprehensive Diagram Strategy"), not hand-written JSON.
- If the user's own prompt asks for a plan and confirmation first, that overrides "no questions".

Default output directory: `~/diagrams/`. Create it if missing. File name is a slug of the
system, e.g. `~/diagrams/uber-hld.excalidraw`. If the user named a path, use theirs.

## Step 4: Render loop (mandatory)

```bash
uv run --project ~/.claude/skills/excalidraw-diagram/references \
  python ~/.claude/skills/excalidraw-diagram/references/render_excalidraw.py <absolute-path-to-file.excalidraw>
```

Then Read the PNG and fix what you see: clipped text, overlaps, arrows crossing elements
or landing in empty space, uneven spacing, unbalanced composition. Re-render. Repeat
until it holds, typically 2 to 4 passes. Never ship a diagram you have not looked at.

If the render fails on the esm.sh import, the pinned version in `render_template.html`
has rotted; pin a newer `@excalidraw/excalidraw@<ver>?bundle` that resolves.

## Step 5: Answer shape

1. Assumptions block.
2. Design: components, stores, the hard part, trade-offs.
3. Both file paths, `.excalidraw` and `.png`.
4. One line on what you would change first if a stated assumption is wrong.

No questions anywhere in the answer. The user iterates by sending a correction.
