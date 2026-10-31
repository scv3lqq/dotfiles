# ChatGPT Ayu desktop theme

## Goal and current behavior

Provide a native desktop theme import matching Ghostty, Telegram and Zen.
The repository currently documents desktop colors but has no import preset.
Desktop UI control is denied by the runtime; preparing an import must not bypass
that restriction. Applying it and visually verifying it remain user steps.

## Research and design

- Ghostty uses background #0B0E14 and foreground #E8E6DD; Telegram uses
  accent #D2A6FF. Zen uses the same Ayu family with restrained surfaces.
- [OpenAI settings](https://learn.chatgpt.com/docs/reference/settings) exposes
  theme import, colors, contrast, UI/code fonts and sidebar translucency.
- [Linear](https://linear.app/now/behind-the-latest-design-refresh) favors
  quiet navigation and subtle structure. [Vercel](https://vercel.com/geist/colors)
  uses restrained surface steps; [Stripe](https://docs.stripe.com/stripe-apps/design)
  prioritizes contrast and consistent native components.
- The installed app's public shipped import schema requires the prefix
  codex-theme-v1: followed by JSON. The dark syntax preset ID is ayu.
- Choose native UI/content typography for reading, JetBrainsMono Nerd Font
  for code, contrast 55 and opaque windows for a stable canvas. Built-in layout,
  spacing and font sizes remain native; the import does not expose those controls.

## Shared definitions

The complete import preset is the following single line, with one final newline:

```theme
codex-theme-v1:{"codeThemeId":"ayu","theme":{"accent":"#D2A6FF","accentSource":"custom","contrast":55,"fonts":{"code":"\"JetBrainsMono Nerd Font\", monospace","content":null,"ui":null},"ink":"#E8E6DD","opaqueWindows":true,"semanticColors":{"diffAdded":"#AAD94C","diffRemoved":"#F07178","skill":"#D2A6FF"},"surface":"#0B0E14"},"variant":"dark"}
```

## Acceptance criteria

1. The preset matches the frozen line and parses as JSON with the native prefix.
2. The README states the native import steps, original-theme backup step and the
   fact that the preset has not been applied or visually verified in this session.
3. Only this plan and chatgpt/ayu-terminal-dark.theme and chatgpt/README.md change.
4. Gates pass. No app config, IPC, debugging port or app bundle is modified.

## Gates

- `just check`
- `git diff --check`
- Task gate below.

## Task T1

Own only chatgpt/ayu-terminal-dark.theme and chatgpt/README.md. No dependencies.
Create the preset verbatim from Shared definitions. Add a concise English README
(at most 14 lines) describing palette, native reading fonts and code font.
Document Settings > Appearance > Advanced: first copy/save the existing dark
theme, select Dark, use the dark theme Import button, paste the entire preset
line and submit Import theme. Explain that only the dark preset is imported.
State that application and visual verification remain pending because desktop
control is unavailable. No additional scripts, tests or installer changes.
This is static configuration with no new program behavior.

Task gate (run from repository root):

```bash
python3 - <<'PY'
import json
from pathlib import Path
plan = Path('plans/chatgpt-ayu-theme.md').read_text()
expected = plan.split('```theme\n', 1)[1].split('```', 1)[0]
actual = Path('chatgpt/ayu-terminal-dark.theme').read_text()
assert actual == expected
assert actual.startswith('codex-theme-v1:')
theme = json.loads(actual[15:])
assert theme['variant'] == 'dark' and theme['codeThemeId'] == 'ayu'
readme = Path('chatgpt/README.md').read_text()
for text in ('Appearance', 'Advanced', 'Import', 'Copy', 'not been applied'):
    assert text in readme, text
print('PASS: frozen native import and handoff instructions')
PY
```

Definition of done: task gate passes, scoped files only, independent review
confirms shipped schema compatibility. UI acceptance remains explicitly unverified.

## Seams

One task; preset path in README must resolve to ayu-terminal-dark.theme.

## Edge cases

- macOS desktop is the requested target; Linux and CLI setup remain unchanged.
- No GUI access: provide import, never claim the theme was applied.
- Missing code font: CSS monospace fallback remains available.
- First run: native importer applies a dark preset; user selects Dark explicitly.
- Dirty checkout: preserve unrelated work; initial tracked checkout was clean.
- No external live file changes are authorized by this plan, so no live backup
  is created. README instructs copying the original theme before import.

## Baseline

- Base b383320: just check passed (47 setup/plugin tests, four plan tests and
  shell/config gates); git diff --check passed on the clean checkout.
- Task gate is red before implementation: chatgpt/ayu-terminal-dark.theme absent.
- Checkout wait returned free after two checks before creating the feature branch.

## Not doing

No app bundle patches, undocumented storage edits, live IPC, browser themes,
GUI automation bypass, app restart, installer changes or unrelated documentation.
