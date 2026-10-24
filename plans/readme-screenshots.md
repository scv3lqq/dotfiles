# README screenshots

## Goal

Show the setup in `README.md` with four screenshots of a made-up demo scene:
an AeroSpace layout, Neovim in tmux, the `prefix + s` session picker and Yazi.
The repo is public, so every pixel must come from the demo: no real projects,
sessions, paths, shell history, user name or host name.

Current behavior: `README.md` has no images and the repo has no `assets/`
directory. Nothing in the configs changes.

## Acceptance criteria

Run from the repo root. `$S` is the session scratchpad directory (passed to
every agent in its prompt; never written into a repo file).

1. `ls assets/screenshots` prints exactly `layout.png`, `nvim.png`,
   `picker.png`, `yazi.png`.
2. `for f in assets/screenshots/*.png; do sips -g pixelWidth "$f" | tail -1; done`
   prints `pixelWidth: 1800` four times.
3. `stat -f '%z %N' assets/screenshots/*.png`: every size is at most 1572864.
4. `for f in assets/screenshots/*.png; do $S/run/bin/ocr "$f"; done | grep -ciFf $S/run/forbidden.txt`
   prints `0` (forbidden list from Shared definitions).
5. OCR proves each shot's content (`$S/run/bin/ocr <png> | grep -ciF <phrase>`
   prints at least 1): `nvim.png`: `orders.go`, `Idempotency`;
   `picker.png`: `billing`, `gateway`, `idempotency`, `invoice`;
   `yazi.png`: `retry.go`, `billing-worker`; `layout.png`: `api-gateway`, `ok`.
6. `magick identify -verbose assets/screenshots/*.png | grep -ciFf $S/run/forbidden.txt`
   prints `0`.
7. `grep -cF '## Screenshots' README.md` prints `1`;
   `grep -cF '](assets/screenshots/' README.md` prints `4`;
   `grep -oE 'assets/screenshots/[a-z]+\.png' README.md | sort -u | xargs ls`
   exits 0.
8. `grep -cF 'assets/screenshots/' CLAUDE.md` prints `1`; `wc -l < CLAUDE.md`
   prints a number below 200.
9. `git diff main -- README.md CLAUDE.md | python3 -c 'import sys; print(sum(chr(0x2014) in l for l in sys.stdin if l.startswith("+")))'`
   prints `0`.
10. The machine is back to its state before the run: `test ! -e ~/code`
    exits 0; `defaults read com.mitchellh.ghostty NSQuitAlwaysKeepsWindows`
    prints `1`; `env -u TMUX tmux -L dotfiles-demo ls` exits non-zero;
    `aerospace list-windows --monitor all --app-bundle-id com.mitchellh.ghostty.demo | wc -l`
    prints `0`; `grep -c DEMO_HIST ~/.zsh_history` prints `0`;
    `diff $S/run/env-before.txt $S/run/env-after.txt` exits 0.
11. `git diff --name-only main...HEAD` lists exactly `CLAUDE.md`, `README.md`,
    the four `assets/screenshots/*.png` and `plans/readme-screenshots.md`.
12. Visual check: Read each PNG; it shows what its README caption says and
    nothing that is not part of the demo scene.

## Gates

No test suite in this repo; the gates are the acceptance criteria above plus
the per-task gates. Full Gates = criteria 1-11, run by the orchestrator and
the validator; criterion 12 by the reviewer and the validator.

## Shared definitions

### Paths and names

- Work dir: `$S/run/` (scripts, raw captures, logs). Reuse from the spike:
  `$S/spike/GhosttyDemo.app` (Ghostty clone, bundle id
  `com.mitchellh.ghostty.demo`), `$S/spike/bin/claude` (fake Claude binary),
  `$S/spike/bin/winbounds` (window bounds helper), `$S/spike/e2e.zsh`
  (working end-to-end recipe), `$S/spike/winbounds.swift`, `$S/spike/claude.c`.
