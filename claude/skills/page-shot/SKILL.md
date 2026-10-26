---
name: page-shot
description: Screenshot an HTML page (local file, localhost server or URL) in headless Chrome at any width, real phone widths like 375 px included, optionally after running JS in the page first (click a tab, type into a field, press a button, await a reload). Use to check a page you built or changed before reporting it done, "как выглядит страница", "проверь на мобильной ширине", a dashboard or skill page after an edit.
argument-hint: "<url|file.html> [width]"
allowed-tools: Bash(node:*), Read
---

# Page screenshot

`node ~/.claude/skills/page-shot/shot.mjs <url|file.html> <scratchpad>/<name>.png [width=1280] ['<js>']`,
then Read the PNG.

- Widths below ~500 px need this script: `chrome --headless --window-size=375,...` renders wider and crops.
  Under 500 px it emulates a phone: a page without `<meta name="viewport">` lays out at 980 px, as on a phone.
- `<js>` runs after load with top-level await: `document.querySelector('[data-view=list]').click()`; a
  field: `const i = document.getElementById('x'); i.value = '3'; i.dispatchEvent(new Event('input'))`;
  a reload it triggers: `await new Promise(r => setTimeout(r, 3000))`. The last expression's value (no `return`: it is a SyntaxError) prints as
  `js: ...`; an exception prints and exits 1.
- Every run starts with a fresh profile (empty localStorage): a stateful flow goes into one `<js>`.
- Full page, capped at 2400 px tall. Each image costs context: shoot the states that changed.
