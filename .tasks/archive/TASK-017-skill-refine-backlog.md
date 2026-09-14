---
id: TASK-017
title: "refine-backlog skill: periodic lightweight backlog pass"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-017-skill-refine-backlog
pr: https://github.com/RobotNerd/sdlc-llm/pull/26
merge_commit: d0f729c03c2d25e71237f0067bff06260761bbdf
blocked_by: [TASK-009]
blocks: []
---

# TASK-017: refine-backlog skill: periodic lightweight backlog pass

## Description

A short periodic pass (not a ceremony): confirm/reorder TODO priority with the user, recompute blocked status via `sync`, surface stale `todo` tasks as `wont-do` candidates, and flag under-specified tasks for another `add-task`-style pass (SPEC-001 §`refine-backlog`).

## Acceptance criteria

- [x] Skill is a checklist with STOP markers; it proposes changes and waits for the user rather than acting unilaterally on priority.
- [x] Runs `sync` to recompute `blocked` / `blocks` and epic status — does not hand-edit them.
- [x] Lists `todo` tasks whose `created` date is old as `wont-do` candidates, with the user deciding.
- [x] Flags tasks lacking concrete acceptance criteria or a testing strategy for re-refinement.
- [x] Any TODO reordering is applied by editing the hand-maintained list, then `sync` — which must preserve the new order.

## Testing strategy

1. Run against the current board; confirm it reports the blocked chain (e.g. TASK-004 → TASK-006 → …) and proposes nothing destructive without confirmation.
2. Backdate a fixture task's `created`; confirm it shows up as a `wont-do` candidate.
3. Reorder two TODO lines through the skill; confirm `sync check` stays clean and the order holds.

## Worklog

- 2026-09-13: Built `.claude/skills/refine-backlog/SKILL.md` — pure prose, same as
  `add-task`/`init-project` before their script-extraction follow-ups (021/022), since this task
  predates that pattern being applied here too. Much smaller than `implement-task`: essentially a
  report-then-confirm loop, with `sync` already owning all the mechanical recomputation.
  Stale-`todo` threshold is a hardcoded 30 days in the skill's own prose, not a `config.md`
  field — no other skill reads it, so it didn't need a schema change.
- **Tested against the real board first** (safe, read-only): confirmed the blocked-chain report
  correctly says "nothing blocked" (no `⛔` markers exist today), the stale scan correctly finds
  nothing (`TASK-018`, the oldest real `todo`, is only 3 days old against the 30-day threshold),
  and the under-specified scan correctly finds nothing (spot-checked `TASK-018`'s AC — concrete).
  This directly proves the AC's "proposes nothing destructive without confirmation" on a genuinely
  healthy board, not a contrived empty one.
- **Then a scratch fixture** (same throwaway-branch approach as TASK-016), on
  `test-refine-backlog-dryrun`, to exercise the paths the real board couldn't:
  - `TASK-025` (scratch), backdated `created: 2026-06-01` (104 days) — the stale-scan logic
    correctly flagged it as the only candidate among every real+scratch `todo` task.
  - `TASK-026` (scratch), body sections left as literal `{{criterion}}`/`{{step}}` template
    placeholders — the under-specified scan correctly flagged only this one.
  - Reordered `TASK-025`/`TASK-026`'s TODO lines (moved the literal rendered lines, per the
    skill's own step 5) — `sync check` stayed at exit `0` before and after, confirming reordering
    never registers as drift.
  - Cleanup: discarded the scratch reorder edit, deleted `test-refine-backlog-dryrun` (local and
    remote). No scratch artifacts remain in the real backlog or on GitHub.
- `pytest` (211 passed) and `sync check` (exit 0) reconfirmed on this branch after restoring the
  real implementation — no Python touched, both are reconfirmations.

## Notes

- Blocked by TASK-009 (relies on the TODO-merge semantics being settled).
- Independent of the other skills.
