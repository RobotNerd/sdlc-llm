---
id: TASK-025
title: "refine-backlog: move mechanical steps to a stdlib script; activity-aware stale detection"
type: refactor
status: in-review
epic: EPIC-001
created: 2026-09-14
branch: task-025-refine-backlog-script-split
pr: "https://github.com/RobotNerd/sdlc-llm/pull/35"
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

- [x] A stdlib-only Python script under `.claude/skills/refine-backlog/` performs: the resync
      step (`sync` then `sync check`), the blocked-chain report (reading `BOARD.md`'s `⛔`
      markers and the tasks they name), the under-specified scan (flagging any `todo`/`blocked`
      task whose Acceptance criteria or Testing strategy section is empty or still carries
      template placeholder text), and applying a confirmed TODO reorder (moving the exact
      rendered line, then confirming `sync check` stays clean).
- [x] The stale-`todo` scan is reimplemented as **active-days-elapsed**: for each `todo` task,
      count distinct calendar days with ≥1 commit to `default_branch` strictly between its
      `created` date and today (via `git log`), and flag it only if that count exceeds a
      threshold (default 30, kept as a constant in the script — not a `config.md` field, same as
      today). A repo dormant for months and just resumed must not flag every pre-existing task.
- [x] `SKILL.md` is rewritten so its own prose covers only the human-facing proposals and
      decisions (which `wont-do`/re-interview/reorder suggestions to act on) — each backed by one
      script invocation for the mechanical computation and reporting.
- [x] Unit tests (`pytest`) cover: active-days-elapsed against a fixture git history with a
      deliberate multi-week gap (must not flag a task created right before the gap once resumed),
      the under-specified scan's placeholder/empty detection, and the blocked-chain report against
      a mixed-status fixture.
