---
id: TASK-010
title: "sync next-id: print the next free id for a type"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-010-sync-next-id
pr: https://github.com/RobotNerd/sdlc-llm/pull/11
merge_commit: 81f25c26144e2d9d15f4526fb3e868a1c3fd49ff
blocked_by: [TASK-004]
blocks: [TASK-014, TASK-015]
---

# TASK-010: sync next-id: print the next free id for a type

## Description

Subcommand that prints the next free ID for a type: max existing ID of that type across `.tasks/`, `.tasks/specs/`, and `.tasks/archive/`, plus 1, zero-padded to three digits (SPEC-001 §'ID allocation').

## Acceptance criteria

- [ ] `sync next-id task` → `TASK-021` given TASK-001..020 present (this epic).
- [ ] `sync next-id epic` → `EPIC-002`; `sync next-id spec` → `SPEC-002`.
- [ ] Archived files are included in the max — an ID is never reused after archiving.
- [ ] Unknown type argument exits non-zero with a usage message.
- [ ] Output is exactly the ID plus a newline — nothing else — so skills can capture it.

## Testing strategy

1. With the 20 task files in place, run `sync next-id task` and confirm `TASK-021`.
2. Move a fixture `TASK-050` into `.tasks/archive/` and confirm `next-id task` jumps to `TASK-051`.
3. Run `sync next-id bogus` and confirm non-zero exit.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-004 (loader supplies the ID inventory).
- Blocks TASK-014, TASK-015 (both allocate IDs through this).
