# Status line: context bar

## Goal

Replace the plain context segment (`17%`) of `claude/statusline.sh` with a
thin 10-cell bar plus the percentage: `━╾──────── 17%`. The filled part is a
little lighter than the row, the empty track darker; at 60% the bar and the
percentage turn yellow, at 80% red (same thresholds as today).

Current behavior: segment 4 is `<ctx>%`, gray below 60, `Y` at 60, `R` at 80
(`plans/claude-statusline.md`, Output format). Everything else in the row
stays as it is.

Decision (user): the thin-line style, 5% steps.

## Acceptance criteria

1. The Fixture suite below prints only `PASS` lines and exits 0.
2. `/bin/bash -n claude/statusline.sh` exits 0; `test -x claude/statusline.sh`.
3. `git diff main...HEAD --stat` lists exactly `claude/statusline.sh`,
   `plans/claude-statusline-bar.md`, `plans/claude-statusline.md`.
4. `git diff main...HEAD -- claude/statusline.sh` touches only the color
   definitions and segment 4 (the `# 4. Context` block).

## Gates

- `/bin/bash -n claude/statusline.sh`
- `test -x claude/statusline.sh`
- the Fixture suite
- `git diff --check main...HEAD`

## Shared definitions

### Bar format

- 20 half-cell units: `units = (ctx * 20 + 50) / 100` (integer division,
  i.e. ctx rounded to the nearest 5%), capped at 20.
- `full = units / 2` cells of `━` (U+2501), then `╾` (U+257E) when
  `units % 2 == 1`, then `─` (U+2500) up to 10 cells in total.
- Colors: new `FILL` = `\033[38;5;245m`, new `TRACK` = `\033[38;5;237m`.
  The filled part (including `╾`) is painted `R` at ctx >= 80, `Y` at
  ctx >= 60, else `FILL`; the track is always `TRACK`.
- Segment 4 raw bytes: `<fill color><filled><TRACK><track><G> <pct>` where
  `<pct>` is the existing `tint "$ctx" 60 80 "${ctx}%"` result (plain below
  60, `<Y>64%<G>` / `<R>85%<G>` above). The fill color and `TRACK` codes are
  always emitted, even when their part is empty.

Examples (stripped): 0 `──────────`, 3 `╾─────────`, 10 `━─────────`,
17 `━╾────────`, 23 `━━╾───────`, 59 `━━━━━━────`, 64 `━━━━━━╾───`,
85 `━━━━━━━━╾─`, 100 and 150 `━━━━━━━━━━`.

### Fixture suite

Supersedes the suite in `plans/claude-statusline.md`. Run as
`bash <file>` from anywhere inside the repo.