- Fixture root: `$HOME/code`. It must not exist before T1 runs; it shows as
  `~/code/...` in Yazi and the picker, so no path with the user name appears.
- Projects (Go modules, stdlib only, no network):

  | Dir | Module |
  |---|---|
  | `~/code/orders-api` | `example.com/orders-api` |
  | `~/code/billing-worker` | `example.com/billing-worker` |
  | `~/code/api-gateway` | `example.com/api-gateway` |

- Demo git identity: `Demo User <demo@example.com>`; every git call that
  commits runs with `-c user.name='Demo User' -c user.email=demo@example.com
  -c commit.gpgsign=false`; repos init with `-b main`.
- Demo zsh history: `$S/run/zsh_history`, zsh extended format
  (`: <epoch>:0;<command>`), 12 generic lines (`go test ./...`,
  `git log --oneline -5`, `make lint`, `docker compose up -d`, ...).
- tmux server: label `dotfiles-demo`, config `$S/run/tmux.conf` built as in
  the spike (tmux/tmux.conf above `# Plugins`, `bind r` pointed at the demo
  config, then `set -g @tmux-dotbar-bg "#0B0E14"` and `run-shell` of
  `~/.tmux/plugins/tmux-dotbar/dotbar.tmux` and
  `~/.tmux/plugins/vim-tmux-navigator/vim-tmux-navigator.tmux`). Never TPM,
  never `~/.tmux.conf` on this server. Started with
  `env -u TMUX DEMO_HIST=$S/run/zsh_history tmux -L dotfiles-demo -f $S/run/tmux.conf`.
- Sessions and windows (names at most 8 chars: the status bar cuts at 8):

  | Session | cwd | Window | Content |
  |---|---|---|---|
  | `orders` | `~/code/orders-api` | 1 `editor` | `nvim -i NONE -c 'silent AutoSession disable' -O +/Idempotency-Key internal/handler/orders.go internal/handler/orders_test.go` |
  | | | 2 `shell` | empty prompt |
  | | | 3 `claude` | fake Claude, `@claude_state waiting`, title `Add idempotency keys to order creation` |
  | `billing` | `~/code/billing-worker` | 1 `files` | `yazi internal/worker/retry.go` |
  | | | 2 `claude` | fake Claude, `@claude_state done`, title `Retry failed invoice webhooks` |
  | `gateway` | `~/code/api-gateway` | 1 `shell` | ran `go test ./...`, then `git log --oneline -5`, ends at an empty prompt |

- Shots (final files, 1800 px wide, metadata stripped, at most 1572864 bytes):

  | File | Content |
  |---|---|
  | `assets/screenshots/layout.png` | three demo windows on one workspace: `orders:editor` left full height, `billing:files` right top, `gateway:shell` right bottom |
  | `assets/screenshots/nvim.png` | one window, `orders:editor` |
  | `assets/screenshots/picker.png` | one window, `orders:editor` under the picker popup: `orders` expanded, Claude rows at the bottom |
  | `assets/screenshots/yazi.png` | one window, `billing:files` |

- Forbidden list: `$S/run/forbidden.txt`, one fixed string per line, matched
  case-insensitively (`grep -iFf`) by every leak check. Written by the
  orchestrator before dispatch and kept out of the repo: it holds the user
  name, real names, the GitHub handle, the host names, work-context words
  and scratch path fragments. Agents read it, never copy it into repo files
  or demo content.

## Tasks

### T1: demo fixtures

Model: sonnet. Depends on nothing. Files (outside git): `$S/run/fixtures.zsh`,
`$S/run/zsh_history`, the tree under `~/code`. No repo file changes, no commit.

`fixtures.zsh` (zsh, `set -euo pipefail`):

- Aborts with `fixtures: ~/code exists, refusing` and exit 1 when `~/code`
  exists; with `fixtures: missing <tool>` and exit 1 when `go` or `git` is
  missing.
