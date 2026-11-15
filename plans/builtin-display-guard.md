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
  display), `watch`, `selftest` (decision table, no display access).
- The transaction commits with `.forSession`, not `.permanently`: logout or
  reboot always brings the built-in back, so a dead agent cannot strand it.
- `watch`: `CGDisplayRegisterReconfigurationCallback` serviced by an
  `NSApplication` run loop (activation policy `.prohibited`), debounced 1 s,
  plus a 2 s poll and an `IORegisterForSystemPower` wake hook. Every callback
  (display, flags) and every change of the display snapshot is logged.
- Decision (`decide`): built-in off while a real external is active, on
  otherwise. Real external: not built-in, active, EDID size > 0, vendor not
  `0`, `0xFFFFFFFF` or `'unkn'`. While the built-in is off, an external also
  has to be one seen while the built-in was on (trusted set), so a display
  that appears after the last real one left never counts, whatever it reports.
- An attempt is not repeated for the same snapshot, so a no-op action (lid
  closed) cannot loop. SIGTERM, SIGINT, SIGHUP re-enable the built-in before
  exit.

## Unplug bug (fixed 2026-11-15)

First version: unplugging the monitor left the built-in dark, the log had
nothing between the disable and the manual stop. Two causes:

1. WindowServer activates a placeholder when the last real display goes
   away. Unified log at the unplug: `Display 2 hot plug 0`, then
   `VirtualDisplay::set_display_state display_id=3 ... target_state=on`,
   `display 0x3 added ... marking main`, `display 0x2 removed`. The old rule
   counted any active non-built-in display as external, so display 3 kept the
   built-in off. BetterDisplay hits the same placeholder:
   https://github.com/waydabber/betterdisplay/issues/5913
2. `CFRunLoopRun` in a plain CLI never receives WindowServer display
   notifications: after an `on` from another process the watcher logged no
   callback and its poll read a stale display list for 5 s, until its own
   SIGTERM handler called `CGBeginDisplayConfiguration`, which flushed the
   queued callbacks. The same binary on an `NSApplication` run loop logged the
   callback within 1 s and reacted.

Second unplug test (16:44:41) still left it dark: the snapshot was only
`4:virtual:on:v756e6b6e:677mm`. With only the placeholder up, the disabled
built-in is in no list (SkyLight's included) and `CGDisplayIsBuiltin` is
false for an absent ID, so `decide` hit its "no built-in" guard and returned
`none`. Fix: the built-in ID is learned while visible and stored in
`~/Library/Application Support/builtin-display/builtin-id`; `decide` takes
that ID and never needs the built-in in the snapshot; enable goes straight to
`SLSConfigureDisplayEnabled(stored ID, true)` and is retried on every 2 s
poll, each attempt logged with its CGError (disable keeps the no-repeat rule).
Open question: for an ID WindowServer does not know, `SLSConfigureDisplayEnabled`
returns 0 and `CGCompleteDisplayConfiguration` returns 1001 (probe with ID 99);
whether a known but unlisted built-in commits is only provable by a real
unplug. If the log shows `enable 1: ... CGError 1001`, enabling while absent
is impossible and the fallback is the lid cycle.

Checked: `selftest` (18 cases, the logged unplug state included); live, an
external `builtin-display on` is logged and reverted within 1 to 2 s;
`kickstart -k` restores and re-disables. A real unplug cannot be simulated
safely here (disabling the external would leave no display), so it stays a
manual test.
- Binary: `~/.local/bin/builtin-display` (already on PATH via `zsh/.zprofile`).
  `install.sh` builds it on macOS when `swiftc` exists.
- Agent: `~/Library/LaunchAgents/local.builtin-display.plist`, outside the
  repo like `local.topgrade`; `RunAtLoad` + `KeepAlive`, log
  `~/Library/Logs/builtin-display.log`. README carries the heredoc to recreate
  it.

## Edge cases

- Lid closed with external: macOS clamshell already removes the built-in; the
  watcher sees no active built-in and does nothing.
- External unplugged while built-in off: WindowServer's placeholder becomes
  the only active display; it is not a trusted real external, so the watcher
  reconnects the built-in within ~1 s (2 s poll worst case).
- Reboot / logout: `.forSession` resets to on; the agent starts at login and
  disconnects again if the external is present.
- Sleep/wake: the wake hook re-evaluates 1 s after power-on; the 2 s poll
  covers a missed callback.
- Monitor plugged in while the built-in is off (another monitor): not
  trusted yet, so one on/off flicker.
- Manual `builtin-display on` while the agent runs is reverted; stop the agent
  first.
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
