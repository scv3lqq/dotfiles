# Built-in display guard (macOS)

Status: implemented 2026-11-15 on macOS 26 (Darwin 25.5), Apple Silicon.

## Current behavior

BetterDisplay (trial Pro, `disconnectBuiltInOnExternal`) kept the MacBook
built-in display disconnected while an external monitor was attached. It was
uninstalled and its cask removed from `install.sh` (revert of `e83efcc`), so
the built-in now stays on next to the external monitor.

## Goal

A small own tool, `builtin-display`, that disconnects the built-in display
whenever an external display is active and reconnects it when none is, run by
a launchd agent. Non-goals: brightness, mirroring, Intel Macs, Linux.

## API research

macOS has no public call for this. The private SkyLight function
`SLSConfigureDisplayEnabled(CGDisplayConfigRef, CGDirectDisplayID, bool) ->
CGError`, called inside `CGBeginDisplayConfiguration` /
`CGCompleteDisplayConfiguration`, performs a real disconnect on Apple Silicon
(macOS 13+). A disabled display drops out of `CGGetActiveDisplayList` and
`CGGetOnlineDisplayList`; `SLSGetDisplayList` still lists it, which is how
`on` finds the built-in ID again.

- https://github.com/calvincchan/displaytoggle (signatures in
  `Sources/displaytoggle/SkyLightBridge.h`, Apple Silicon only, macOS 13+)
- https://github.com/jonpurdy/display-disabler (the `CGSConfigureDisplayEnabled`
  alias, macOS 15 target)
- https://alinpanaitiu.com/blog/turn-off-macbook-display-clamshell/ (Lunar
  BlackOut, the original reverse engineering)
- https://github.com/waydabber/betterdisplay/issues/1433 (Intel: disconnect
  works one way only, reconnect needs the lid)

Verified here on 2026-11-15: `off`, `on` and `watch` work, `aerospace
list-monitors` goes from two monitors to Mi Monitor only and back.

## Design

- `builtin-display/builtin-display.swift`: single-file Swift CLI, compiled with
  `swiftc -O`. Symbols are resolved with `dlopen`/`dlsym`, so a macOS release
  without them fails with a message (exit 2), not a dyld crash.
- Commands: `status`, `on`, `off` (refuses without an active external
  display), `watch`.
- The transaction commits with `.forSession`, not `.permanently`: logout or
  reboot always brings the built-in back, so a dead agent cannot strand it.
- `watch`: `CGDisplayRegisterReconfigurationCallback` on the main run loop,
  debounced 1 s, plus a 30 s reconcile timer for missed callbacks. Desired
  state: built-in off while any non-built-in display is active, on otherwise.
  An attempt is not repeated for the same display set, so a no-op action
  (lid closed) cannot loop. SIGTERM, SIGINT, SIGHUP re-enable the built-in
  before exit.
- Binary: `~/.local/bin/builtin-display` (already on PATH via `zsh/.zprofile`).
  `install.sh` builds it on macOS when `swiftc` exists.
- Agent: `~/Library/LaunchAgents/local.builtin-display.plist`, outside the
  repo like `local.topgrade`; `RunAtLoad` + `KeepAlive`, log
  `~/Library/Logs/builtin-display.log`. README carries the heredoc to recreate
  it.

## Edge cases

- Lid closed with external: macOS clamshell already removes the built-in; the
  watcher sees no active built-in and does nothing.
- External unplugged while built-in off: active list becomes empty, the
  watcher reconnects the built-in within ~1 s (30 s worst case).
- Reboot / logout: `.forSession` resets to on; the agent starts at login and
  disconnects again if the external is present.
- Sleep/wake: reconfiguration callbacks fire on wake; the 30 s timer covers a
  missed one.
- Agent stopped (`bootout`) or crashed: SIGTERM handler reconnects; a crash
  leaves the built-in off until the external is unplugged, lid cycled, or
  `builtin-display on` is run; KeepAlive restarts the agent anyway.
- Linux or no `swiftc` (no Xcode CLT): `install.sh` skips the build with a
  message.
- Dirty worktree: only the files below are staged, by explicit pathspec.

## Files

- `builtin-display/builtin-display.swift` (new)
- `install.sh`: macOS-only build step
- `README.md`: layout row and agent section
- this plan

## Operate

- State: `builtin-display status`
- Manual: `builtin-display on` / `builtin-display off`
- Inspect: `launchctl print gui/$(id -u)/local.builtin-display`
- Restart: `launchctl kickstart -k gui/$(id -u)/local.builtin-display`
- Stop (reconnects the built-in): `launchctl bootout gui/$(id -u)/local.builtin-display`
- Start: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.builtin-display.plist`

## Rollback

`launchctl bootout gui/$(id -u)/local.builtin-display`, remove the plist and
`~/.local/bin/builtin-display`, revert the commit.
