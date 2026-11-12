# Check latency measurements

Measurements on macOS 26.5.1 arm64, Python 3.15.2, tmux 3.8 and codex-cli 0.167.1 use `time.monotonic_ns()`. Times are elapsed, not CPU time. Test commands ran sequentially; first means a fresh process and fixture, followed by warm runs. OS caches were not evicted. Concurrent workloads were uncontrolled and baseline load was not recorded.

## Test gates

Historical measurements from an earlier implementation, superseded by the later full-gate results below. Seconds; each cell gives first / warm samples, then median (range). All measured commands exited successfully.

| Command | Before | After (candidate unless marked final) |
| --- | --- | --- |
| `python3 -B -m unittest codex.test_activity.NotificationTests` | 20.145 / 21.417, 20.827; 20.827 (20.145–21.417) | 23.565 / 22.434, 38.143; 23.565 (22.434–38.143) |
| `python3 -B -m unittest codex.test_agent_inbox.InboxTests` | 20.553 / 18.097, 20.152; 20.152 (18.097–20.553) | 32.492 / 22.080, 21.804; 22.080 (21.804–32.492) |
| `python3 -B codex/run_tests.py` | 46.452 / 47.207, 48.065; 47.207 (46.452–48.065) | 62.732 / 58.492, 59.735; 59.735 (58.492–62.732) |
| `just check` | 52.633 / 51.514, 53.041; 52.633 (51.514–53.041) | 66.377 / 59.543, 57.537; 59.543 (57.537–66.377) |
| `just check-fast` | unavailable: new recipe | 0.294 / 0.267, 0.351; 0.294 (0.267–0.351) |

Candidate NotificationTests grew from 20 to 21 tests; InboxTests stayed at 25. The candidate runner grew from 190 to 191 discovered tests in 11 groups; the final full check includes 192 Codex tests, including 22 NotificationTests; `just check` also includes four feature-plan tests. `check-fast` runs shell syntax checks, `codex/check.py` and those four tests; it omits the full Codex suite and does not replace the mandatory full gate. The final class and standalone runner timings were not repeated after the NUL fix. Candidate full check measured 72.709 / 55.047, 59.807 seconds, median 59.807 (55.047–72.709); candidate fast check measured 0.329 / 0.310, 0.287, median 0.310 (0.287–0.329). Class times overlap in the concurrent runner and must not be summed.

The notification hook now batches ordinary scalar jq extraction with fallback for complex, invalid or NUL-containing input. One unchanged representative test measured 1.454 / 1.441, 1.541 seconds before and 1.368 / 1.389, 1.336 after: medians 1.454 and 1.368, ranges 1.441–1.541 and 1.336–1.389. This narrow result does not prove full-gate improvement: full runs were slower, the test count changed, and untouched Inbox also slowed. Instrumentation attributed 19.300 of 19.394 seconds in NotificationTests and 19.159 of 19.225 seconds in InboxTests to subprocess calls including scripts and children, not specifically startup or unnecessary waiting. Load averages at diagnosis were 8.97/8.54/7.81 and at completion 9.93/11.21/9.33; the cause of the spread is unknown.

## Catalog and network

`codex app-server` over stdio was initialized once, then sequential `plugin/list` RPCs were timed. Milliseconds below show first / warm-process samples, median and range. Earlier requests may warm caches; no cache-hit telemetry or independent cold-process series was captured, so these results cannot separate cache from network cost. The default RPC median of 2.942 seconds does not establish a cache read; a current isolated cache-read metric is unavailable. The user-reported 1.11-second value is historical, not a current controlled measurement.

| Request | First / warm; median (range), ms | Response |
| --- | --- | --- |
| Default | 3699.10 / 2752.20, 2942.14; 2942.14 (2752.20–3699.10) | 8 marketplaces, 0 load errors |
| Local | 73.48 / 24.63, 23.02; 24.63 (23.02–73.48) | 8, 0 |
| Vertical | 3.10 / 2.54, 2.57; 2.57 (2.54–3.10) | 0, 0 |
| All enumerated kinds | 889.89 / 841.50, 776.58; 841.50 (776.58–889.89) | 9, 0 |
| All enumerated kinds, `forceRefetch` | 1592.28 / 1606.37, 2155.98; 1606.37 (1592.28–2155.98) | 9, 0 |

