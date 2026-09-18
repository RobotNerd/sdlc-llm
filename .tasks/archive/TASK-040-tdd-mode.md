---
id: TASK-040
title: TDD mode for implement-task phase 2
type: feature
status: done
epic: EPIC-003
created: 2026-09-14
branch: task-040-tdd-mode
pr: "https://github.com/RobotNerd/sdlc-llm/pull/77"
merge_commit: 5dd8118ec2325f5f585f062963ba5d94abfa36e0
blocked_by: [TASK-032, TASK-033, TASK-034, TASK-035, TASK-036, TASK-037, TASK-038]
blocks: [TASK-054, TASK-055]
---

# TASK-040: TDD mode for implement-task phase 2

## Description

Blocked on all seven EPIC-002 tasks, per this epic's placement decision. Independent of every
other task in this epic — it's a project-wide `implement-task` behavior change, not batch-specific,
and applies identically to a single-task run or a batch run.

New `.tasks/config.md` key, `tdd_enforced`, default `true`. When `true`, `implement-task` phase 2
changes: write the test(s) for a Testing strategy step (or acceptance criterion) first, run them
and confirm they fail for the expected reason (not an unrelated error), then implement until they
pass. When `false`, phase 2 keeps today's behavior (write code and its tests together).

## Acceptance criteria

- [x] `init-project/templates/config.md` (and this repo's own `.tasks/config.md`) include
      `tdd_enforced: true`, documented under "Key notes" alongside the other boolean flags.
- [x] `scaffold.py`'s `REQUIRED_KEYS`/interview gains `tdd_enforced` (asked, with `true` proposed
      as the default, confirmable/overridable like every other interview value).
- [x] With `tdd_enforced: true`, `implement-task` phase 2 writes a failing test before any
      implementation code, runs it to confirm it fails for the right reason, then implements and
      re-runs until green — documented as an explicit sub-step, not left to model discretion.
- [x] With `tdd_enforced: false`, phase 2's behavior is unchanged from today.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Extend `tests/test_init_project_scaffold.py`: a scaffolded `config.md` contains
   `tdd_enforced: true` by default, and a `false` answer round-trips correctly.
2. Whatever test module the (by-then-existing) `implement-task` script uses gains cases: with
   `tdd_enforced: true`, the phase-2 step order writes/fails/implements/passes in that sequence; a
   test that doesn't fail as expected before implementation surfaces as a stop condition rather
   than silently continuing.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   run `implement-task` on a trivial scratch task with `tdd_enforced: true` and confirm the test
   file exists and was run (and failed) before the implementation file was written. Human-run —
   record in the Worklog.

## Worklog

- 2026-09-18: Added `tdd_enforced` to `init-project`'s config schema — `REQUIRED_KEYS`
  (`.claude/skills/init-project/scaffold.py`), the `{{tdd_enforced}}` placeholder + frontmatter
  field + "Key notes" bullet in `templates/config.md`, and a new interview row in
  `init-project/SKILL.md` step 3 (default proposed `true`, confirmable/overridable). It's a
  `REQUIRED_KEYS` entry, so — like every other interview-only key — `upgrade`'s
  `migrate-config` deliberately never auto-adds it to an already-scaffolded project
  (`merge_config_schema` explicitly skips `REQUIRED_KEYS`); this repo's own `.tasks/config.md`
  was updated by hand instead (added `tdd_enforced: true` + its own "Key notes" bullet), standing
  in for the interview since there's no separate human to ask here.
- 2026-09-18: Rewrote `implement-task/SKILL.md` phase 2's step 1: reads `tdd_enforced` from
  `.tasks/config.md` (default `true` if unset) and branches — `true` writes each Testing
  strategy step's/acceptance criterion's test(s) first, confirms they fail for the expected
  reason (not an unrelated error), then implements and re-runs until green, one
  criterion/step at a time; `false` keeps the original "write the change and its tests
  together" wording verbatim. Step 2 (the full `test_command`/`lint_command` run) is now
  explicit about being a final run "regardless of mode."
- 2026-09-18: Step 1 — extended `tests/test_init_project_scaffold.py`: a scaffolded config
  contains `tdd_enforced: true` by default (`test_render_config_fills_every_placeholder`,
  extended), and a `false` answer round-trips correctly (new
  `test_render_config_tdd_enforced_false_round_trips`). Also added `"tdd_enforced": True` to the
  shared `INIT_PROJECT_ANSWERS`/`SAMPLE_ANSWERS`/`RUN_ANSWERS` dicts in the 6 other test files
  that build a full `render_config`/`run` answers dict (`test_add_task_scaffold.py`,
  `test_implement_task_scaffold.py`, `test_plan_feature_scaffold.py`,
  `test_refine_backlog_scaffold.py`, `test_init_project_upgrade.py`, and
  `test_init_project_scaffold.py` itself) — `render_config` raises on a missing `REQUIRED_KEYS`
  entry, so every one of them would otherwise now fail.
- 2026-09-18: Step 2 — **reinterpreted, recorded here rather than skipped silently.** This step
  as written expects "the implement-task script['s test module]" to gain cases asserting the
  phase-2 write/fail/implement/pass step *order*. There is no such script: phase 2 is 100%
  prose-driven judgment (per `implement-task/SKILL.md`'s own architecture note — `scaffold.py`
  owns only deterministic git/gh/frontmatter actions, never phase 2's content), so there is
  nothing here for `pytest` to mechanically exercise — inventing a pure function nothing else
  calls, purely to have something to unit-test, would be dead code for its own sake. The real
  verification of step-ordering is step 5's live scratch dry run below; step 1's config-plumbing
  tests are the only mechanically-testable surface this change actually has.
- 2026-09-18: Step 3 — `.venv/bin/pytest`: 620 passed, 0 failed. Also re-ran the portable-surface
  guard tests specifically, since `init-project/SKILL.md`/`templates/config.md` and
  `implement-task/SKILL.md` all live under the portable skills surface — clean.
- 2026-09-18: Step 4 — `python3 .tasks/bin/sync check` exits 0.
- 2026-09-18: Step 5 (human-run, per the task's own testing strategy) — **skipped by explicit
  human decision**, asked before wrap-up rather than assumed. The change is config-schema +
  `SKILL.md` prose only, already covered by the automated config round-trip tests above; the
  human chose to verify the actual write-test-first/fail/implement/pass sequence live the first
  time a real task runs under `tdd_enforced: true`, rather than via a dedicated throwaway
  scratch-branch dry run first.

## Notes

- Independent of the batch/autonomy mechanism (TASK-039, 041-045) — could be implemented in any
  order relative to them once EPIC-002 is done.
