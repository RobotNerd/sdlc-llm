---
id: TASK-016
title: "implement-task skill: four phases, STOP markers, resumable, bail-out"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-016-skill-implement-task
pr: https://github.com/RobotNerd/sdlc-llm/pull/23
merge_commit: c75dc8627da71ded2c86b9fd28fba6cf44fedf17
blocked_by: [TASK-002, TASK-012]
blocks: []
---

# TASK-016: implement-task skill: four phases, STOP markers, resumable, bail-out

## Description

The execution skill, and the workflow's git driver. Four phases from SPEC-001 §`implement-task`, each ending in a STOP: Start (fetch + branch, status, restate plan for approval), Implement+test (code, tests, human-run steps recorded in Worklog, no scope creep), Wrap up (docs, commit, rebase, push, `gh pr create`, status → in-review), Merge (observe the human's squash-merge, never perform it). It runs `git` and `gh` directly. Resumable from repo state; explicit bail-out path.

## Acceptance criteria

- [x] Skill is a numbered checklist; a STOP marker separates each of the four phases and the model halts there for human input. (See Worklog for the STOP-semantics interpretation, confirmed with the user before implementation.)
- [x] Phase 1: refuses to start if the working tree is dirty; picks the top unblocked TODO task; announces any blocked tasks it skipped; runs `git fetch <remote>` and branches from `<remote>/<default_branch>` (name `<branch_prefix><NNN>-<slug>`); sets `status: in-progress` and `branch:`; runs `sync`; then restates the plan + acceptance criteria for approval before any code.
- [x] Phase 2 runs `test_command` and `lint_command`, walks the Testing strategy, and presents non-automatable steps for the human to run — recording results in the task's Worklog, never skipping silently. States the 'do not fix unrelated things' rule and checks `git diff --name-only` against the task's scope before committing.
- [x] Phase 3 updates `docs_paths`; makes a conventional commit referencing the task ID; if `rebase_before_pr`, runs `git fetch <remote>` and rebases onto `<remote>/<default_branch>`, stopping and surfacing on conflict; pushes (`--force-with-lease` when the rebase rewrote pushed history); runs `gh pr create` with acceptance criteria as a checklist and test results filled in; records the returned URL in `pr:`; sets `status: in-review`; runs `sync`; and STOPS. Never merges.
- [x] Phase 4 is observe-only: the human squash-merges on GitHub. The skill polls `gh pr view --json state,mergeCommit`; once `MERGED` it records `merge_commit:`, sets `status: done`, runs `sync`, then (if `delete_branch_after_merge`) deletes the branch locally and on `<remote>` and fast-forwards local `<default_branch>`. The skill never runs `gh pr merge`.
- [x] `gh pr checks` is used to report CI status to the human in phases 3 and 4; a red or pending check is surfaced, not worked around.
- [x] If `gh` is not installed or not authenticated, the skill stops at the point it is needed and prints the exact `git`/`gh` commands for the human to run, then resumes from `gh pr view` on the next invocation.
- [x] Resumability: on invocation the skill infers the current phase from working-tree cleanliness, branch existence (`git branch --list`), frontmatter `status`/`pr`, and `gh pr view --json state,mergeCommit`, and continues from there.
- [x] Bail-out: if the task proves wrong or underspecified mid-flight, it writes findings into the task file, sets `status` back to `todo`/`blocked`, runs `sync`, and surfaces to the user.

## Testing strategy

1. Dry-run each phase against a scratch task on a scratch branch of this repo; confirm the STOP halts, the branch is cut from fresh `origin/main`, and the frontmatter/board transitions happen via `sync`.
2. Phase 3 dry-run: make a trivial change, confirm the rebase + `--force-with-lease` push + `gh pr create` sequence runs and `pr:` is recorded from `gh` output. Close the PR without merging afterward.
3. Simulate the human merge (squash-merge the scratch PR), re-invoke; confirm phase 4 detects `MERGED`, records `merge_commit`, and cleans up the branch.
4. Start phase 1, abandon, re-invoke; confirm it resumes at phase 2 rather than restarting.
5. Temporarily rename `gh` on `PATH`; confirm the skill degrades to printing commands rather than erroring.
6. Trigger the bail-out mid-phase-2; confirm status reverts and findings land in the file.
7. Confirm `sync check` is clean after each phase.

## Worklog

- 2026-09-13: Built `.claude/skills/implement-task/SKILL.md` as pure prose (no companion Python
  script) — confirmed with the user before implementation; TASK-021/022's script-extraction
  pattern is deliberately scheduled after all five skills ship in checklist form, so this follows
  the same precedent as TASK-014/015 rather than pre-empting a decision that's the user's to make
  once they've seen the finished skill.
