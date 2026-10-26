---
name: git-history-rewrite
description: Safely rewrite pushed git history (fix author/committer identity, sign old commits for GitHub Verified, drop a file, edit old messages) with a backup, a stash of the dirty worktree, verification that trees are unchanged, and force-with-lease. Use for "не тот автор коммитов", wrong user.email in old commits, "убери файл из истории", "подпиши коммиты / перезапиши с подписью", or any filter-branch / force-push task.
---

# Rewriting pushed history

Destructive and needs an explicit ask (`~/.claude/CLAUDE.md`: never force-push or rewrite
history unless told to). Confirm scope first: how many commits, which branch, is the repo
cloned anywhere else.

## 0. Re-read state, do not trust earlier snapshots

The session-start git status and any `git log` from earlier in the conversation go stale:
another Claude session can commit into the same repo mid-task.

```bash
git -C <repo> rev-parse HEAD && git -C <repo> status --short && git -C <repo> log --format='%h %an <%ae> %ad %s' --date=short -5
```

Count what is actually wrong before proposing a scope:

```bash
git log --format='%ae|%ce' | sort | uniq -c
```

## 1. Fix the cause first

A wrong author almost always comes from repo-local config overriding the global one:

```bash
git config --show-origin --get-all user.email   # file:.git/config wins over file:~/.gitconfig
git config user.email <address>                 # repo-local, applies to future commits
```

## 2. Backup

```bash
ts=$(date +%Y%m%d-%H%M%S)
git bundle create ~/.claude/backups/<repo>-pre-rewrite-$ts.bundle --all
git rev-parse HEAD > ~/.claude/backups/<repo>-pre-rewrite-$ts.head
```

Backups live in `~/.claude/backups/`, never inside the repo. Restore: `git fetch <bundle> main`.

## 3. Park the dirty worktree

filter-branch refuses to run with unstaged changes, and uncommitted work must survive:

```bash
git stash push -u -m "history-rewrite"
```

## 4. Rewrite

Identity, keeping author and commit dates:

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter '
case "$GIT_AUTHOR_EMAIL" in
  old@one|old@two)
    GIT_AUTHOR_NAME="<Name>"; GIT_AUTHOR_EMAIL="<address>"
    export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL ;;
esac
case "$GIT_COMMITTER_EMAIL" in
  old@one|old@two)
    GIT_COMMITTER_NAME="<Name>"; GIT_COMMITTER_EMAIL="<address>"
    export GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL ;;
esac
' --tag-name-filter cat -- --branches 2>&1 | tr '\r' '\n' | tail -3
```

Progress goes to stderr as one `\r`-joined line: without `tr '\r' '\n'` a `tail` still
dumps every rewritten commit into context. Same for `git clone`, `brew install`, `npm i`.

Drop a file from history: same shape with `--index-filter 'git rm --cached --ignore-unmatch <path>'`.

Scrub text from every version (home paths, names): work in a fresh clone in the scratchpad,
never in a shared checkout. `git clone -b <branch> <repo> <dir>` (`-b`: a local clone checks
out the source's current branch), copy the repo-local signing config into it, then one pass
that replaces and re-signs; the replacement table lives in a scratchpad script, never in the
repo:

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --tree-filter "python3 <scratch>/scrub.py" \
  --commit-filter 'git commit-tree -S "$@"' -- <branch> 2>&1 | tr '\r' '\n' | tail -1
```

`scrub.py` walks `.` (skip `.git`, links), `bytes.replace` per pair, longest pair first. Verify:
same `rev-list --count`; `git log '--format=%an|%ae|%ad|%cn|%ce|%cd|%B'` shasum equal old vs
new; `%G?` all G; `git log -p --format='COMMIT %h' | grep -c <patterns>` is 0 (plain `log -p`
also prints `Author:` lines); every `+` line of `git diff <old> <new>` holds a replacement.
Push from the clone with `--force-with-lease=<branch>:<old sha> <remote url>`, then move the
shared checkout only when it is clean and still at `<old sha>`: `fetch` + `reset --hard origin/<branch>`.

Sign existing commits (SSH signing configured first: `gpg.format ssh`, `user.signingkey`,
`commit.gpgsign true`, `gpg.ssh.allowedSignersFile`): keeps author and committer dates.

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --commit-filter 'git commit-tree -S "$@"' -- <branch> 2>&1 | tr '\r' '\n' | tail -3
git log --format='%G?' | sort | uniq -c          # all G
```

GitHub shows Verified only if the key is also added as a *signing* key (auth keys do not
count): `gh ssh-key add <key.pub> --type signing` needs scope `admin:ssh_signing_key`
(`gh auth refresh -h github.com -s admin:ssh_signing_key`, browser device flow: run it in
a separate terminal, `!` may hang on "Press Enter"). Confirm after push:
`gh api 'repos/<o>/<r>/commits?sha=<branch>&per_page=100' --jq '.[].commit.verification.verified' | sort | uniq -c`.

## 5. Verify before pushing

```bash
git rev-parse <old-head>^{tree}; git rev-parse HEAD^{tree}   # must be identical
git log --format='%ae|%ce' | sort | uniq -c                  # only the intended identity
git rev-list --count HEAD                                    # same count as before
git stash pop
```

A changed tree hash means the rewrite touched content: reset to the backup and rethink.

## 6. Push and clean up

```bash
git push --force-with-lease origin <branch>
```

`--force-with-lease`, never bare `--force`: it aborts if the remote moved since the last fetch.

- `push declined due to repository rule violations`: a ruleset blocks `non_fast_forward` (every
  repo from skill `public-repo` has `protect main`). Ask once, then
  `gh api repos/<o>/<r>/rulesets` for the id, `gh api -X PUT .../rulesets/<id> -f enforcement=disabled`,
  push, PUT it back to `active` (after a signing rewrite, add `{"type":"required_signatures"}` to its
  `rules` in the same PUT).
- A rewrite that changes the root commit fails the next gitleaks-action run on the push
  (`fatal: ambiguous argument '<root>^'`): no leak, the action diffs from a parent that doesn't
  exist. Don't leave main red: prove it with `gitleaks git <repo> --no-banner`, then right after the
  push run `gh workflow run ci --ref <branch>` (full-history scan; needs `workflow_dispatch` in
  `on:`, else add it in a signed follow-up commit and push, whose run is green) and check the run.

Tell the user afterwards:

- every hash changed, so other clones need `git fetch && git reset --hard origin/<branch>`,
  not `git pull` (which replays the old commits as duplicates);
- a parallel session holding an old SHA will hit the lease on its next push;
- old objects stay reachable via `refs/original/`, cleanup once things look right:
  `git update-ref -d refs/original/refs/heads/<branch> && git reflog expire --expire=now --all && git gc --prune=now`.
