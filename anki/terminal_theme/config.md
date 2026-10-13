## Terminal Theme

Ghostty (Ayu dark) + tmux look for Anki. Restart Anki after changing anything
here.

- `status_bar` - tmux-style bar at the bottom of the reviewer (deck, queue
  counts, clock).
- `font_family` - primary font. Falls back to
  `JetBrains Mono, Menlo, monospace` when missing.
- `font_size` - base size in pixels.
- `qt_styling` - also restyle native Qt windows (Browse, Add, Preferences).
  Off by default: it touches the application-wide stylesheet.

The palette lives in `web/theme.css` (`:root` block). Edit it there, nothing
else hardcodes colors.
