---
id: TASK-025
title: "refine-backlog: move mechanical steps to a stdlib script; activity-aware stale detection"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-025-refine-backlog-script-split
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-027]
---

# TASK-025: refine-backlog: move mechanical steps to a stdlib script; activity-aware stale detection

## Description

Same pattern as TASK-021/022/024, applied to `refine-backlog` (TASK-017): move its deterministic
steps into a stdlib-only Python script — resync (`sync`/`sync check`), the blocked-chain report
(reading `BOARD.md`'s `⛔` markers), the stale-`todo` scan, the under-specified scan (detecting
placeholder/empty Acceptance criteria or Testing strategy), and applying a confirmed TODO reorder.
`SKILL.md` shrinks to what's genuinely the human's call: which `wont-do`/re-interview/reorder
proposals to act on.

**Additional work item, decided with the user before implementation:** replace the stale-`todo`
scan's simple "`created` more than 30 wall-clock days old" check with an **active-days-elapsed**
measure — count distinct calendar days with at least one commit to `default_branch` between a
task's `created` date and now, and flag it only once that count exceeds the threshold (default
30), not raw wall-clock days. This fixes a real problem with the current rule: on a personal
project that gets dropped and picked back up much later, a pure wall-clock check flags *every*
`todo` task as stale the instant the project is resumed, regardless of whether anything was
actually neglected. Active-days-elapsed contributes ~0 for a long dormant gap, so nothing is
falsely flagged on resume, while a task genuinely bypassed through 30+ days of real ongoing work
still gets flagged, matching the original rule's intent. (Two alternatives considered and
rejected during planning: anchoring the wall-clock check to the *last* commit instead of "today"
doesn't actually fix the problem — the first commit made after resuming becomes the new anchor,
so the flood just gets delayed by one commit; and a raw commit-count threshold was viable
but a less intuitive knob to tune than a day-count, given commit granularity varies. See the
`add-task` conversation that filed this task for the full comparison.)

## Acceptance criteria

- [ ] A stdlib-only Python script under `.claude/skills/refine-backlog/` performs: the resync
      step (`sync` then `sync check`), the blocked-chain report (reading `BOARD.md`'s `⛔`
      markers and the tasks they name), the under-specified scan (flagging any `todo`/`blocked`
      task whose Acceptance criteria or Testing strategy section is empty or still carries
      template placeholder text), and applying a confirmed TODO reorder (moving the exact
      rendered line, then confirming `sync check` stays clean).
- [ ] The stale-`todo` scan is reimplemented as **active-days-elapsed**: for each `todo` task,
      count distinct calendar days with ≥1 commit to `default_branch` strictly between its
      `created` date and today (via `git log`), and flag it only if that count exceeds a
      threshold (default 30, kept as a constant in the script — not a `config.md` field, same as
      today). A repo dormant for months and just resumed must not flag every pre-existing task.
- [ ] `SKILL.md` is rewritten so its own prose covers only the human-facing proposals and
      decisions (which `wont-do`/re-interview/reorder suggestions to act on) — each backed by one
      script invocation for the mechanical computation and reporting.
- [ ] Unit tests (`pytest`) cover: active-days-elapsed against a fixture git history with a
      deliberate multi-week gap (must not flag a task created right before the gap once resumed),
      the under-specified scan's placeholder/empty detection, and the blocked-chain report against
      a mixed-status fixture.
- [ ] Every guardrail already in `SKILL.md` (propose, don't act unilaterally on `wont-do` or
      reordering) still holds — the script reports and computes; only the human's confirmed
      choice is applied.

## Testing strategy

1. Build a small fixture git repo with a deliberate multi-week commit gap; confirm a task
   `created` right before the gap is *not* flagged once "today" is set to just after the repo
   resumes, and confirm a task genuinely untouched through 30+ active days of continuous
   post-resume commits *is* flagged.
2. Unit-test the under-specified scan against a template-placeholder fixture and a genuinely
   filled-in one.
3. Unit-test the blocked-chain report against a fixture with a real (not currently-outstanding)
   and a resolved `blocked_by` chain.
4. Dry-run a confirmed TODO reorder through the script; confirm `sync check` stays clean.
5. Re-read `SKILL.md` and confirm its remaining prose is proposal/decision-facing only, with one
   script call per mechanical step it used to describe as prose.

## Worklog

_(empty — appended during implementation)_

## Notes

- No hard dependency — TASK-017 (what this refactors) is already done.
- Placed at the bottom of TODO — decided with the user via `add-task`'s priority-placement step.
- The active-days-elapsed design was chosen over two alternatives (last-commit-anchored
  wall-clock, raw commit-count) after an explicit analysis-and-recommendation pass with the user
  during this task's own creation — see Description for the comparison.
