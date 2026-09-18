---
id: TASK-067
title: "batch_select range mode: use BOARD.md's hand-ordered TODO slice, not numeric task-id order"
type: bug
status: todo
epic: EPIC-003
created: 2026-09-18
branch: task-067-range-mode-board-order
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-067: batch_select range mode: use BOARD.md's hand-ordered TODO slice, not numeric task-id order

## Description

`.claude/skills/implement-task/batch_select.py`'s `"range"` mode (TASK-039) currently treats its
two endpoints as a *numeric* task-id range — `resolve_range("TASK-032..TASK-034", ...)` walks
`032, 033, 034` in order, silently skipping any id that doesn't exist or is already
`done`/`wont-do`. That's wrong: it ignores `.tasks/BOARD.md`'s hand-ordered TODO list entirely,
which is the one place task priority actually lives (`sync` never reorders it — see
`.tasks/guidelines.md`).

Fix: `"range"` mode should resolve to the **slice of the current TODO list** starting with the
given start task id and ending with the given end task id, inclusive, in board order — not
numeric id order. Reuse the same `_TODO_HEADING`/`_TODO_LINE_RE` BOARD.md-parsing technique
`resolve_stopping` already uses (and `scaffold.py`'s own `pick_top_unblocked`), generalized to an
explicit start id instead of always starting at the top.

## Acceptance criteria

- [ ] `resolve_range` resolves to the TODO list's slice from the start id through the end id,
      inclusive, in the list's literal board order — not by numeric task-id comparison.
- [ ] If the start id appears *after* the end id in the TODO list (the two arguments are backwards
      relative to real board order), the selection is refused with a clear message — same posture
      as the old numeric mode's "range is backwards" case, not silently reversed.
- [ ] If either endpoint isn't on the TODO list at all (wrong id, not currently `todo`, or simply
      never prioritized), the selection is refused with a clear message naming which endpoint.
- [ ] A task in the slice that's marked `⛔ blocked_by` on the board (still `todo`, just currently
      blocked) is included in the resolved candidate list as-is — `validate_and_order`'s existing
      blocked_by check (inside-set-and-ordered vs. outside-and-unresolved) is what actually decides
      whether the overall selection is valid, same as every other mode; `resolve_range` itself
      doesn't special-case blocked entries.
- [ ] The module docstring's description of `"range"` mode is corrected (currently describes
      numeric id order).
- [ ] Existing numeric-range-order tests in `tests/test_batch_select.py` are replaced with
      board-order equivalents; no test still asserts numeric id ordering for this mode.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests for `resolve_range` against a hand-built `board_text` fixture (same style
   `resolve_stopping`'s tests already use): a normal in-order slice, a slice containing a
   `⛔ blocked_by`-marked line, endpoints reversed relative to board order (refused), an endpoint
   missing from the TODO list (refused), start == end (single-task slice).
2. Update/extend `select_batch`'s range-mode dispatch test and the CLI subprocess test(s) in
   `tests/test_batch_select.py` to use a `BOARD.md` TODO order that differs from numeric id order,
   proving board order — not id order — is what's actually used.
3. `python3 -m pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Scope is limited to `resolve_range`/its docstring/its tests — the other three selection modes
  (`epic`, `list`, `stopping`) are unaffected and already correct.
- TASK-039's own (now-archived) task file still describes the old numeric-range behavior in its
  Description — left as historical record, not corrected retroactively.
