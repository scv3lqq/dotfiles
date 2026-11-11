# Check latency measurements

Measurements on macOS 26.5.1 arm64, Python 3.15.2, tmux 3.8 and codex-cli 0.167.1 use `time.monotonic_ns()`. Times are elapsed, not CPU time. Test commands ran sequentially; first means a fresh process and fixture, followed by warm runs. OS caches were not evicted. Concurrent workloads were uncontrolled and baseline load was not recorded.

## Test gates

Seconds; each cell gives first / warm samples, then median (range). All measured commands exited successfully.

| Command | Before | After (candidate unless marked final) |
| --- | --- | --- |
| `python3 -B -m unittest codex.test_activity.NotificationTests` | 20.145 / 21.417, 20.827; 20.827 (20.145–21.417) | 23.565 / 22.434, 38.143; 23.565 (22.434–38.143) |
| `python3 -B -m unittest codex.test_agent_inbox.InboxTests` | 20.553 / 18.097, 20.152; 20.152 (18.097–20.553) | 32.492 / 22.080, 21.804; 22.080 (21.804–32.492) |
| `python3 -B codex/run_tests.py` | 46.452 / 47.207, 48.065; 47.207 (46.452–48.065) | 62.732 / 58.492, 59.735; 59.735 (58.492–62.732) |
| `just check` | 52.633 / 51.514, 53.041; 52.633 (51.514–53.041) | 66.377 / 59.543, 57.537; 59.543 (57.537–66.377), final |
| `just check-fast` | unavailable: new recipe | 0.294 / 0.267, 0.351; 0.294 (0.267–0.351), final |

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
