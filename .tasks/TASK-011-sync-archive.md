---
id: TASK-011
title: "sync archive: move done/wont-do tasks to .tasks/archive/"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-011-sync-archive
pr: null
merge_commit: null
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

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-004 and TASK-008 (board reference updated as part of the move).
- Blocks TASK-013.
- For this repo all 20 tasks are `todo`, so the first real archive run is a no-op — good for the bootstrap check.