These are route observations, not before/after comparisons. The explicit kinds list excludes Global in the 0.167.1 processor. With kinds omitted and `forceRefetch: true`, three separate-process requests took 87639.73, 89067.76 and 99911.04 ms: median 89067.76, range 87639.73–99911.04. Each returned eight marketplaces and zero reported load errors; these are separate processes, not a cold-cache series. A prior request timed out after 10 seconds and may have continued during later samples. A verified JSON tracing channel recorded another request at 96036.61 ms without matching fallback, featured-fetch failure, timeout or decode messages. The classifier inspected only message fields for a scoped log target. Global's actual outcome and the cause of its delay remain opaque: successful RPCs and zero load errors can coexist with a logged remote fallback, and missing matching messages do not exclude errors elsewhere. Network conditions were uncontrolled.

## Agent startup and review

Three separate current-model (`gpt-6.1-sol`, high effort) representative defect probes detected the intended defect in 3/3 cases. Their first `thread.started` events were 0.458, 0.366 and 0.579 seconds: median 0.458, range 0.366–0.579. End-to-end process times were 28.472, 15.318 and 16.317 seconds: median 16.317, range 15.318–28.472. These are three distinct cases, not repeated samples of one case. The event is a startup proxy, not isolated startup latency; review time cannot be derived by subtracting it. Item events lack sufficient item metadata to isolate model inference, tool time or review phases. No alternate model, before/after series or isolated startup metric was measured, so no model-change or latency-improvement claim follows.

## Fingerprints and checks

Candidate measurement SHA-256: `claude/hooks/notify.sh` `7b28a199ed642e4c23d2a87a963b931a2172dd4bfdfd7480275b2c92568492a3`; `codex/test_activity.py` `ed997b7ef7d87aca219d6c71163d2562357445404c5f54c9a5fe9b395d86dbbb`; `codex/test_agent_inbox.py` `ba336623b79335721946a310678d10bceada84f96463bb370ba25317e32f55d9`; `codex/run_tests.py` `445eaaee2c05a72c87cb7f61c7c80ae21cead8e358d9ed2cb9141acb32c6e856`; `tmux/agent-inbox.sh` `29e625171b35dc9e0b9dd84cb29aae700315a82d954cd61dc517d783b405b573`; `justfile` `5d73512185bdb297026557d55d808d47dbb9cfd7d5b2da3b3a1ab20d75c25b94`. Final full and fast gate source SHA-256: `claude/hooks/notify.sh` `1d5280524c76a0a611488d93a0fb50f63663f2eb551caf0c359136fc25a46424`; `codex/test_activity.py` `fc981f07f358d4e5b1e93929dec0794f222aa65106c652091d5956d72157b9a6`; `justfile` `5d73512185bdb297026557d55d808d47dbb9cfd7d5b2da3b3a1ab20d75c25b94`. Before hook SHA-256: `0734926936c6fc68733633b919c7c352db3b5d8b2c2967ee48d936ef68cc3f50`. Generated experimental `ClientRequest.json` SHA-256: `2d629aaaceea335d7e58ab19ce5908c8dd75ca3f3a6161a5f015bf59aadd3295`.

The parser regression passed before and after implementation, including jq and Python fallback cases. A NUL regression failed before its fix and both focused regression methods passed after it; a bounded differential of 105 jq inputs against HEAD had zero mismatches. Four focused harness integrity tests passed; they cover source drift, report hashes, symlinks and artifact tampering. No harness instruction or role changed. Timings and checks reflect their measured source fingerprints, not later edits.

## Full gate with Python fallback compatibility tests

