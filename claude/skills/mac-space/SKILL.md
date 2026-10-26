---
name: mac-space
description: Audit what takes disk space and RAM on this Mac, then delete or shrink what the user picks (VM images, colima/docker, caches, Chrome code_sign_clone). Use for «что много весит», «что занимает память», «мало места на диске», «почисти диск», «почему swap», «аудит диска/памяти». Not malware (mac-audit), not closing panes only (tmux-cleanup).
argument-hint: "[ram|disk]"
allowed-tools: Bash(bash ~/.claude/skills/mac-space/audit.sh:*), Bash(du:*), Bash(df:*)
---

# mac-space

1. Audit, read-only, one call (timeout 300000, disk part ~100 s): `bash ~/.claude/skills/mac-space/audit.sh [ram|disk]`. Post one status line before it.
2. Drill only into a block over ~5G the output does not explain: `du -xhd1 <dir> | sort -rh | head -15`.
3. Report: a disk table and a RAM table (what, size, one-line comment: age, running or not, re-downloadable or not), then "ничего не удалял" and the candidates. Delete nothing before the user names it.

## Reading the numbers
- RAM: the script uses top MEM (physical footprint), ps RSS undercounts it. Every Claude CLI session spawns its own stdio MCP servers (the `node` row), so idle sessions are the cheapest win: `/tmux-cleanup`.
- `/private/var` is large without sudo: it is the user's own `/var/folders/<xx>/<id>/X`, the `zz` dirs read as 0.
- Chrome `.../X/com.google.Chrome.code_sign_clone/code_sign_clone.*`: one APFS clone of Chrome.app per launch, left behind when Chrome is killed (headless/CDP). Clones of the installed version share blocks, so du overcounts and deleting frees ~0. Clones of an older version hold ~1.5G each. Delete only while Chrome is closed (`pgrep -x 'Google Chrome'`). Leak source: headless launches without `--disable-features=MacAppCodeSignClone` (page-shot has it).
- `/Applications` and the script's sums can exceed the volume's used space: clones and hard links are counted twice.

## Cleanup recipes (only what the user named)
- Measure `df -g /System/Volumes/Data` before and after each item, report the real gain.
- VM bundles (`~/Parallels/*.macvm|*.pvm`, UTM `~/Library/Containers/com.utmapp.UTM/Data/Documents/*.utm`): check `pgrep -x prl_vm_app prl_macvm_app UTM QEMULauncher` is empty, then `rm -rf` the bundle. The apps stay unless asked.
- Colima "почистить": `colima start`, inspect `docker system df`, `docker ps -a`, volume sizes (`docker system df -v`).
  - Remove: images no container uses, by ref (`docker ps -aq | xargs docker inspect -f '{{.Image}}'` gives used `sha256:` IDs, match them against `docker images --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}'`), build cache (`docker builder prune -af`: the user asked, so the CLAUDE.md prune ban, which covers my own leftovers, does not apply), empty (0B) dangling volumes.
  - Keep: containers, named volumes. Non-empty dangling volumes: inspect with an image already present, so nothing gets pulled (`docker run --rm -v <vol>:/v postgres sh -c 'cat /v/PG_VERSION; ls /v; du -sh /v/base/*'`), and ask.
  - Host space comes back only after `colima ssh -- sudo fstrim -av` (diffdisk is sparse). Then `colima stop` if it was stopped.
- Claude.app `vm_bundles` (Cowork VM) is recreated on next use: deleting it is a temporary gain.
