---
name: public-repo
description: Publish a local repo to GitHub as public and harden it (privacy and secret gates, CI with pinned actions and gitleaks, repo security settings), plus README screenshots from a made-up demo. Use for "опубликуй на github", "сделай репо публичным", "по канонам github / безопасности", "добавь скриншоты в readme".
argument-hint: "[owner/name]"
---

# Public GitHub repo

The owner's defaults for every public repo. Run in order, skip what is already done. Heavy steps
(demo screenshots, CI fixes) go to a background agent with this file as its brief.

## Content rules
- English only: README, UI strings, prompts, test data, comments.
- Nothing personal: no hosts, IPs, SSH ports, domains, usernames, home paths, emails. Settings via env
  with `.env.example`; `.env` gitignored (add `!.env.example` if `.env.*` is ignored).
- No infra of the owner's (nginx vhosts, VPN, server specifics). A deploy kit only when asked, generic
  and parameterized.
- `git config user.email` is the GitHub noreply address (`<id>+<login>@users.noreply.github.com`).
- Files: README (what, screenshots, requirements, run locally, use, configuration table, security,
  development layout), LICENSE (MIT, `Copyright (c) <year> <git config user.name>`), SECURITY.md (private
  vulnerability reporting + design notes), `.gitignore`, `.editorconfig`, Makefile `check` (lint +
  tests), `.pre-commit-config.yaml` with gitleaks, `.github/dependabot.yml` (language ecosystem +
  github-actions, weekly).

## CI
- `.github/workflows/ci.yml`: `on:` push to main, `pull_request`, `workflow_dispatch` (full-history
  gitleaks scan after a history rewrite); top-level `permissions: contents: read`; checkout with
  `persist-credentials: false`; every action pinned by full SHA plus a `# vX.Y.Z` comment. Latest SHA:
  `tag=$(gh api repos/<o>/<r>/releases/latest --jq .tag_name); gh api repos/<o>/<r>/commits/$tag --jq .sha`.
- Jobs: tests + linter; `secrets`: checkout with `fetch-depth: 0`, then `gitleaks/gitleaks-action`
  with `GITHUB_TOKEN` (no license for a personal account).
- GitHub-hosted runners only: never attach a self-hosted runner (fork PRs would
  run code there). Never `pull_request_target`.

## Gates before the first push
- Every commit SSH-signed (`git log --format=%G? | sort | uniq -c`: only `G`). Missing
  `gpg.format`: the repo-local block of `~/dotfiles/install.sh` ("Commit signing for this repo")
  before the first commit; already committed unsigned: skill `git-history-rewrite` (unpushed, no force).
- `make check`.
- gitleaks (`go install github.com/zricethezav/gitleaks/v8@<tag>` if missing):
  `$(go env GOPATH)/bin/gitleaks dir . --no-banner`, after the commit `gitleaks git . --no-banner`.
- python3 scan of `git ls-files` for U+0400..U+04FF and U+2014: empty.
- `git ls-files -z | xargs -0 grep -nIiE -f <(grep -vE '^[[:space:]]*(#|$)' ~/.claude/private/denylist)`: empty; no denylist file: say so in the report.
- `git status --short`: no `bin/`, `data/`, `.env`, binaries.

## Publish and harden
```sh
R=<owner>/<name>
gh repo create $R --public --source=. --remote=origin --push --description "..."
gh repo edit $R --add-topic a,b --enable-wiki=false --enable-projects=false --delete-branch-on-merge
gh api -X PATCH repos/$R -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
gh api -X PUT repos/$R/private-vulnerability-reporting
gh api -X PUT repos/$R/vulnerability-alerts
gh api -X PUT repos/$R/automated-security-fixes
gh api -X PUT repos/$R/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
gh api -X PUT repos/$R/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors
gh api -X POST repos/$R/rulesets --input - <<'EOF'
{"name":"protect main","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"required_signatures"}]}
EOF
```
- The ruleset blocks deletion, force pushes and unsigned commits: the owner pushes straight to main.
- Verify each setting with a GET, then `gh run watch <id> --exit-status`.
- Git over SSH pushes workflow files even without the token's `workflow` scope.

## README screenshots
- Made-up demo only: fake backends (fake API server, fake CLI) on spare ports with invented English
  data; never the owner's accounts, data or production services.
- Shoot the real UI with skill `page-shot`, driving the flow in its `<js>`. PNG 1800 px wide, run
  `magick ... -strip`, save to `assets/screenshots/<name>.png`. Look at every image, OCR it for names,
  hosts, ports and paths before committing.
- README: `## Screenshots` near the top, one line saying it is a made-up demo, then a caption and
  `![alt](assets/screenshots/<name>.png)` per image.
- Monospace fonts with ligatures (JetBrains Mono) draw `<-`, `!=` as glyphs: set
  `font-variant-ligatures: none` on code.
