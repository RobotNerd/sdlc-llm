---
id: TASK-037
title: SessionStart board-context hook
type: feature
status: done
epic: EPIC-002
created: 2026-09-14
branch: task-037-sessionstart-board-context-hook
pr: "https://github.com/RobotNerd/sdlc-llm/pull/70"
merge_commit: f2036ef432e5ef4db02def3a7eddde63c5bcb06d
blocked_by: [TASK-032, TASK-052]
blocks: [TASK-039, TASK-040]
---

# TASK-037: SessionStart board-context hook

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-052 (guidelines.md trim — see amendment
below).

On `SessionStart`, inject the current `BOARD.md` In Progress/In Review sections and, if a task is
`in-progress`/`in-review`, that task's id/title/status/`pr` as `additionalContext` — so
`implement-task`'s resume-detection starts from fact already in context rather than re-deriving it
via tool calls every session.

Also inject `.tasks/guidelines.md`'s contents as `additionalContext`, read verbatim (never a
copy embedded in the hook script) — so the shared workflow model (the artifact model, what `sync`
owns, which skill to reach for) is in context from turn one in every scaffolded project, with no
`CLAUDE.md` edit required in the target repo. This only became worth doing once TASK-052 trimmed
the file to something small enough to inject on every session; injecting the pre-trim 91-line file
would defeat that task's whole point.

Not a guardrail — a convenience hook that reduces redundant board/task reads and puts the workflow
model in context at the start of every session.

## Acceptance criteria

- [x] A session start with no in-flight task injects the board's open columns (In Progress, In
      Review) only.
- [x] A session start with an in-flight task also includes that task's id/title/status/`pr`.
- [x] `.tasks/guidelines.md`'s contents appear in the injected `additionalContext` alongside the
      board state.
- [x] Output is silent (the hook skips cleanly) if `.tasks/` doesn't exist, so this hook is
      harmless in a non-workflow repo.
- [x] The hook still exits cleanly if `.tasks/` exists but `.tasks/guidelines.md` specifically is
      absent — it injects the board context it does have and simply omits the guidelines section,
      the same tolerant posture as the "`.tasks/` doesn't exist" case.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the context-building function against fixture `BOARD.md`/task-file states: none
   in-flight, one in-progress, one in-review.
2. Unit tests on the same function with `guidelines.md` present vs. absent, confirming its content
   is included/omitted respectively without affecting the board-context portion.
3. Hook-script test confirming the `additionalContext` field shape matches the documented
   `SessionStart` JSON schema.
4. A test confirming the hook exits cleanly with no output when `.tasks/` is absent.
5. `pytest` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- Confirmed the exact `SessionStart` hook contract before writing any code (Claude Code's docs
  hallucinate on a couple of fetches, so verified against the raw markdown source directly):
  stdin carries `hook_event_name: "SessionStart"` and a `source` field
  (`startup`/`resume`/`clear`/`compact`/`fork`); output is
  `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<string>"}}`
  on stdout with nothing else printed; `SessionStart` has no blocking/deny concept at all — any
  exit code just proceeds, so there's never a reason to exit non-zero here.
- Added `.claude/hooks/sessionstart_board_context.py`: `build_context(tasks_root)` extracts
  `BOARD.md`'s rendered `in-progress`/`in-review` regions verbatim (via `sync.find_region`, so
  it's always what's actually on the board, never re-derived), appends an explicit
  id/title/status/`pr` summary via `sync.discover()` if any task is in-flight, and appends
  `.tasks/guidelines.md`'s contents verbatim if the file exists. Returns `None` (hook prints
  nothing) if `.tasks/` doesn't exist or is otherwise empty of board/guidelines content — never
  an error path. `main()` reads the `SessionStart` payload, resolves `.tasks/` from the event's
  own `cwd` (not a fixed location — this hook is portable, vendored into every project), and
  prints the documented JSON shape only when there's something to report.
- Mirrored the new hook to `.claude/skills/init-project/vendored-hooks/sessionstart_board_context.py`
  (byte-identical, matching the existing `pretooluse_*` convention) and registered it in **both**
  `.claude/settings.json` and `.claude/skills/init-project/templates/settings.json` under a new
  `SessionStart` array — unlike TASK-036's repo-only hook, this one ships to every scaffolded
  project.
- Added `tests/test_sessionstart_board_context.py` (14 tests): `build_context` unit tests (no
  `.tasks/`, board columns with no in-flight task, in-progress summary, in-review summary with a
  real `pr` value, guidelines present/absent, an entirely empty `.tasks/`), hook-script subprocess
  tests (silent when `.tasks/` absent, ignores non-`SessionStart` events, survives malformed
  stdin, output shape matches the documented schema exactly), a test against this repo's own real
  tree, and vendoring checks (vendored copy byte-identical to canonical; both `settings.json`
  files register `SessionStart` identically).
- Full suite: `.venv/bin/pytest -q` → 540 passed (526 existing + 14 new), no existing test edited.
- `python3 .tasks/bin/sync check` → exit 0.

## Notes

- Depends on TASK-032's hooks-infrastructure/wiring pattern, and now also on TASK-052's trimmed
  `guidelines.md` (see Description).
- Amended 2026-09-16 (before implementation started) to also inject `guidelines.md`'s contents,
  closing a gap found during a `guidelines.md`-scoping review: nothing in a scaffolded project
  ever loaded that file today. Added `TASK-052` to `blocked_by` accordingly. No other behavior
  change to this task's original board-context scope.
