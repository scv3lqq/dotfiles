# Terminal card templates

Card styling in the same palette as `anki/terminal_theme`. Standalone: works on
AnkiDroid with no add-on installed, because `cards.css` carries its own copy of
the palette.

## Files

- `cards.css` - paste into the note type's **Styling** box.
- `front.html` - paste into the **Front Template**.
- `back.html` - paste into the **Back Template**.

## Where to paste

Your existing note types are not modified. Clone one first:

1. Tools > Manage Note Types > Add > Clone: Basic, name it e.g.
   `Basic (terminal)`.
2. Select it > Cards.
3. Front Template: replace the contents with `front.html`.
4. Back Template: replace the contents with `back.html`.
5. Styling: replace the contents with `cards.css`.
6. Save, then switch the notes you want over with Browse > select >
   Notes > Change Note Type.

The templates assume fields named `Front` and `Back`. For a different note type
rename the `{{Front}}` / `{{Back}}` references; the CSS classes stay the same.

## What it looks like

```
❯ what does `set -o pipefail` do?█

❯ what does `set -o pipefail` do?
  │ the pipeline returns the first non-zero exit status
❯ █
# shell tags
```

- `.tt-prompt` - the `❯` before the question, cyan.
- `.tt-cursor` - blinking block cursor, `#E6B450`. Remove the
  `animation` line in `.tt-cursor` to make it solid.
- `.tt-output` - the answer, rendered like command output behind a left rule.
- `.tt-comment` - tags line, hidden when the note has no tags.

## Notes

- `hr#answer` is hidden: the second prompt line already separates the two
  sides.
- Type-in answers (`{{type:Back}}`) are styled; add the field to `front.html`
  inside the `.tt-line` if you use them.
- The font falls back to `JetBrains Mono, DejaVu Sans Mono, Menlo, monospace`.
  On AnkiDroid install the font into the collection (`_JetBrainsMono.ttf` in
  `collection.media`) and add an `@font-face` rule if you want an exact match.
