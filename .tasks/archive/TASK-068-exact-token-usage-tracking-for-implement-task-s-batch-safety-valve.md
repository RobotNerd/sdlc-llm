---
id: TASK-068
title: Exact token-usage tracking for implement-task's batch safety valve
type: feature
status: done
epic: EPIC-003
created: 2026-09-18
branch: task-068-exact-token-usage-tracking-for-implement-task-s-batch-safety-valve
pr: "https://github.com/RobotNerd/sdlc-llm/pull/85"
merge_commit: 1f51c777c15627e0294bdd8d3427b207523061dd
blocked_by: [TASK-043]
blocks: []
---

# TASK-068: Exact token-usage tracking for implement-task's batch safety valve

## Description

Blocked on TASK-043 (the usage safety valve's config keys, `check_usage_thresholds`,
`render_usage_summary`, and the batch-mode checkpoint plumbing all already exist — this task only
changes where `tokens_used` comes from).

TASK-043 shipped both `context_pct` and `tokens_used` as the model's own best-effort estimate,
since no tool in this harness reports exact usage numbers. Investigation (reading ccstatusline's
bundled source and this session's own transcript file) found that `tokens_used` specifically
*can* be made exact: Claude Code writes every turn's token usage into the session's own transcript
JSONL (`~/.claude/projects/<escaped-cwd>/<session-id>.jsonl`), and the current session's id is
already visible in this session's own scratchpad path — no new tool needed, just a file to parse.
`context_pct` cannot be fixed the same way: its denominator (the actual context-window size) is
only ever passed to the statusline process on a transient stdin pipe, never persisted anywhere, so
it stays a self-estimate. This task only replaces `tokens_used`.

Add `compute_session_token_usage(transcript_path)` to `scaffold.py`, reproducing ccstatusline's own
`getTokenMetrics` algorithm: keep transcript lines with `message.usage`, dedupe streaming partials
(only entries with a truthy `stop_reason`, plus the trailing `null` one), sum `input_tokens` +
`output_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`. Wire it to a new
`session-token-usage` CLI subcommand taking `{"transcript_path"}`, returning `{"tokens_used", ...
per-field breakdown}`. It should raise clearly (non-zero exit, no stack trace) on a missing file or
an unparseable line — a future Claude Code transcript-format change is an expected failure mode,
not a bug to paper over.

Update `SKILL.md`'s Batch mode section: at each usage checkpoint, derive the current session's
transcript path and call `session-token-usage` instead of tracking a running self-estimated tally;
feed its `tokens_used` straight into `check-usage-thresholds`. If `session-token-usage` fails, note
it in that task's Worklog, skip the token-budget half of that checkpoint's check (keep doing the
context-usage estimate), and continue — a parsing hiccup on an internal file format must never
escalate into a systemic interrupt on its own. Update `.tasks/config.md`'s and `templates/
config.md`'s `token_budget_per_batch` Key notes bullet to say `tokens_used` is now an exact sum
from the session's own transcript, not an estimate.

## Acceptance criteria

- [x] `compute_session_token_usage` correctly sums a synthetic transcript fixture's token usage,
      matching ccstatusline's own dedup-then-sum algorithm (streaming partials excluded).
- [x] `session-token-usage` (CLI) returns `{"tokens_used", ...}` for a real transcript file and
      exits non-zero with a clear message (not a traceback) on a missing/malformed one.
- [x] `SKILL.md`'s batch-mode usage checkpoints use `session-token-usage`'s real total instead of a
      self-estimated running tally, with a documented fallback (skip the token-budget check, don't
      halt) when that call fails.
- [x] `context_pct` is untouched — still documented as a self-estimate; this task doesn't attempt
      to make it exact.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests: a synthetic JSONL fixture with a few `message.usage` entries, including at least
   one streaming-partial duplicate (no `stop_reason`, followed by a real one with the same
   content), asserting `compute_session_token_usage` sums correctly and ignores the duplicate.
2. Unit tests: `compute_session_token_usage` raises clearly on a missing file and on a line with no
   `message.usage`/malformed JSON.
3. CLI-level test for `session-token-usage`, mirroring the existing pattern for
   `check-usage-thresholds`/`render-usage-summary`.
4. Manual sanity check (human or this session, since it's read-only and free): run
   `session-token-usage` against this actual session's own transcript file and confirm the reported
   total is a plausible cumulative figure, not zero or an error.
5. `pytest` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- Tests first (10 failing: function/subcommand absent), then implemented; all pass.
- `compute_session_token_usage` raises `TranscriptError` (CLI: message to stderr, exit 2, no traceback) on a missing/unreadable file, a non-JSON line (names the line number), or a transcript with **no** `message.usage` entries at all. Interpretation note: the task text says "a line with no `message.usage`" should raise, but such lines (user turns, summaries) are routine in real transcripts, so they're skipped; only "nothing recognisable anywhere" is treated as a format change.
- Dedup: entries with a truthy `stop_reason` kept, plus the last usage entry regardless (the in-progress turn); earlier `stop_reason: null` partials dropped.
- Manual sanity check (Testing strategy step 4), run against this session's own transcript: `{"tokens_used": 4581452, "input_tokens": 100, "output_tokens": 49950, "cache_read_input_tokens": 4251939, "cache_creation_input_tokens": 279463}` -- plausible cumulative figure for ~a dozen implement-task phases; dominated by cache reads, as the specified algorithm sums them.
- SKILL.md: step 3.1 now derives the transcript path from the scratchpad path and calls `session-token-usage`; fallback on failure = Worklog note + `token_budget: null` + continue (never an interrupt). Removed the running self-estimated tally (step 2). `context_pct` untouched, still documented as an estimate.
- `.tasks/config.md` and `templates/config.md` Key notes updated.
- Full suite + `sync check` results recorded in the PR.

## Notes

- This intentionally couples `implement-task`'s batch mode to Claude Code's own internal,
  undocumented transcript file format — the same kind of harness-specific coupling `SKILL.md`
  already accepts for `ScheduleWakeup`, not a new category of risk for this skill.
- `context_pct` staying a self-estimate is a deliberate, confirmed scope boundary, not an
  oversight — see TASK-043's own Worklog and this task's Description for why the denominator can't
  be recovered from any file.