```bash
SL="$(git rev-parse --show-toplevel)/claude/statusline.sh"
T=$(mktemp -d)
echo "fixtures in $T"
git init -q -b demo-branch "$T/repo"
git init -q -b feature/this-is-a-very-long-branch-name-for-tests "$T/long"
git init -q -b main "$T/det"
git -C "$T/det" -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com \
  commit -q --allow-empty -m init
git -C "$T/det" checkout -q --detach
mkdir "$T/plain"
SHA=$(git -C "$T/det" rev-parse --short HEAD)
fail=0
mk() { jq -cn --arg cwd "$1" "{workspace: {current_dir: \$cwd}} * $2"; }
raw() { printf '%s' "$1" | "$SL"; }
raw_has() { perl -0777 -ne 'BEGIN{$p=shift @ARGV; $p =~ s/\\e/\e/g} exit(index($_, $p) < 0 ? 1 : 0)' "$1"; }
check() {
  out=$(raw "$2"); rc=$?
  got=$(printf '%s' "$out" | perl -pe 's/\e\[[0-9;]*m//g')
  if [ "$rc" = 0 ] && [ "$got" = "$3" ]; then echo "PASS $1"
  else echo "FAIL $1 rc=$rc got=[$got] want=[$3]"; fail=1; fi
}
color() {
  if raw "$2" | raw_has "$3"; then r=yes; else r=no; fi
  if [ "$r" = "$4" ]; then echo "PASS $1"
  else echo "FAIL $1 substring [$3] present=$r want=$4"; fail=1; fi
}
J1=$(mk "$T/repo" '{model: {id: "claude-opus-5-5"}, effort: {level: "xhigh"}, context_window: {used_percentage: 23.7}}')
check C1 "$J1" 'repo  demo-branch · opus 5.5 xhigh · ━━╾─────── 23%'
color C1r "$J1" '\e[38;5;245m━━╾\e[38;5;237m───────\e[38;5;240m 23%' yes
J2=$(mk "$T/plain" '{model: {id: "claude-sonnet-4-5-20250929"}, context_window: {used_percentage: null}}')
check C2 "$J2" 'plain · sonnet 4.5 · ────────── 0%'
color C2r "$J2" '\e[38;5;245m\e[38;5;237m──────────\e[38;5;240m 0%' yes
J3=$(mk "$T/plain" '{model: {id: "claude-opus-5-5[1m]"}, effort: {level: "high"}, context_window: {used_percentage: 64}}')
check C3 "$J3" 'plain · opus 5.5 high · ━━━━━━╾─── 64%'
color C3c "$J3" '\e[33m━━━━━━╾\e[38;5;237m───\e[38;5;240m \e[33m64%\e[38;5;240m' yes
J4=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 85}}')
check C4 "$J4" 'plain · opus 5.5 · ━━━━━━━━╾─ 85%'
color C4c "$J4" '\e[31m━━━━━━━━╾\e[38;5;237m─\e[38;5;240m \e[31m85%\e[38;5;240m' yes
J5=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, effort: {level: "high"}, context_window: {used_percentage: 59.9}}')
check C5 "$J5" 'plain · opus 5.5 high · ━━━━━━──── 59%'
color C5y "$J5" '\e[33m' no
color C5r "$J5" '\e[31m' no
J6=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 86.4}, seven_day: {used_percentage: 41}}}')
check C6 "$J6" 'plain · opus 5.5 · ━───────── 10% · 5h 86%'
color C6c "$J6" '\e[33m5h 86%\e[38;5;240m' yes
J7=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 79.9}, seven_day: {used_percentage: 97}}}')
check C7 "$J7" 'plain · opus 5.5 · ━───────── 10% · 7d 97%'
color C7c "$J7" '\e[31m7d 97%\e[38;5;240m' yes
check C8 "$(mk "$T/repo" '{workspace: {git_worktree: "wt"}, model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch ⎇ wt · opus 5.5 · ╾───────── 5%'
check C9 "$(mk "$T/repo" '{agent: {name: "reviewer"}, model: {id: "claude-haiku-5-5"}, effort: {level: "medium"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch · reviewer · haiku 5.5 medium · ╾───────── 5%'
check C10 "$(mk "$T/plain" '{model: {id: "us.anthropic.claude-opus-4-1-20250805-v1:0"}, context_window: {used_percentage: 1}}')" 'plain · opus 4.1 · ────────── 1%'
check C11 "$(mk "$T/plain" '{model: {id: "claude-opus-4-20250514"}, context_window: {used_percentage: 1}}')" 'plain · opus 4 · ────────── 1%'
check C12 "$(mk "$T/plain" '{model: {id: "gpt-x", display_name: "Custom Model"}, context_window: {used_percentage: 1}}')" 'plain · custom model · ────────── 1%'
check C13 "$(mk "$T/long" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'long  feature/this-is-a-very-long-bra… · opus 5.5 · ────────── 1%'
check C14 "$(mk "$T/det" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" "det  $SHA · opus 5.5 · ────────── 1%"
check C15 "$(mk "$HOME" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" '~ · opus 5.5 · ────────── 1%'
out=$(printf 'not json' | "$SL"); rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then echo "PASS C16"; else echo "FAIL C16 rc=$rc out=[$out]"; fail=1; fi
check C17 "$(mk "$T/plain" '{context_window: {used_percentage: 3}}')" 'plain · ╾───────── 3%'
if raw "$J1" | perl -0777 -ne 'exit(/\A\e\[38;5;240m[^\n]*\e\[0m\n\z/ ? 0 : 1)'; then echo "PASS C18"; else echo "FAIL C18 framing"; fail=1; fi
check C19 "$(mk "$T/gone" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'gone · opus 5.5 · ────────── 1%'
t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do raw "$J1" >/dev/null; done
t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
if perl -e "exit(($t1 - $t0) < 1.0 ? 0 : 1)"; then echo "PASS C20 20 runs in $(perl -e "printf '%.3f', $t1 - $t0") s"
else echo "FAIL C20 20 runs took $(perl -e "printf '%.3f', $t1 - $t0") s"; fail=1; fi
J21=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 100}}')
check C21 "$J21" 'plain · opus 5.5 · ━━━━━━━━━━ 100%'
color C21r "$J21" '\e[31m━━━━━━━━━━\e[38;5;237m\e[38;5;240m \e[31m100%\e[38;5;240m' yes
check C22 "$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 150}}')" 'plain · opus 5.5 · ━━━━━━━━━━ 150%'
check C23 "$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 17}}')" 'plain · opus 5.5 · ━╾──────── 17%'
exit $fail
```

