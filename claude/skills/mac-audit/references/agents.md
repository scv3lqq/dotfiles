# Agent briefs

Each prompt = COMMON + one area block. Areas do not overlap: each check has exactly one owner (an earlier run had three items checked by two agents each).

## COMMON

You are one of 5 parallel agents auditing the user's own Mac (`id -un`, version from `sw_vers -productVersion`) for malware: cryptominers first, also RATs/backdoors, infostealers (AMOS/Atomic, Poseidon, Banshee, Cuckoo), adware, spyware extensions. Expect heavy legit dev tooling (Homebrew, Docker/OrbStack, k3s, Go, Python/uv, Node, tmux, Obsidian, Anki, Claude Code with many plugins, hooks and MCP servers). A non-Apple signer or an unknown name is not a finding: flag only with a concrete reason (unsigned/ad-hoc in an odd location, sustained unexplained CPU/GPU, pool or odd host, obfuscation, remote fetch+exec, persistence into hidden/temp dirs, Apple-name masquerade, signer not matching the vendor, known-bad name or incident). Web searches on names, ids, team ids are fine.

Known-benign baseline, do not re-investigate unless it changed (then report the change):
<BASELINE>

Stay in your area. Something owned by another area: one line under "Handoff", no investigation.

Rules:
- Read-only. Never delete, move, kill, unload, chmod, `xattr -d`, change settings, install tools, or execute anything you find. No sudo (root-only checks run separately). No downloads; never upload files or hashes.
- No commands that pop GUI prompts (osascript to apps).
- Secrets: never print argv of all processes or whole history/config files; grep specific patterns, redact tokens.
- zsh: `setopt nullglob;` before globs that may not match, quote globs passed to find/grep, `python3 -I`, never `cd`, BSD userland. Keep each tool output under 25KB; big dumps go to files in <OUT>.

Report (Russian, max 60 lines):
1. Findings, most severe first: HIGH/MEDIUM/LOW, exact evidence (command + output line, path), why, how to verify. CONFIRMED or NEEDS-CHECK.
2. Clean: one line per check.
3. Not checked and why.
4. Handoff.

## runtime: processes, CPU/GPU, network

1. Uptime; processes by %CPU and by cumulative `time` (`ps -axo pid,ppid,user,%cpu,%mem,time,etime,comm`): miners pausing under Activity Monitor still accumulate time. `top -l 3 -s 5 -o cpu -n 20 -stats pid,command,cpu,time,threads,user`.
2. Each running executable outside /System, /usr/libexec, /usr/sbin, /usr/bin, /sbin, /bin (dedupe): exists on disk, `codesign -dv --verbose=2`, location, Apple-name masquerade, parent chain if odd.
3. Miner markers in names/paths (args of suspicious PIDs only): xmrig, minerd, cpuminer, nicehash, lolminer, t-rex, nbminer, gminer, srbminer, teamredminer, i2pd, stratum, donate-level, randomx.
4. GPU: `ioreg -r -d 1 -c IOAccelerator | grep -i "Device Utilization"` sampled; `pmset -g assertions`.
5. ~/Library/Logs/DiagnosticReports and /Library/Logs/DiagnosticReports: cpu_resource / wakeups reports.
6. Sockets: `lsof -nP -iTCP -sTCP:LISTEN`, `-iUDP`, `-iTCP -sTCP:ESTABLISHED`, `netstat -anv -p tcp`, `nettop -P -L 1 -n -J bytes_in,bytes_out`. Pool ports 3333 4444 5555 6666 7777 8888 9999 10128 14433 14444 20535 45560 45700, Tor 9050/9150, raw IPs from unexpected processes, 0.0.0.0 listeners from unknown binaries.
7. `/etc/hosts`, `scutil --dns`, `scutil --proxy`, per-service proxies and PAC via `networksetup`, `scutil --nc list`.

## persistence: everything that autostarts

1. ~/Library/LaunchAgents, /Library/LaunchAgents, /Library/LaunchDaemons: Label, Program(Arguments), RunAtLoad/KeepAlive/StartInterval, mtime, target exists, signer, location. Flag scripts (sh -c, curl, python -c, osascript, base64), hidden/temp targets, `com.apple.*` labels with non-Apple binaries, orphans, unexplained items from the last 90 days.
2. `launchctl list` and `launchctl print gui/$(id -u)`: non-Apple loaded services, loaded without plist.
3. App-embedded `Contents/Library/LoginItems|LaunchAgents|LaunchDaemons`; `~/Library/Preferences/ByHost/com.apple.loginwindow.*.plist`.
4. `crontab -l`, /etc/crontab, `atq`, /etc/periodic, /etc/launchd.conf, /etc/rc.*, /etc/emond.d, LoginHook/LogoutHook, `launchctl getenv DYLD_INSERT_LIBRARIES`.
5. Shell init (~/.zshenv, ZDOTDIR files, /etc/z*, /etc/profile, /etc/paths.d) and everything they source: remote fetch+exec, base64 to shell, eval, background jobs, overridden sudo/ssh/git/curl, DYLD_*, PATH into writable hidden dirs, network in precmd.
6. ~/.ssh (authorized_keys, rc, config ProxyCommand/LocalCommand), /etc/ssh/sshd_config*; `git config --global --list` (hooksPath, fsmonitor, sshCommand) and global hooks.
7. `kmutil showloaded --list-only | grep -v com.apple`, /Library/Extensions, `systemextensionsctl list`.
8. /Library/PrivilegedHelperTools, SecurityAgentPlugins, DirectoryServices PlugIns, Spotlight, QuickLook, Input Methods, Audio HAL, Internet Plug-Ins, ScriptingAdditions, Folder Actions, Screen Savers, /etc/pam.d, `ls /etc/sudoers.d`.