- Writes the three modules with heredocs, runs `go mod init <module>` in
  each (the go directive is whatever the toolchain writes), commits the
  history below with fixed `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` (start
  `2026-10-19T09:00:00+00:00`, +3 h per commit), then applies the
  uncommitted edits.
- Writes `$S/run/zsh_history`.

Code style of the demo (it is the user's showcase): hexagonal layout
(`cmd/`, `internal/{domain,usecase,repository,handler}/`), errors wrapped as
`fmt.Errorf("op: %w", err)`, table-driven tests, comments only for why, no
logging library (stdlib `log` only in `main.go`), gofmt clean. Lines in
`internal/handler/orders.go`, `internal/handler/orders_test.go` and
`internal/worker/retry.go` at most 70 columns with tabs as 4 (they are shown
in half-width splits); other files at most 90.

`orders-api`:

- `internal/domain/order.go`: `type Status string` with `StatusPending`,
  `StatusPaid`, `StatusCancelled`; `type Order struct` (`ID`, `CustomerID`,
  `AmountCents int64`, `Currency`, `Status`, `CreatedAt time.Time`);
  `ErrNotFound`, `ErrInvalidAmount` (`errors.New`).
- `internal/usecase/orders.go`: `Repository` interface (`Save`, `Get`,
  `GetByIdempotencyKey`); `type CreateInput struct` (`CustomerID`,
  `AmountCents`, `Currency`, `IdempotencyKey string`); `Orders` with
  `Create(ctx, CreateInput) (domain.Order, error)` (validates the amount,
  returns the stored order when the idempotency key was seen) and
  `Get(ctx, id string) (domain.Order, error)`; an injectable clock and ID
  generator.
- `internal/repository/memory.go`: in-memory repository, `sync.RWMutex`.
- `internal/handler/orders.go`, 60 to 90 lines: `OrderService` interface
  (`Create`, `Get` as in usecase), `Orders` struct, `NewOrders`,
  `Routes(mux *http.ServeMux)` registering `POST /orders` and
  `GET /orders/{id}`, `create` and `get` handlers, `writeJSON`, and an error
  mapper (`ErrNotFound` 404, `ErrInvalidAmount` 422, bad JSON 400, else 500,
  via `errors.Is`).
- `internal/handler/orders_test.go`: table-driven `TestOrdersCreate`
  (created 201, invalid amount 422, bad JSON 400) with `httptest` and a fake
  service; at least 40 lines.
- `cmd/orders-api/main.go`: wires repository, usecase, handler,
  `log.Fatal(http.ListenAndServe(":8080", mux))`.
- `Makefile` (`test`, `lint` targets), `.gitignore` (`/bin/`), `README.md`
  (3 lines).
- History: `chore: init module`, `feat(domain): add order model and errors`,
  `feat(usecase): create and fetch orders`,
  `feat(handler): expose orders over HTTP`,
  `test(handler): cover order creation`.
- Uncommitted: `create` in `internal/handler/orders.go` reads the
  `Idempotency-Key` header into `CreateInput.IdempotencyKey` (4 to 8 added
  lines). Both the committed and the edited state build and pass tests.

`billing-worker`:

- `internal/worker/invoice.go`: `type Invoice struct` (`ID`, `CustomerID`,
  `AmountCents`, `WebhookURL string`).
- `internal/worker/retry.go`, 40 to 60 lines: `type Backoff struct`
  (`Base`, `Max time.Duration`, `Attempts int`), `ErrPermanent`,
  `Retry(ctx context.Context, b Backoff, op func(context.Context) error) error`:
  exponential delay capped at `Max`, waits on a `time.Timer` or `ctx.Done()`,
  stops early on `errors.Is(err, ErrPermanent)`, returns
  `fmt.Errorf("retry: %d attempts: %w", n, err)`.
- `internal/worker/retry_test.go`: table-driven (succeeds on 3rd attempt,
  permanent error stops at 1, context cancel).
- `internal/worker/webhook.go`: `Sender` interface, `Worker.Deliver(ctx,
  Invoice) error` using `Retry`.
- `cmd/billing-worker/main.go`, `Makefile`, `.gitignore`, `README.md`.
- History: `chore: init module`, `feat(worker): add invoice model`,
  `feat(worker): retry with exponential backoff`,
  `feat(worker): deliver invoice webhooks`. Worktree clean.

`api-gateway`:

- `internal/proxy/proxy.go`: route table (path prefix to upstream
  `*url.URL`), `httputil.ReverseProxy` per route, 404 for unknown prefixes.
- `internal/proxy/proxy_test.go`: table-driven with `httptest` upstreams.
- `internal/ratelimit/limiter.go`: token bucket with an injectable clock,
  `Allow() bool`, a `DefaultBurst` constant.
- `internal/ratelimit/limiter_test.go`: table-driven, independent of
  `DefaultBurst`'s value.
- `cmd/api-gateway/main.go` (upstreams `http://localhost:8081`,
  `http://localhost:8082`), `Makefile`, `.gitignore`, `README.md`.
- History: `chore: init module`, `feat(proxy): route by path prefix`,
  `test(proxy): cover unknown routes`, `feat(ratelimit): add token bucket`,
  `fix(ratelimit): refill on first request`.
- Uncommitted: `DefaultBurst` changes from 10 to 20.

Task gates (all must pass; T1 leaves `~/code` in place for T2):

- `for m in orders-api billing-worker api-gateway; do (cd ~/code/$m && test -z "$(gofmt -l .)" && go vet ./... && go test -count=1 ./...) || echo FAIL $m; done`
  prints no `FAIL`.
- `for m in orders-api billing-worker api-gateway; do git -C ~/code/$m log --format='%an <%ae>' | sort -u; done`
  prints only `Demo User <demo@example.com>`.
- `git -C ~/code/orders-api status --porcelain` prints
  ` M internal/handler/orders.go`; for `api-gateway`
  ` M internal/ratelimit/limiter.go`; for `billing-worker` nothing.
- `grep -rniFf $S/run/forbidden.txt ~/code $S/run/zsh_history --exclude-dir=.git`
  prints nothing.
- `for f in orders-api/internal/handler/orders.go orders-api/internal/handler/orders_test.go billing-worker/internal/worker/retry.go; do expand -t4 ~/code/$f | awk 'length > 70' ; done`
  prints nothing.
- `wc -l < ~/code/orders-api/internal/handler/orders.go` between 60 and 90.

Definition of done: gates green, `fixtures.zsh` reruns cleanly after
`mv ~/code $S/run/code.old` (do that once to prove it, then rerun).

### T2: capture

Model: sonnet. Depends on T1 (fixtures in `~/code`). Files: `$S/run/capture.zsh`,
`$S/run/ocr.swift` (built to `$S/run/bin/ocr`), `$S/run/tmux.conf`,
`$S/run/raw/`, and in the repo `assets/screenshots/{layout,nvim,picker,yazi}.png`.
Commit only the four PNGs: `feat(readme): add demo screenshots`.

Start from `$S/spike/e2e.zsh`; its snippets are verified (Ghostty clone
launch, window id polling, workspace layout, `fzf --listen` picker control,
`compose`, cleanup). `capture.zsh` (zsh, `set -uo pipefail`, a `trap cleanup EXIT`):

1. Preflight, each failure prints `capture: <reason>` and exits 1:
   `~/code` missing; any of `magick`, `swiftc`, `yazi`, `nvim`, `go`,
   `~/.local/share/nvim/mason/bin/gopls` missing; no monitor named
   `Built-in Retina Display` in `aerospace list-monitors`; workspace 5 not
   empty (`aerospace list-windows --workspace 5`); port 16266 in use.
2. Record `$S/run/env-before.txt`: main tmux session names
   (`env -u TMUX tmux list-sessions -F '#{session_name}'`), focused
   workspace and each monitor's visible workspace, sorted AeroSpace window
   ids excluding the demo bundle id, listing of
   `~/.local/share/nvim/sessions` (empty line if absent),
   `defaults read com.mitchellh.ghostty NSQuitAlwaysKeepsWindows`.
3. Build `$S/run/tmux.conf`, start the server, create the sessions and
   windows from Shared definitions. In every zsh pane, after a client is
   attached (spike: typing before attach leaves a wrapped line), send
   ` fc -p $DEMO_HIST 1000 1000; clear` (leading space), then
   `tmux clear-history`. Fake Claude panes: ` clear; exec <claude binary>`,
   then `set -p @claude_state`, `select-pane -T '<title>'`.
4. `aerospace workspace 5`, launch the clone attached to `orders:editor`
   (`open -na $S/spike/GhosttyDemo.app --args --window-save-state=never
   --auto-update=off -e /opt/homebrew/bin/tmux -L dotfiles-demo attach -t orders:editor`),
   poll for its window id. Wait 8 s for nvim and gopls, then send `zz` and
   `:nohlsearch | echo` Enter, wait 1 s. Check `capture-pane -p` of the
   editor pane: contains `Idempotency-Key`, last line has no `Session`
   text. `screencapture -x -o -l <id> $S/run/raw/nvim.png`.
5. Picker: set `@claude_since` of the `billing:claude` pane to now-120 and
   of the `orders:claude` pane to now-45,
   set the server env `FZF_DEFAULT_OPTS` to the server's current value plus
   `--listen=127.0.0.1:16266`, open the popup with
   `send-keys -K -c <client> C-a s` in the background, wait for the port,
   unset the env again, POST `pos(<N>)` with N the 1-based index of the
   `orders` session row in `GET 127.0.0.1:16266?limit=30` (sessions sort by
   name, so `first` lands on `billing`), then
   `transform(~/dotfiles/tmux/session-picker.sh right {1} {2} {3})` with
   `~` expanded; check `GET 127.0.0.1:16266?limit=30` lists `editor`,
   `idempotency` and `invoice` rows; wait 1 s, capture `raw/picker.png`,
   POST `abort`.
6. Yazi: `switch-client -c <client> -t billing:files`, wait 2 s, check
   `capture-pane` shows `retry.go`, capture `raw/yazi.png`, switch back to
   `orders:editor`.
7. Layout: launch two more clone windows attached to `billing:files` and
   `gateway:shell`; `aerospace flatten-workspace-tree --workspace 5`,
   `aerospace layout --workspace 5 --root tiles horizontal` (spike order),
   `aerospace join-with --window-id <gateway window> left`; wait 2 s; check
   the three tmux client sizes are about 77x42, 77x20, 77x20; `compose`
   (canvas `#2A2F3A`, size 2880x1740) into `raw/layout.png`.
8. Post-process each raw PNG:
   `magick raw/<n>.png -strip -resize 1800x assets/screenshots/<n>.png`.
9. `cleanup` (also the EXIT trap, idempotent): `tmux -L dotfiles-demo
   kill-server`, wait for the clone windows to disappear, restore each
   monitor's visible workspace and then the focused one from
   env-before.txt, `lsregister -u` the clone, `defaults delete
   com.mitchellh.ghostty.demo` (ignore "does not exist"), `defaults write
   com.mitchellh.ghostty NSQuitAlwaysKeepsWindows -bool true` only when
   env-before.txt recorded 1 and the value is now different,
   `mv ~/code $S/run/code.<epoch>` (never rm). Then write
   `$S/run/env-after.txt` the same way as step 2.

`ocr.swift`: `ocr <png>` prints one recognized line per text observation
(`VNRecognizeTextRequest`, `.accurate`, `usesLanguageCorrection = false`),
exit 1 with `ocr: <error>` on failure. Build:
`swiftc -O -o $S/run/bin/ocr $S/run/ocr.swift`.

Warn: the run moves AeroSpace focus to workspace 5 for about a minute; keys
typed by the user meanwhile land in demo windows. The OCR and visual gates
catch stray text: on any doubt rerun (T1's `fixtures.zsh` recreates
`~/code` after the cleanup moved it).

Task gates: acceptance criteria 1 to 6 and 10, plus Read each PNG under
`assets/screenshots/` and confirm it matches its Shared definitions row.

Definition of done: gates green, the four PNGs committed with the message
above, scripts left in `$S/run/`.

### T3: README and CLAUDE.md

Depends on nothing (refers to T2's file names from Shared definitions).
Files: `README.md`, `CLAUDE.md`. Verbatim edits; commit:
`docs: add screenshots section to README`.

Edit 1, `README.md`, old text:

```
`install.sh --update`.

## Requirements
```

new text:

```
`install.sh --update`.

## Screenshots

The projects, sessions and shell history in these shots are a made-up demo.

AeroSpace tiling three Ghostty windows: Neovim, Yazi and a shell with the
Starship prompt.

![AeroSpace layout with Neovim, Yazi and a shell](assets/screenshots/layout.png)

Neovim inside tmux: a Go handler next to its test, gitsigns marks in the
gutter, lualine at the bottom.

![Neovim in tmux](assets/screenshots/nvim.png)

`prefix + s`: the session tree popup; Claude panes waiting on you or finished
in the last 10 minutes are listed at the bottom.

![tmux session picker](assets/screenshots/picker.png)

Yazi with a code preview.

![Yazi file manager](assets/screenshots/yazi.png)

## Requirements
```

Edit 2, `README.md`, old text:

```
| `notes/`, `plans/`, `everything.md` | | personal notes, implementation plans, Russian cheatsheet |
```

new text:

```
| `notes/`, `plans/`, `everything.md` | | personal notes, implementation plans, Russian cheatsheet |
| `assets/screenshots/` | | README screenshots of a made-up demo, recipe in `plans/readme-screenshots.md` |
```

Edit 3, `CLAUDE.md`, old text:

```
- `README.md`: user-facing setup.
```

new text:

```
- `README.md`: user-facing setup.
- `assets/screenshots/`: README shots of a made-up demo scene; how to retake
  them: `plans/readme-screenshots.md`.
```

Task gates: acceptance criteria 7, 8, 9.

## Seams

| Producer | Consumer | Contract |
|---|---|---|
| T1 | T2 | Paths and names: project dirs, file paths opened in nvim and Yazi, `Idempotency-Key` in `orders.go`, demo history path |
| T2 | T3 | Shots table: file names and what each shows (README captions) |

## Edge cases

- macOS only: the capture needs AeroSpace, Ghostty and `screencapture`;
  nothing runs on Linux and no config changes, so Linux is unaffected.
- Missing tools or gopls, Retina display absent (lid closed), workspace 5
  busy, `~/code` present, port 16266 taken: preflight aborts before any
  window opens.
- First run: Screen Recording is already granted to the terminal (spike).
- Failure mid-run: the EXIT trap kills the demo server, closes the clone,
  restores focus and Ghostty defaults, moves `~/code` aside.
- Dirty worktree: the branch starts clean; only the files of criterion 11
  change.
- Real data paths: the main tmux server, the main Ghostty instance and its
  defaults domain, `~/.zsh_history`, nvim shada and sessions,
  `~/.claude/settings.json` are never written.

## Not doing

- No capture scripts or fixtures in the repo: they live in `$S/run/`; this
  plan is the recipe for a retake.
- No GIF or video, no Linux screenshots, no `everything.md` changes.
- No changes to nvim, tmux, Ghostty, AeroSpace, Yazi or zsh configs.
- No image optimizer installs (`brew install` is off limits).
