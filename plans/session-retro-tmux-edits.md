# Session retrospective: exact tmux guidance edits

Companion to `plans/session-retro-efficiency.md`, task T1, base `946be62`.
Only `.claude/rules/tmux.md` is changed by this block.

**E1.** (lines 27-34)

````md E1-old
- A popup is invisible to `capture-pane`. To see its fill or timing, attach
  a `-L` server client from a python3 `pty.fork()` and parse the client's
  output (`48;2;R;G;Bm` = popup background), or run the command inside the
  popup through a relaying pty that logs timestamps. fzf sends `\e[6n` and
  DECRQM on start and waits ~0.5 s for replies, so a bare pty without tmux
  overstates its startup. A flash before the first frame is `popup-style`.
- A copied `/bin/bash` (fake `pane_current_command`) is SIGKILLed on macOS
  until `codesign -s - -f <copy>`.
````

````md E1-new
- A popup is invisible to `capture-pane`. To see its fill or timing, attach
  a `-L` server client from a python3 `pty.fork()` and parse the client's
  output (`48;2;R;G;Bm` = popup background), or run the command inside the
  popup through a relaying pty that logs timestamps. fzf sends `\e[6n` and
  DECRQM on start and waits ~0.5 s for replies, so a bare pty without tmux
  overstates its startup. A flash before the first frame is `popup-style`.
  Set the slave PTY dimensions with `TIOCSWINSZ` before attaching the client.
  Use short unique fixture titles and verify the selected pane ID: narrow list
  columns can clip a title without a rendering or navigation failure.
- A copied executable (fake `pane_current_command`) needs
  `codesign -s - -f <copy>` on macOS. For system binaries use `shutil.copyfile`
  plus explicit executable permissions; `copy2` can fail while copying protected
  file flags through `chflags`.
````