- [x] Every guardrail already in `SKILL.md` (propose, don't act unilaterally on `wont-do` or
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

- 2026-09-14: Built `.claude/skills/refine-backlog/scaffold.py` (stdlib only), four subcommands:
  `resync` (bare `sync` then `sync check`), `report` (blocked-chain + stale-`todo` +
  under-specified, one call), `mark-wont-do`, `reorder`. Imports the repo's own `.tasks/bin/sync`
  by file path (same technique TASK-022/024 used) and reuses `discover`/`load_config`/
  `Artifact.write()`/`render_todo_line`/`_TODO_HEADING`/`_TODO_LINE_RE` rather than
  re-implementing any of it — `reorder` in particular reuses `sync`'s own `render_todo_line` so
  every rewritten line is byte-identical to what `sync` itself would render.
- **Active-days-elapsed** (`active_days_elapsed`): `git log <default_branch> --since=<created>
  --date=short --pretty=%ad`, collected into a set of distinct calendar days, discarding the
  `created` day itself ("strictly after"). Tested against a real backdated git history (not
  mocked, since the whole point is real commit dates): a task `created` right before a ~200-day
  dormant gap, with only 2 active days before the gap and 2 after resuming (3 total after
  `created`), stays well under the 30-day threshold — proving the fix's actual point, that a
  project resumed after a long break doesn't get every pre-existing task flagged. A second
  fixture with 35 consecutive real active days after `created` correctly exceeds the threshold.
- **Real bug caught by testing against the live board** (testing-strategy step "run against the
  real board first", same precedent TASK-017 itself set): the first `underspecified_scan`
  implementation flagged TASK-028 as having placeholder Acceptance criteria — false positive.
  TASK-028's actual criteria are fully concrete; one bullet just *mentions* `{{placeholder}}`
  syntax in prose ("not a `{{placeholder}}`, documented under..."), and the naive check
  (`"{{" in line`) matched that substring anywhere in a line regardless of context. Fixed by
  requiring the *entire* line, after stripping list/checkbox/number markup, to be nothing but the
  placeholder token itself (`^\{\{\w+\}\}$`) — a real unfilled placeholder from `task.md`'s
  template is always alone on its line (e.g. `- [ ] {{criterion}}`), so this stays precise while
  no longer matching prose that merely references the syntax. Added a regression test
  (`test_underspecified_scan_does_not_flag_prose_that_mentions_placeholder_syntax`) using
  TASK-028's actual bullet text as the fixture. Confirmed fixed: `report` run again against the
  real board now returns `underspecified: []`.
- Blocked-chain report (`blocked_chain_report`): reuses `sync`'s own `_TODO_LINE_RE` to find `⛔`
  markers and each named blocker's current status, so a transitive chain (a blocker that's
  itself still blocked, or in-progress) is visible in the report without recursing — `SKILL.md`
  narrates it. Run against the real board: correctly reported the real EPIC-002/003 dependency
  chains (e.g. TASK-039 blocked by seven still-`todo` EPIC-002 tasks), with TASK-025 itself
  (this task) correctly shown as the `in-progress` blocker for TASK-027 — proves the report
  reflects live state, not a fixture.
- `reorder`: takes the complete new TODO ordering, refuses (nothing written) unless it's exactly a
  permutation of the current `todo` set (missing/unexpected/duplicate ids all named in the error),
  otherwise rewrites the TODO section and confirms `sync check`.
- **Tests** (`tests/test_refine_backlog_scaffold.py`, 20 new — 19 first pass + 1 regression):
  `active_days_elapsed` (dormant-gap-not-flagged, sustained-activity-flagged) against real
  backdated git history; `stale_todo_scan` (uses the threshold, skips non-`todo`);
  `underspecified_scan` (placeholder/filled/vague/mentions-syntax/skips-done-and-in-progress);
  `blocked_chain_report` (mixed-status fixture, empty case); `apply_reorder` (applies order,
  refuses missing/unexpected/duplicate) as pure function tests; `resync`/`report`/`mark-wont-do`/
  `reorder` subcommands exercised as real subprocesses against a scratch repo built via
  `init-project`'s and `add-task`'s own scaffold scripts.
- Full suite: `pytest` 300 passed (280 prior + 20 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout, including after the live `report`/`reorder` runs against it.
- Re-read `SKILL.md` (testing strategy step 5): every remaining step is either a human-facing
  proposal/decision (narrate the blocked chain, ask about `wont-do`/re-interview/reorder) or
  exactly one `scaffold.py` call for the mechanical part.
- **CI failure found post-PR, fixed here** (user caught it: "test step failed... I think on
  `test_report_flags_add_tasks_unfilled_body_placeholders`"): the `test` job failed on GitHub
  Actions with `subprocess.CalledProcessError: Command ['git', 'log', 'main', ...] returned
  non-zero exit status 128` inside `active_days_elapsed`. Root cause: the `repo` test fixture did
  a bare `git init` and relied on git's `init.defaultBranch` config defaulting to `main` — true on
  this machine, not necessarily true on the GitHub Actions runner (whose initial branch turned out
  to be something else) — while the fixture's own `config.md` hardcodes `default_branch: "main"`.
  `git log main` then failed with "unknown revision" since no local branch was literally named
  `main`. Confirmed the root cause (not a guess) by reproducing locally with
  `GIT_CONFIG_GLOBAL=<a config forcing init.defaultBranch=master>`, seeing the same failure, then
  confirming the fix (explicitly `git checkout -b main` right after `git init`, matching what the
  `git_repo` fixture in the same file already did correctly) passes under that same simulated
  config. Not a production bug — `active_days_elapsed` querying `git log <default_branch>` is a
  reasonable assumption for this tool's real usage (a solo dev's own already-initialized repo,
  where `default_branch` is virtually always a real local branch), just an under-specified test
  fixture. `pytest` 300 passed again after the fix, including under the simulated CI-like config.
- **Separately flagged for the human, not fixed here (out of this task's scope):** while
  investigating, found that `implement-task`'s `wrap-up` (TASK-024) records `pr:`/
  `status: in-review` and runs `sync` *after* pushing and opening the PR, but never commits+pushes
  that resulting change itself — leaving it as local, uncommitted drift on the task branch unless
  a human/LLM operator notices and does a manual follow-up commit+push (exactly the "record PR,
  set status in-review" bookkeeping step done by hand for TASK-022/024 before `wrap-up` existed).
  This task's own PR (#35) hit exactly that: `wrap-up` opened it, but its `pr:`/`status`/board
  update sat uncommitted until caught here and pushed as a manual follow-up. `implement-task/
  scaffold.py` is a different skill's file, out of TASK-025's scope to fix — worth a follow-up
  task so every future `wrap-up` call doesn't silently leave the same gap.

## Notes

## Notes

- No hard dependency — TASK-017 (what this refactors) is already done.
- Placed at the bottom of TODO — decided with the user via `add-task`'s priority-placement step.
- The active-days-elapsed design was chosen over two alternatives (last-commit-anchored
  wall-clock, raw commit-count) after an explicit analysis-and-recommendation pass with the user
  during this task's own creation — see Description for the comparison.
