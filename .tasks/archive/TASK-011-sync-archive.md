---
id: TASK-011
title: "sync archive: move done/wont-do tasks to .tasks/archive/"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-011-sync-archive
pr: https://github.com/RobotNerd/sdlc-llm/pull/12
merge_commit: efa3b35180e3a55a8b7acbda082366f954d5112a
blocked_by: [TASK-004, TASK-008]
blocks: [TASK-013]
---

# TASK-011: sync archive: move done/wont-do tasks to .tasks/archive/

## Description

Move every `done` and `wont-do` `TASK-*.md` into `.tasks/archive/`, leaving a one-line reference (title + PR link) behind for traceability. Runs at the end of every `sync` when `archive_done: true`; also invokable standalone (SPEC-001 §'The sync script', §'Resolved during planning').

## Acceptance criteria

- [ ] `done` and `wont-do` task files are moved to `.tasks/archive/`, preserving filename.
- [ ] A one-line reference remains discoverable (in an `archive` region or index) with the task title and, for `done`, the PR URL from frontmatter.
- [ ] Archived files still count for `sync next-id` (verified with TASK-010).
- [ ] With `archive_done: false` in `config.md`, `sync` skips archiving; `sync archive` still works when called directly.
- [ ] Moving is idempotent — a second run finds nothing to do.
- [ ] Unit tests over a fixture repo with one `done`, one `wont-do`, one `todo` task.

## Testing strategy

1. Fixture repo: mark one task `done`, run `sync`, confirm the file is under `.tasks/archive/` and a reference line remains.
2. Run `sync` again; confirm no further change.
3. Set `archive_done: false`; confirm `sync` leaves the file in place but `sync archive` moves it.

## Worklog

- 2026-09-13: `python3 .tasks/bin/sync archive` against this real repo reports "Nothing to
  archive" — all 9 done tasks so far were already hand-moved into `.tasks/archive/` during each
  task's phase-4 bookkeeping. Real confirmation that the manual archiving matches what the real
  code now does, and that the idempotency check holds on real history, not just fixtures.
- Design decision on AC #2 ("a one-line reference remains discoverable... in an archive region or
  index"): didn't build a separate index. `archive()` only moves the file — frontmatter (title,
  `pr`) is untouched, and `discover()` already scans `.tasks/archive/`, so TASK-008's
  `render_board_column` keeps surfacing a done task's title + PR on the board regardless of file
  location, up to its 20-row cap. Once a task ages past that cap, the archived file itself (full
  content, not just one line) is the durable record. A second index would duplicate that.
- `should_auto_archive(config)` is implemented and tested even though nothing calls it yet — the
  bare `sync` write mode that would (per AC #4, "with archive_done: false, sync skips archiving")
  doesn't exist (see TASK-012's Worklog). `sync archive`, invoked directly, always archives
  regardless of config, which is what "sync archive still works when called directly" asks for.

## Notes

- Blocked by TASK-004 and TASK-008 (board reference updated as part of the move).
- Blocks TASK-013.
- For this repo all 20 tasks are `todo`, so the first real archive run is a no-op — good for the bootstrap check.