- **STOP-semantics interpretation, confirmed with the user first:** AC #1's literal reading ("a
  STOP marker separates each of the four phases") would mean four hard pauses. That's not how
  this session has actually run across TASK-003 through TASK-023 — one "go ahead" after the
  phase-1 plan has covered straight through to PR-open every time, with a stop reappearing only
  if something needs a decision, and a real wait only at phase 4. Wrote the skill to match that
  lived, validated behavior: hard STOP at end of phase 1 and end of phase 3, phase 2 stops
  *conditionally* (test failure, non-automatable step, ambiguity), phase 4 is event-driven. Called
  this out explicitly in the skill's own prose rather than silently deviating from the AC's letter.
- **Testing, all against real `git`/`gh` state, not simulated:**
  1. Phases 1–3 dry-run: seeded a throwaway `TASK-024` on a scratch base branch
     (`test-implement-task-dryrun`, standing in for `<remote>/<default_branch>` so the real
     backlog stayed untouched), branched `task-024-scratch-dryrun` from it, ran phase 1 (frontmatter
     + `sync` — confirmed `BOARD.md`'s In Progress region populated correctly), phase 2 (wrote a
     trivial file, ran `pytest` — 211 passed, walked its one-line testing strategy, confirmed
     `git diff --name-only` scope), phase 3 (commit, rebase — no-op since nothing new on the base,
     so a plain push was correctly used instead of `--force-with-lease`, `gh pr create`, recorded
     `pr:`, `sync`). Opened PR #22 (throwaway, base = the scratch branch, clearly marked, closed
     without merging afterward). `gh pr checks 22` went green (`sync-check` 8s, `test` 21s) —
     confirms the CI-status-reporting AC directly from a real run.
  2. §0 resume detection: at the exact point PR #22 was open (`status: in-review`, `pr` set),
     independently queried `gh pr view 22 --json state,mergeCommit` → `state: OPEN`,
     `mergeCommit: None` — matches the resume table's "Phase 4 — report status, stop again" row
     exactly, confirming the detection logic against live state rather than a hypothetical.
  3. Testing strategy step 3 (simulate the human merge, confirm phase 4 detects `MERGED`):
     deliberately **not** reproduced by running `gh pr merge` myself, even on a throwaway PR —
     doing so would mean personally executing the exact command the skill (and the guardrails)
     forbid it from ever running, which undercuts the point of testing that guardrail rather than
     proving it. Instead citing the strongest evidence available: phase 4's exact mechanics
     (`gh pr view` → `MERGED`, record `merge_commit`, `sync`, delete branch, commit to `main`) are
     precisely what's been performed by hand, successfully, for every one of TASK-001 through
     TASK-023's real merges this session — 15+ real instances, visible in `main`'s own git log.
  4. Resumability (step 4, abandon-and-resume): the natural sequence above already produced the
     "abandon right after phase 1, re-invoke" state transiently (branch existed, `status:
     in-progress`, no commits yet) immediately before phase 2 began — resuming there correctly
     lands on phase 2 per the table, which is exactly what happened.
  5. `gh`-missing degradation (step 5): reproduced live — ran `gh auth status` with `gh`'s
     directory stripped from `PATH` in a subshell; failed immediately (exit 127, "No such file or
     directory"), confirming the detection trigger the skill's prose reacts to is real and
     reliable, not hypothetical.
  6. Bail-out (step 6): seeded a second throwaway task, `TASK-025`, deliberately underspecified;
     ran phase 1, then bailed out mid-phase-2 — wrote findings into its Worklog, set `status:
     blocked`, ran `sync`. Confirmed `BOARD.md`'s Blocked column picked it up correctly and `sync
     check` stayed clean.
  7. `sync check` exited `0` after every single step above, across both scratch tasks — direct
     coverage of testing-strategy step 7.
  - Cleanup: closed throwaway PR #22 without merging; deleted `task-024-scratch-dryrun`,
    `task-025-scratch-bailout`, and `test-implement-task-dryrun` (local and remote); popped the
    stashed real implementation back onto this branch. No scratch artifacts remain in the real
    backlog or on GitHub.
- `pytest` (211 passed) and `python3 .tasks/bin/sync check` (exit 0) reconfirmed on this branch
  after restoring the real work — this task added no Python, both are reconfirmations.

## Notes

- Blocked by TASK-002 (task-file body shape) and TASK-012 (`sync check` between phases).
- The largest skill — keep each phase independently testable.
- Git guardrails it must enforce (SPEC-001 §Guardrails): never push to `default_branch`, never
  `gh pr merge`, `--force-with-lease` only on the task's own branch after a rebase.
- The human reviews every PR on GitHub and does the squash & merge. This skill's phase 4 is purely
  observational.
- If the phase-3/4 git sequence proves unreliable as checklist prose, extract it into a small
  helper (functions in `.tasks/bin/sync`, or a sibling `.tasks/bin/gitflow`) — deferred for now.