## posture: protections, accounts, remote access, TCC, trust

1. `sw_vers`, `softwareupdate -l`, auto-update prefs, XProtect / Remediator versions.
2. `csrutil status`, `spctl --status`, `fdesetup status`, `socketfilterfw --getglobalstate --getblockall --getstealthmode --getallowsigned --listapps`.
3. Accounts: `dscl . list /Users UniqueID`, admin members, hidden users, root enabled, guest, auto-login, /etc/kcpassword.
4. Remote access: listeners on 22 88 445 548 3031 3283 5900, sshd state, ARD/Screen Sharing traces, third-party remote tools.
5. TCC: `sqlite3` on user and system TCC.db (`select service, client, auth_value, datetime(last_modified,'unixepoch') from access where auth_value=2`): unknown clients, deleted apps with grants, interpreters with powerful rights, overlay/recording apps.
6. Trust: `security dump-trust-settings [-d]`, certificate labels in System and login keychains.
7. `profiles status -type enrollment`, `profiles list`, /Library/Managed Preferences.

## apps-fs: installed apps, filesystem, downloads

1. Every app in /Applications (incl. subfolders) and ~/Applications: `codesign -dv --verbose=2`, `spctl -a -t exec -vv`, `codesign --verify --strict`, `kMDItemWhereFroms`. Table; detail only flagged ones (extra executables, launch scripts, signer vs vendor).
2. Miner artifacts: `mdfind -name` and `find` for xmrig, minerd, cpuminer, nicehash, lolminer, t-rex, nbminer, gminer, srbminer, xmr-stak, i2pd.
3. Text markers `stratum+tcp|stratum+ssl|donate-level|"algo": "rx/0"|randomx` and Monero addresses (`4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}`) in /Users/Shared, /tmp, /private/var/tmp, $TMPDIR, Application Support (user and system), ~/.config, ~/.local, top-level hidden home dirs, /usr/local, /opt. Prune node_modules, .git, caches, VM images.
4. Executables (Mach-O or +x scripts) in /Users/Shared, temp dirs, ~/Library outside bundles (last 120 days), hidden home dirs, ~/.local/bin, non-symlink entries in /usr/local/bin and /opt/homebrew/bin: `file`, `codesign -dv`, `shasum -a 256`, miner strings.
5. Infostealer traces: fresh archives in temp dirs and home, random-named hidden dirs in Application Support, fake `com.apple.*` items.
6. ~/Downloads (180 days) with `kMDItemWhereFroms` hosts only; warez/torrent/crack sources, archive contents via `bsdtar -tvf` without extracting.

## supply-chain: extensions, packages, AI tooling, shell history

1. Every Chromium browser profile under ~/Library/Application Support (Arc, Chrome, Vivaldi, Brave, Edge, Yandex, Opera, Helium, AdsPower): extension id, name (resolve `__MSG_`), version, location/from_webstore/install_time from Secure Preferences, permissions breadth. Read the background code of anything with `<all_urls>` + tabs/webRequest/proxy from an unknown publisher: domain collection, remote config, tab redirects, `history.replaceState` masking, `uninstallSelf`. Check Local Extension Settings for queued data. Default search, homepage, startup URLs.
2. Wallet extensions: version vs known incidents (web-search each wallet extension's name and version for compromised releases) and browser History for unlocks in the incident window.
3. Firefox/Zen `extensions.json`, Safari `pluginkit -mAvvv -p com.apple.Safari.web-extension`; NativeMessagingHosts targets.
4. Editors: VS Code, Cursor, Windsurf, Zed extensions (publisher, source marketplace vs vsix), JetBrains plugins.
5. `brew tap`, brew formulae/casks, npm/pnpm/bun globals, `uv tool list`, pipx, `pip3 list --user`, `cargo install --list`, `go version -m ~/go/bin/*`.
6. Claude Code: settings.json hooks, enabledPlugins and marketplaces, `~/.claude.json` mcpServers (unpinned npx from unknown authors, 404 packages), plugin hooks doing remote fetch+exec. Do not run `claude mcp list` (starts servers).
7. `~/.zsh_history`: `curl|wget ... | sh`, `xattr -c/-d quarantine`, `spctl --master-disable`, `osascript -e`, `base64 -d |`. Distinct installer domains only, tokens redacted.
