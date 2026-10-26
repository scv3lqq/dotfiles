---
name: mac-audit
description: Audit this Mac for malware (cryptominers, RATs, infostealers, adware, spyware browser extensions, risky TCC grants) with 5 parallel read-only agents plus one sudo tmux window, verify findings, then remove what the user approves (incl. Chromium/Arc extensions offline). Use for «проверь мак на вирусы / майнеры», «аудит безопасности macOS», «нет ли малвари».
argument-hint: "[focus area, optional]"
---

# macOS malware audit

Last full run: 2026-10-25 (about 750k subagent tokens, 13 min wall clock). Read-only until the user approves removals.

## 1. Launch (one message)

- Five agents from `references/agents.md` (COMMON + area block each, `subagent_type: general-purpose`), all in one message. Replace `<OUT>` with `<scratchpad>/audit/<area>` and paste `~/.claude/private/mac-audit-baseline.md` into `<BASELINE>` (the word `none` when that file is missing).
- Same message: `tmux new-window -n sudo-audit "zsh ~/.claude/skills/mac-audit/scripts/sudo-checks.zsh <scratchpad>/audit/sudo"`, then a background wait: `until [ -f <dir>/DONE ]; do sleep 5; done`. Tell the user to type the password in that window.
- When DONE: `python3 -I ~/.claude/skills/mac-audit/scripts/summarize-sudo.py <scratchpad>/audit/sudo` (BTM login items, powermetrics top CPU/GPU, all-user sockets, deleted-but-running binaries, root cron/sudoers/profiles). Do not hand-parse the raw files.

## 2. Verify before reporting

- Every HIGH/MEDIUM: check it yourself (read the extension/script code, `codesign -dv`, web-check a claimed incident or CVE). Do not repeat an unverified CVE number.
- Spyware extension: check whether its servers still resolve via DoH (`curl -s -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=<host>&type=A'`); `dig` may return fake-IP answers (198.18.x) behind a local proxy or VPN client.
- Report: verdict line, numbered findings (severity, evidence, action), "проверь сам", short clean list, then one numbered list of steps only the user can do.

## 3. Remediation (after approval)

- Chromium/Arc extension: never launch the browser while a phoning-home extension is enabled. With the browser closed: `python3 -I ~/.claude/skills/mac-audit/scripts/remove_chromium_ext.py "<User Data dir>" <ProcessName> ~/Backups/<browser>-extensions-<date> <ext_id>...` (moves data dirs to the backup, drops `extensions.settings`, its MACs and `updateclientdata`). Then `open -g -a <Browser>`, wait ~30 s, confirm the ids are absent from `Default/Secure Preferences`, `kill -TERM` the browser. Arc honors this; a wallet extension's vault lives in the backup, say so.
- TCC: `tccutil reset All <bundle_id>` works without sudo for both TCC dbs, but only while the app is still installed (error -10814 once deleted). Reset first, then trash. Leftover grants of a deleted app: System Settings, "−" (inert, bound to the app's signature).
- Trash with `mv` into `~/.Trash/audit-<date>/<parent>/`: same-named dirs from Caches/WebKit/Logs collide.

## Baseline

Known-benign items of this Mac live in `~/.claude/private/mac-audit-baseline.md`, outside the
public dotfiles repo. After the run update that file: add what the user confirmed benign.

## Limits

- macOS 26 QuarantineEventsV2 has no URLs: use `mdls -raw -name kMDItemWhereFroms`.
- DiagnosticReports rotate after about a week.
- `sfltool dumpbtm`, `powermetrics`, root sockets, `lsof +L1`, root cron, sudoers: sudo script only.