Three serial `just check` runs, after adding the new compatibility suite, used a monotonic timer immediately around the command. All passed. The first, second and third runs took 61.462, 60.421 and 62.327 seconds; median 61.462, range 60.421–62.327. One-minute load averages at each start/end were 6.55/9.48, 9.48/8.68 and 8.68/8.09 respectively. The machine had eight logical CPUs. The first run is a first process invocation, not an evidenced OS cold-cache run. These numbers do not meet a five-second goal, and changed coverage and uncontrolled load prevent a direct before/after full-gate attribution.

A separate instrumented series passed in 63.763, 62.780 and 60.621 seconds, including up to one second of final polling wait. One-second process snapshots observed at least 419, 426 and 400 distinct PIDs; fast processes can be missed and PID reuse is possible, so these are sampled lower bounds, not full nested counts. The observer added `ps` calls and can perturb timings. In these diagnostic runs, NotificationTests ended 47.9–50.3 seconds after gate start, InboxTests 41.0–43.2 seconds, and HookTests 33.7–35.6 seconds. They overlap in the four-worker runner. The separately scheduled new compatibility suite took 12.472–12.740 seconds in the plain runs (unittest's own timer), after the parallel worker phase.

A fresh serial focused profile after the change measured NotificationTests at 24.400 seconds, InboxTests at 20.121 seconds and HookTests at 14.847 seconds. These include setup and fixtures; higher concurrent times are consistent with contention but do not establish its cause. The inbox fixture uses Python tmux, ps and date stubs, while hook integration also uses a real isolated tmux server. A separate microbenchmark measured Python startup at 17.62 ms median and the Python shim plus interpreter at 31.62 ms; these are process-level observations, not a full-gate cost decomposition. No complete process-tree trace or measured residual breakdown between real operations, fixture startup and system contention is available.

### Activity tmux fixture logger experiment

A shell fast path for simple `tmux` call records was tested against the existing
`jq` logger. Three serial NotificationTests baselines took 23.241, 25.628 and
24.046 seconds; three candidate trials took 22.841, 23.531 and 22.915 seconds.
Each trial passed all 22 tests. The candidate's median improvement was 1.131
seconds, smaller than the baseline range of 2.387 seconds, so it does not prove
a repeatable win beyond noise. More importantly, it bypassed an installed `jq`
that returned an error, changing stderr, exit status and call records. The
candidate was reverted. An isolated protocol test records this failure along
with JSON encoding, missing `jq`, log failure and concurrent append checks.
The timing measures the class rather than a full `just check` gate.

### Reusing immutable fixture executables

The activity and inbox fixtures now keep immutable stub programs on stable
inodes for each test class. Per-test environment, logs, state, home directories
and tmux sockets remain separate. Three serial runs of NotificationTests,
InboxTests and HookTests together (65 tests) took 53.052, 51.632 and 51.713
seconds before this wave and 15.212, 15.365 and 15.134 seconds after it. The
runs used the same explicit environment and Python executable. These focused
numbers do not establish the full-gate result.

An intermediate full gate passed in 21.724 seconds, before the final launcher
and notifier changes. Its slowest recorded class, RunnerTests, took 11.624
seconds under concurrent load. A subsequent isolated RunnerTests diagnostic
took 11.533 seconds; its source is outside this fixture experiment's scope.
The full-gate target of five seconds is therefore not established.

### Runner tmux isolation and launch fixtures

A current three-run baseline of the complete gate passed in 27.089, 19.557 and
19.382 seconds (median 19.557, range 19.382–27.089). Child CPU was 20.271,
19.899 and 20.037 seconds respectively; starting load averages were
2.79/4.52/4.53, 4.23/4.72/4.60 and 3.66/4.56/4.55. These invocations did not
establish a cold operating-system cache. The first process invocation took
longer; the cause was not measured.

The runner fixtures now explicitly select an empty tmux configuration for their
four private servers. A real-server canary confirmed that a deliberately selected
configuration executes its marker and the empty configuration does not, while
both servers accept commands. No parent socket is used. The focused runner and
canary suite passed 13 tests in 4.545 seconds. The first full candidate passed
in 15.436 seconds, with 21.952 seconds of child CPU. A second candidate using a
shared immutable launch executable passed in 14.569 seconds, with 23.060
seconds of child CPU. The launch suite alone passed eight tests in 0.704 seconds,
compared with 2.406 seconds in a preceding focused run. These are individual
observations, not controlled repeated measurements.

A shell date fixture and additional isolation regressions passed a later full
candidate in 14.788 seconds, with 22.613 seconds child CPU and one-minute load
rising from 5.31 to 8.86. The date fixture's 43 hook and inbox tests passed in
8.987 seconds; preceding separate class timings totaled 10.614 seconds. Load
and run composition differ, so neither observation establishes a full-gate
improvement attributable to the date fixture. The full gate retained 192
original Codex tests, the notification and isolation regressions, and four
feature tests. AST comparisons retained the original test methods and their
calls in the runner, launcher, activity and inbox files, after normalizing only
the four explicit tmux configuration arguments in the runner. No full-gate
result below five seconds has been established. Prior sampled PID counts are
lower bounds, not complete process counts; no process observer was active in
these timed gate runs.

Three further serial full gates passed in 17.749, 17.030 and 14.691 seconds
(median 17.030, range 14.691–17.749), with child CPU of 24.458, 24.442 and
22.909 seconds. One-minute load rose from 7.04 to 7.84, 7.84 to 8.36 and 8.36
to 10.50, respectively. Each ran 192 original Codex tests, eight notification
and fixture regression tests and four feature tests. This series does not meet
the target. A separate instrumented class profile found 175 direct tmux calls
and 29 direct shell hook calls taking 1.556 and 4.478 seconds wall respectively;
nested calls were not attributed. Surviving fixture log records undercount
calls because tests reset logs. Sampling and tracing limitations do not justify
an irreducible execution-time claim.

An experimental shell fast path for the hook's process stub passed its focused
tests but altered traceback output on fallback. It was reverted. A microtest
of 20 stable-inode Python process stubs took 0.804 seconds wall and 0.498 CPU;
20 jq lookups took 0.084 and 0.061 seconds, but the latter do not implement the
full error contract and cannot be treated as equivalent.

After running the two independent launch isolation calls concurrently, three
plain full gates passed in 16.182, 16.217 and 14.791 seconds (median 16.182,
range 14.791–16.217). Child CPU was 23.844, 25.766 and 24.079 seconds;
one-minute load was 3.04→6.46, 6.46→7.73 and 7.73→8.90. The regression retains
both calls and their assertions. Tool versions were just 1.59.0, Python 3.15.2,
tmux 3.8 and jq 1.8.2. This remains above five seconds; the concurrent change
has not established a repeatable full-gate improvement.

### Persistent immutable fixture code

The fixture code cache stores only executable source, keyed by its bytes and
interpreter fingerprint. It does not cache test results. The private cache checks
ownership, permissions and content; atomic publication supports concurrent
workers. Each test still gets its own environment, state, home and logs. Each
class links the cached inode into its private temporary directory, which is
removed at class cleanup. Regression checks cover concurrent threads and
processes, content and interpreter changes, symlinks and corrupted entries.

A complete gate starting with an explicitly empty cache passed in 15.467
seconds. The next two passed in 12.674 and 13.270 seconds with a warm cache.
After interpreter-fingerprint coverage was added, three full gates passed in
12.682, 11.780 and 12.996 seconds (median 12.682, range 11.780–12.996), with
child CPU 22.454, 23.350 and 25.771 seconds. Some entries had been populated by
focused checks before the first of those runs, so it was not an empty-cache
measurement. The gate ran 192 original Codex tests, 13 notification and
fixture regressions and four feature tests. Starting one-minute loads were
5.33, 5.16 and 5.04. Neither series meets the five-second target. CPU time and
load alone do not identify contention or establish an irreducible floor.

A generic shell dispatcher preserved ordinary arguments, environment, stdin,
status and `$0` in a small prototype but changed `BASH_SOURCE`. The fixture
bodies currently searched do not reference that variable or `__file__`, but
error paths and other protocol cases remain unverified; the prototype was not
adopted.

### Scoped dispatcher experiment

A shared shell dispatcher was evaluated for built-in-only date fixtures, using
private body files for each test. The original and dispatched programs agreed
in a focused test on arguments, environment, NUL stdin, Unicode, stdout, stderr
and exit status; a separate test checked independent concurrent bodies and
replacement. The candidate's complete gate passed in 15.447 seconds with an
empty code cache and 12.554 and 12.291 seconds with a warm cache. Child CPU was
24.699, 25.110 and 24.840 seconds, respectively. One-minute load was
6.92→7.50, 7.50→6.76 and 6.76→6.09. Each run included 192 original Codex tests,
14 regression tests and four feature tests. Warm results overlap the previous
11.780–12.996 second series and do not establish a repeatable full-gate win.
The subsequent safe-override regression changed test source after this series;
it is not included in these full-gate measurements. The dispatcher candidate
was reverted because the full-gate timings did not establish a repeatable win.

### Shell environment isolation

With an isolated tmux socket and an explicitly selected zsh, a temporary
`ZDOTDIR` canary was read in all three diagnostic trials; with `/bin/sh`, it
was read in none. Observed startup times of 0.017–0.023 seconds did not show a
speed benefit. Runner fixtures now use a private HOME and ZDOTDIR and select
`/bin/sh`; activity and inbox fixture environments select the same shell and
their private ZDOTDIR. The real tmux canary and runner suite passed 14 tests.

Three subsequent full gates passed in 13.576, 13.927 and 12.993 seconds
(median 13.576, range 12.993–13.927). Child CPU was 24.783, 26.891 and 26.092
seconds, and one-minute load was 9.40→9.10, 9.10→8.80 and 8.80→8.87. Each
included 192 original Codex tests, 14 notification/fixture regressions and
four feature tests. The fixture-code cache was warm; OS cache state was not
measured. The five-second gate target remains unmet.

### Inbox process recorder experiment

For the fixed process-list request, the fixture recorder now takes a private
single-read snapshot after recording the call. An ASCII fast path emits that
snapshot; other inputs use the original Python decoding path. The fixture keeps
per-test data and logs, runs each invocation afresh and deletes its snapshot.
A deterministic barrier test first exposed a validation/read race in an
intermediate candidate. The snapshot version passed that test after the file
was replaced between validation and output. Differential checks also passed for
empty and unterminated input, CRLF, Unicode, quotes, NUL, invalid UTF-8, missing
files, invalid arguments, concurrent log appends and log errors. These focused
checks do not establish equivalence for every possible filesystem failure.

The focused 25-test Inbox suite passed in 4.011, 3.612 and 3.936 seconds before
and 3.108, 2.996 and 3.001 seconds with the snapshot candidate. Corresponding
child CPU was 3.188, 3.231 and 3.221 seconds before, and 2.740, 2.650 and 2.646
after. Three complete warm-cache gates with the added regression passed in
12.598, 12.757 and 12.582 seconds (median 12.598, range 12.582–12.757); child
CPU was 21.030, 21.154 and 21.718 seconds. One-minute load was 6.94→6.71,
6.71→7.11 and 7.11→6.77. Each gate ran 192 original Codex tests, 17
notification/fixture regressions and four feature tests. Prior full-gate
baselines used different load and regression coverage; these series do not
isolate a full-gate speedup. The five-second acceptance target remains unmet.

An independent subsequent full gate passed in 12.608 seconds with a warm
fixture-code cache; operating-system cache state was not established. It ran
the same 192 original Codex tests, 17 regressions and four feature tests.
The user accepted the approximately 12.6-second result for finalization; the
original five-second goal remains unmet. These timings describe the measured
source and environment, not a guarantee for later runs.
