---
name: readme-screenshots
description: Retake or add the README screenshots in assets/screenshots/ (AeroSpace layout, Neovim, tmux session picker, Yazi) from a made-up demo scene, so nothing real reaches the public repo. Use for "пересними скриншоты", "обнови скрины в README", "добавь скрин <tool>", after a config change that alters the look. Drives the real screen (AeroSpace workspace 5) for about a minute.
---

# README screenshots from a demo scene

Design, shot list and acceptance criteria: `plans/readme-screenshots.md`.
Scripts (verified 2026-10-25) in `scripts/`; they expect this layout under a
scratch dir `$S` (never inside the repo):

```
$S/run/{capture.zsh,fixtures.zsh,ocr.swift,zsh_history}   bin/ocr
$S/spike/{winbounds.swift,claude.c}   bin/{winbounds,claude}   GhosttyDemo.app
```

## Steps

1. Preflight: `~/code` must not exist, AeroSpace workspace 5 empty, the
   built-in Retina display on (lid open). Tell the user focus will jump to
   workspace 5 for about a minute and not to type meanwhile.
2. Stage and build (`K` = this skill's `scripts/`):
   ```zsh
   mkdir -p $S/run/bin $S/spike/bin
   cp $K/{capture.zsh,fixtures.zsh,ocr.swift,zsh_history} $S/run/
   cp $K/{winbounds.swift,claude.c} $S/spike/
   swiftc -O -o $S/run/bin/ocr $S/run/ocr.swift
   swiftc -O -o $S/spike/bin/winbounds $S/spike/winbounds.swift
   cc -O2 -o $S/spike/bin/claude $S/spike/claude.c
   A=$S/spike/GhosttyDemo.app
   ditto --noextattr /Applications/Ghostty.app $A
   /usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier com.mitchellh.ghostty.demo' $A/Contents/Info.plist
   codesign --force --deep --sign - $A
   ```
3. Leak list, kept in `$S` only (never commit it):
   ```zsh
   { print -l -- $USER ${=$(git -C ~/dotfiles config user.name)} \
       ${${$(git -C ~/dotfiles remote get-url origin)#*:}%%/*} \
       /users/ /private scratchpad claude-501 dotfiles-demo
     scutil --get LocalHostName; scutil --get ComputerName; } >$S/run/forbidden.txt
   ```
   Entries shorter than 5 chars false-match (`roma` hit `Chromaticity` in
   `magick identify`): drop them or check them with `grep -w`.
4. Content changes (new shot, other demo code) go into `fixtures.zsh` /
   `capture.zsh` first; keep shown files at most 70 columns.
5. `$S/run/fixtures.zsh && $S/run/capture.zsh`. Cleanup (EXIT trap) moves
   `~/code` to `$S/run/code.<epoch>`; rerun `fixtures.zsh` before a retake.
6. Gates: plan acceptance criteria 1-6 and 10 with `$S` set, then Read every
   PNG: only demo content, no stray typed text. Commit only the PNGs that
   changed, by explicit pathspec.

## Gotchas (each cost a rerun or touched real state)

- Never launch the real Ghostty with CLI flags for this:
  `--window-save-state=never` writes `NSQuitAlwaysKeepsWindows=0` into the
  shared `com.mitchellh.ghostty` defaults and a second instance resizes the
  user's tiles. The clone has its own bundle id and defaults domain.
- The demo tmux server never loads `~/.tmux.conf` or TPM: continuum would
  restore real sessions into it and autosave demo ones over the real save;
  tmux-assistant-resurrect rewrites `~/.claude/settings.json`.
- Workspace 9 is force-assigned to the external monitor; 5 lives on Retina.
- Type into panes only after the client attached and the layout reached its
  final size: earlier input wraps, and tab-aligned output (`go test`) loses
  its alignment on reflow.
- The picker sorts sessions by name: select rows with `pos(N)` over
  `fzf --listen`, not `first`. `send-keys -K` opens the popup but cannot
  drive fzf.
- A copied `/bin/sleep` as the fake `claude` gets SIGKILL; use `claude.c`.
- `sips -c <h> <w> --cropOffset <y> <x>` whose box reaches the image edge
  returns the image uncropped without an error; use `magick -crop`.
- zsh history: panes run ` fc -p $DEMO_HIST` (leading space), so nothing
  reaches `~/.zsh_history` and autosuggestions show only demo lines.
