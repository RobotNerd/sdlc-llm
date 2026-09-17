---
id: TASK-045
title: Opt-in, critic-gated, per-batch-capped auto-merge
type: feature
status: todo
epic: EPIC-003
created: 2026-09-14
branch: task-045-critic-gated-capped-auto-merge
pr: null
merge_commit: null
blocked_by: [TASK-041, TASK-032]
blocks: [TASK-054, TASK-055]
---

# TASK-045: Opt-in, critic-gated, per-batch-capped auto-merge

## Description

Blocked on TASK-041 (core autonomous loop) and TASK-032 (EPIC-002's `gh pr merge` guardrail hook,
which must already support this exception — see its Notes, amended 2026-09-14, for the marker
shape this task defines and wires in).

An explicit, off-by-default opt-in that closes the human-merge gate for a batch run. Repurposes
`config.md`'s existing `allow_auto_merge` key (currently fixed `false` for every project) into a
real toggle; it stays `false` unless a project deliberately sets it `true`.

When enabled:
1. Once a PR's checks are green, run a **narrow, checklist-style critic pass** on a cheap/fast
   model (not the implementing model) — scoped to: does the diff satisfy every acceptance
   criterion, does `git diff --name-only` stay in the task's scope, did every quality gate
   actually pass, is there anything alarming. Not an open-ended code-quality review — cost is the
   whole reason this is scoped narrowly (per SPEC-003's Alternatives).
2. The critic must explicitly approve before `gh pr merge` runs. On any critic rejection, treat it
   as an isolated interrupt (per TASK-042): skip auto-merge for this task, leave the PR open for
   human review, flag it in the summary, continue the batch.
3. A new `.tasks/config.md` key — `autonomous_merge_cap` (default e.g. `5`, `null` = unlimited) —
   caps how many tasks in one batch run may be auto-merged. Once reached, force a human checkpoint
   (halt the batch, per TASK-042's systemic routing) regardless of further critic approvals.
4. Just before calling `gh pr merge`, write whatever marker TASK-032's guardrail hook checks for
   (defined here, coordinated with that hook's actual implementation) proving this is the
   scripted, critic-approved path — never a bare model decision to merge.
5. Extend the end-of-batch summary (from TASK-041) with a critic-findings section: what the critic
   found per task it reviewed, even ones that passed — useful signal on whether the critic is
   earning its cost.

## Acceptance criteria

- [ ] `allow_auto_merge` defaults to `false`; auto-merge never happens unless a project explicitly
      sets it `true`.
- [ ] The critic pass runs on a distinctly cheaper/faster model than the implementer, scoped to
      the checklist above — not an open-ended review.
- [ ] A critic rejection skips auto-merge for that task only (isolated interrupt) and leaves the
      PR open for a human, without halting the batch.
- [ ] `autonomous_merge_cap` halts the batch once reached, regardless of further approvals.
- [ ] `gh pr merge` is only ever invoked through this path when enabled, and TASK-032's guardrail
      hook's marker check actually allows it in that case (verified against the real hook, not
      just this task's own code).
- [ ] The end-of-batch summary includes critic findings per reviewed task.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the critic-invocation function against fixture diffs/acceptance criteria (both
   an approve and a reject case).
2. Unit tests on the cap logic: under cap continues, at cap halts.
3. Integration test against TASK-032's actual guardrail hook: with the marker written, `gh pr
   merge` is allowed; without it, denied — proving the two tasks' halves fit together correctly.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.
6. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   with `allow_auto_merge: true` on a scratch project, run a trivial task through to a real
   critic-approved auto-merge, confirming the whole path end to end. Human-run — record in the
   Worklog, given the real-PR/real-merge nature of this test.

## Worklog

_(empty — appended during implementation)_

## Notes

- The single biggest behavior change in this epic — it's the one place this workflow's standing
  "a human always reviews and merges" guardrail gets a deliberate, capped, opt-in exception. Keep
  the default (`allow_auto_merge: false`) untouched by every other task in this repo.
- Coordinate the exact marker format with TASK-032 if that task is picked up by a different
  sitting than this one — its Notes point back here.