## Tasks

### T1: `claude/statusline.sh`, segment 4 as a bar

Scope: two edits in `claude/statusline.sh`, nothing else in the file.

Edit 1, old (lines 9-10):

```
R=$'\033[31m'
RST=$'\033[0m'
```

new:

```
R=$'\033[31m'
FILL=$'\033[38;5;245m'
TRACK=$'\033[38;5;237m'
RST=$'\033[0m'
```

Edit 2, old (lines 80-82):

```
# 4. Context
tint "$ctx" 60 80 "${ctx}%"
add "$REPLY"
```

new (loops, not `${var:0:n}`: substring offsets on multibyte text depend on
the locale Claude Code passes, and macOS bash is 3.2; braces before a
multibyte character: bash 3.2 reads its lead byte as part of the name):

```
# 4. Context: 10-cell bar in half-cell (5%) steps, then the percentage
units=$(( (ctx * 20 + 50) / 100 ))
[ "$units" -gt 20 ] && units=20
full=$((units / 2))
half=$((units % 2))
fill=""
i=0
while [ "$i" -lt "$full" ]; do fill="${fill}━"; i=$((i + 1)); done
[ "$half" -eq 1 ] && fill="${fill}╾"
track=""
i=$((full + half))
while [ "$i" -lt 10 ]; do track="${track}─"; i=$((i + 1)); done
if [ "$ctx" -ge 80 ]; then fc=$R; elif [ "$ctx" -ge 60 ]; then fc=$Y; else fc=$FILL; fi
tint "$ctx" 60 80 "${ctx}%"
add "$fc$fill$TRACK$track$G $REPLY"
```

Task gates: `/bin/bash -n claude/statusline.sh`; `test -x claude/statusline.sh`;
the Fixture suite (all PASS, rc 0).

Commit: `feat(claude): show the context as a bar in the status line` with
pathspec `claude/statusline.sh`.

## Seams

None: one task, one file.

## Edge cases

- macOS bash 3.2: loops and `$(( ))` only.
- ctx above 100 (not expected for the context window): the bar stays full,
  the number is printed as is.
- Live: `~/.claude/statusline.sh` links to the repo file, so the change shows
  on the next repaint of every session; nothing to apply.

## Not doing

- Token counts (`170k/1M`), a different width, other segments.
- Changing thresholds or the rate-limit segments.
