---
id: SPEC-005
title: implement-task v2 - batch-first, critic-gated, local-merge rewrite
status: draft
created: 2026-09-23
---

# SPEC-005: implement-task v2: batch-first, critic-gated, local-merge rewrite

## Problem

`implement-task` grew by layering batch mode, TDD mode, interrupt routing, a usage safety valve, follow-up creation and opt-in auto-merge onto a four-phase single-task skeleton. Its `SKILL.md` now describes two modes with contradictory rules — phase 1/phase 3 STOPs vs. batch-mode announcements and waits, "every STOP halts the batch" vs. isolated/systemic interrupt routing — and its behavior is split across ~400 lines of prose and ~2000 lines of `scaffold.py`/`batch_select.py`. A manual test of TASK-045 (critic-gated auto-merge) failed because the agent followed conflicting instructions. The GitHub PR round-trip (open a PR, wait on CI, wait for a human or the auto-merge path, observe the merge) is also the largest source of latency and machinery, and the human review it exists for is being replaced by a critic anyway. Wording cleanup (TASK-071) can't fix a structural problem: the skill needs one linear workflow, written from scratch.

## Goals

- A new skill, `implement-task-v2`, built from scratch next to v1: one linear workflow in a prose-only `SKILL.md`, with detail moved into `references/` docs that each step loads only when it needs them.
- Every invocation is a batch. No argument means the top unblocked TODO task (a batch of one); an optional argument selects a task list, a board-order range, a stopping task, or an epic. The batch is validated before any work starts.
- Local-only git flow: one local branch per task, squash-merged into `main`, then `main` is pushed. No PRs, no CI polling, no merge observation.
- A cheaper critic subagent (`model: "haiku"`) reviews every task's branch diff — code and docs — and must approve before the merge; a rejection loops back to rework, up to `critic_rejection_attempts`.
- TDD + BDD: behavioral tests are written first and committed; unit tests are throwaway by default.
- Interrupts pause the batch resumably. An interrupted batch (paused, or a lost session) is detected on the next invocation and resumed from the human-readable step name recorded in its batch state.
- Autonomous follow-up task creation, hard-capped by `autonomous_new_task_limit`; anything past the cap is recorded as a recommendation in the reports.
- Per-task and per-batch summary reports in `reports/`, including manual test steps for the human.
- Reimplement the usage safety valve (`context_usage_halt_pct`, `token_budget_per_batch`).
- Docs and `.tasks/config.md` describe v2, and this spec lists the behaviors that are candidates for later migration into a script.

## Non-goals

- Python automation for v2. The rewrite is prose-only; script migration is planned in later tasks after v2 has been manually tested and the prose has settled.
- Renaming v2 to `implement-task`, or deleting v1, its scripts, or its tests. The human does that cutover after this epic.
- Guardrail hooks for v2. Guardrails get rebuilt from the ground up later; during development only the one hook that blocks v2 (`pretooluse_bash.py`) is unregistered in this repo, and the other hooks stay active.
- PRs, GitHub CI gating, and v1's auto-merge machinery (`allow_auto_merge`, `autonomous_merge_cap`, the merge marker).
- Changes to EPIC-004 (external critic provider, orchestrator/worker roles). Revisit after cutover.
- Rewriting the existing `tests/` suite to the new testing strategy. The strategy applies to new work.
- Parallel task execution. One task at a time, one session.

## Alternatives considered

- **Simplify v1 in place (TASK-071).** Rejected: it cuts wording but keeps the two modes, the four phases and the PR flow that cause the conflicts.
- **Fork v1 and strip it down.** Rejected: it inherits the `phase1`..`phase4` structure, and every surviving sentence would need re-validating anyway. Writing from scratch is cheaper and gives a cleaner result.
- **Keep the PR flow with critic-gated auto-merge (v1's TASK-045 path).** Rejected: the GitHub round-trip adds latency, CI polling, `ScheduleWakeup` waits and hook-marker machinery, all for a review the critic now does locally.
- **Build v2 with scripts from day one.** Rejected: prose first lets the workflow be manually tested and settled before its behavior is frozen in code. Scripting an unsettled design means rewriting the script.
- **Do nothing.** Rejected: v1 is unreliable in the batch mode it was last extended for.

## Design

### Layout

```
.claude/skills/implement-task-v2/
  SKILL.md
  references/
    critic.md
    follow-up-tasks.md
    guardrails.md
    interrupts.md
    naming-conventions.md
    summary-report.md
    testing-strategy.md
```

`SKILL.md` holds the step list and nothing else. It names the reference doc that each step needs,
at the point where it's needed. While v2 is in development it's listed in init-project's
`_REPO_ONLY_SKILLS`, so `upgrade` doesn't vendor an unfinished skill into other projects. It's
removed from that list at cutover.

### Parameter

`[tasks|range|stopping-task|epic]` is optional and free-form. The agent parses it; there's no JSON
shape to learn:

| Mode | Example arguments |
|---|---|
| default (no argument) | — |
| epic | `EPIC-NNN` |
| list | `TASK-NNN TASK-MMM`, `tasks 44, 45, and 47`, a single `TASK-NNN` |
| range | `TASK-AAA..TASK-BBB`, `TASK-AAA through TASK-BBB` |
| stopping-task | `..TASK-BBB`, `through TASK-BBB`, `up to TASK-BBB` |

If the argument is ambiguous or doesn't parse, **ASK**. Never guess a mode.

### Workflow

The step names below are exact. The batch state's `step` field records them verbatim; they
replace v1's `phase1`..`phase4`. Steps 4–10 repeat for each task in the batch.

| # | Step | Loops back to |
|---|---|---|
| 1 | `ensure clean repo` | — |
| 2 | `detect interrupted batch` | — |
| 3 | `build batch` | — |
| 4 | `start task` | — |
| 5 | `write tests` | — |
| 6 | `implement task` | — |
| 7 | `run tests` | `implement task` (code is wrong) or `write tests` (a test is wrong) |
| 8 | `spawn critic` | `implement task` / `write tests` on rejection |
| 9 | `merge changes` | — |
| 10 | `create summary report` | `start task` for the next task in the batch |
| 11 | `batch complete` | — |

1. **ensure clean repo**
   - `gh` isn't installed → **STOP**.
   - The working tree is dirty (`git status --porcelain`, excluding `ignored_paths`) → **STOP**.
     The one exception: a batch state file exists, and the checked-out branch is that batch's
     active task branch. That's a resume, and step 2 handles it.
   - Update `main` from `<remote>`. On `main`, run `git pull --ff-only`. On a task branch being
     resumed, run `git fetch <remote> <default_branch>:<default_branch>`. If either fails,
     **STOP**.
2. **detect interrupted batch**
   - No batch state file → go to `build batch`.
   - State exists and the user gave an argument → **ASK**: resume the interrupted batch, or
     discard it and start the new one. Discarding checks out `main`, force-deletes the active
     task's local branch (after confirming, since that loses its commits) and deletes the state
     file. Nothing needs undoing on `main`, because a task's bookkeeping only reaches `main`
     through its squash merge.
   - State exists and there's no argument → resume. Report the batch, its active task, its
     `step` and its `interrupt` (if paused), then apply the user's decision for that interrupt
     (see `interrupts.md`). Check out the task branch and re-enter the recorded `step` from its
     beginning. `merge changes` is the one step that isn't idempotent: first check whether
     `main` already carries the task's squash commit (`git log --grep 'TASK-NNN'`) and skip
     whatever is already done.
3. **build batch**
   - Resolve the argument against `BOARD.md`'s hand-ordered TODO list. Every mode keeps board
     order. In epic mode that means TODO tasks whose `epic:` matches, in board order. This is a
     change from v1, which used id order.
   - Default mode: take the top TODO task that isn't blocked, and announce any blocked tasks it
     skipped.
   - Validate before any work starts. Any failure → **STOP** and ask for clarification:
     - *already implemented*: a task is `done`/`wont-do`, or has been archived.
     - *no stopping task*: the range end or stopping task doesn't exist or isn't on TODO.
     - *no tasks found*: the batch resolved to nothing.
     - *task blocked*: an outstanding `blocked_by` entry is outside the batch, or is inside it
       but ordered after the task it blocks.
     - *task does not exist*: no such task, or it isn't on TODO.
     - *wrong order for range*: the range end sits above its start on the board.
   - Announce the batch order and write the batch state. There's no confirmation STOP; the
     invocation is the approval.
4. **start task**
   - Run the usage checkpoint (`interrupts.md`).
   - Set the task as the batch's active task.
   - `git checkout -b <branch> <default_branch>`. The branch name comes from
     `naming-conventions.md`.
   - Set the task's `status: in-progress` and `branch:`, run `sync`, then commit.
   - Announce the plan: description, acceptance criteria, testing strategy and approach. Don't
     STOP.
5. **write tests** — follow `testing-strategy.md`: failing behavioral tests first, plus throwaway
   unit tests where they help. Commit the behavioral tests.
6. **implement task**
   - Change the repo to meet the acceptance criteria, and update `docs_paths` where the change
     touches them.
   - Stay within the task's scope. Out-of-scope work becomes a follow-up (`follow-up-tasks.md`).
   - Commit.
7. **run tests**
   - Run the quality gates: `test_command` (the full suite, throwaway tests included),
     `lint_command` and `format_command` (when not `null`), and `sync check`.
   - On failure, go back to `implement task` or `write tests`. Repeated failures count toward
     `quality_gate_attempts` (`interrupts.md`).
   - Testing strategy steps that need a human's hands are never run by the agent. They're
     collected for the report's Manual testing section.
8. **spawn critic** — run the usage checkpoint, then follow `critic.md`.
9. **merge changes**, in order:
   1. On the task branch, do the bookkeeping v1 did in phase 4. Append a Worklog entry, set
      `status: done`, then run `sync`, which archives the task and updates the epic and the
      board. Confirm `sync check`, then commit. `merge_commit` stays `null`: the squash commit
      can't record its own hash, and `git log --grep TASK-NNN` finds it.
   2. `git checkout <default_branch>`, `git merge --squash <branch>`, then commit with the
      message from `naming-conventions.md`.
   3. `git push <remote> <default_branch>`. If the push is rejected or fails, raise
      `infra_failure`.
   4. `git branch -D <branch>`. Squash commits aren't ancestors, so `-d` would refuse.
   5. Delete this task's throwaway unit tests.
   6. Mark the task merged in the batch state.
10. **create summary report** — write `reports/<branch>.md` (`summary-report.md`).
11. **batch complete** — reached when every task is merged or the batch pauses.
    - Write `reports/batch-%Y-%m-%d-%H-%M-%S.md` (`summary-report.md`).
    - On completion, delete the batch state and leave `main` checked out.
    - On a pause, keep the batch state.
    - Print the report path and headline, then **STOP**.

Every step that changes files on the task branch ends with a commit. The start and wip commits
are in `naming-conventions.md`. Commits make the critic's `git diff` complete and keep resume
points clean, and the squash merge folds them into one commit.

### Batch state

Path: `.tmp/batch-state-v2.json`. It's gitignored, and it's a different file from v1's
`.tmp/batch-state.json`, so the two skills never read each other's state.

```json
{
  "active_task": "TASK-NNN",
  "argument": "<as given, or null>",
  "follow_ups": [{"created": true, "parent": "TASK-NNN", "task_id": "TASK-NNN", "title": "...", "why": "..."}],
  "interrupt": null,
  "order": ["TASK-NNN", "..."],
  "started": "<ISO-8601 local time>",
  "step": "write tests",
  "tasks": {
    "TASK-NNN": {
      "attempts": {"critic_rejection": 0, "guardrail_denial": 0, "quality_gate": 0},
      "critic": [{"approve": false, "findings": ["..."]}],
      "merge_commit": null,
      "status": "pending | active | merged | skipped"
    }
  },
  "version": 2
}
```

`interrupt` is `null`, or `{"kind", "task_id", "step", "detail", "decision_needed"}`.
`follow_ups` entries with `created: false` are the recommendations that weren't created because
the limit had been reached.

### Config (`.tasks/config.md`)

v2 reads: `autonomous_new_task_limit`, `branch_prefix`, `context_usage_halt_pct`,
`critic_rejection_attempts`, `default_branch`, `docs_paths`, `format_command`,
`guardrail_denial_attempts`, `ignored_paths`, `lint_command`, `quality_gate_attempts`, `remote`,
`test_command`, `token_budget_per_batch`.

v2 ignores the following v1-only keys. The docs task **removes them from `.tasks/config.md`** (values and key notes). v1 still runs until cutover and falls back to its built-in defaults for the missing keys: `allow_auto_merge` off, `delete_branch_after_merge` true, `merge_strategy` squash, `rebase_before_pr` true, `tdd_enforced` true. The init-project template `config.md` stays unchanged until cutover, because vendored projects still run v1.

| Key | Why v2 ignores it |
|---|---|
| `allow_auto_merge`, `autonomous_merge_cap` | The critic always gates the merge. |
| `ci_checks`, `rebase_before_pr` | There are no PRs. |
| `delete_branch_after_merge` | The branch is always deleted. |
| `merge_strategy` | Always squash. |
| `tdd_enforced` | Always TDD. |

New `.gitignore` entries:

- `.tmp/batch-state-v2.json`
- `reports/`
- `tests/throwaway/`

### Reference documents (proposed content)

#### `references/naming-conventions.md`

- **NNN**: the numeric part of the task id (`TASK-NNN` → `NNN`).
- **slug**: the slug in the task's filename (`TASK-NNN-<slug>.md`), which `add-task` derived from
  the title. If the filename has none, kebab-case the title: lowercase, runs of
  non-alphanumerics → `-`, trim leading and trailing `-`.
- **Git branch**: `<branch_prefix><NNN>-<slug>` (`task-NNN-<slug>` with this repo's config).
  Normally identical to the task's existing `branch:` field.
- **Per-task report**: `reports/<branch>.md`, i.e. `reports/task-NNN-<slug>.md`.
- **Batch report**: `reports/batch-%Y-%m-%d-%H-%M-%S.md` (local time, when the report is
  written).
- **Batch state**: `.tmp/batch-state-v2.json`.
- **Commit messages** (conventional commits, citing the task id):
  - start: `chore(TASK-NNN): start task`
  - checkpoint: `wip(TASK-NNN): <step name>`
  - squash: `<type>(TASK-NNN): <task title>`. The body lists the acceptance criteria met and
    the follow-ups created. The task's `type` maps to the prefix:

    | Task `type` | Prefix |
    |---|---|
    | `bug` | `fix` |
    | `chore` | `chore` |
    | `docs` | `docs` |
    | `feature` | `feat` |
    | `refactor` | `refactor` |

#### `references/critic.md`

- **When**: `spawn critic`, after `run tests` is green and before `merge changes`.
- **Launch**: the Agent tool with `model: "haiku"`. The prompt carries:
  - the task id, title and task-file path
  - the branch name and base (`<default_branch>`)
  - one line per quality gate with its result

  The critic reads the rest itself: the task file,
  `git diff <default_branch>...<branch>` and `git diff --name-only <default_branch>...<branch>`.
  The critic is **read-only**. It must not edit, stage, commit, or run anything that changes the
  repo.
- **Checklist**: each item is answered `true`/`false`. It's a checklist, not an open-ended
  style review.

  | Item | Check |
  |---|---|
  | `criteria_met` | The diff satisfies every acceptance criterion. |
  | `docs_clean` | Docs changed wherever behavior changed (`docs_paths`, `SKILL.md`, references). Doc text is concise and accurate, and nothing stale is left behind. |
  | `gates_passed` | Every quality gate reported passing. |
  | `nothing_alarming` | No secrets, destructive or unrelated changes, or disabled tests or guardrails. |
  | `scope_ok` | Every changed file is within the task's scope. `.tasks/` bookkeeping and follow-up task files are always allowed. |
  | `sorted_order` | Lists and data structures whose order doesn't matter are sorted alphanumerically: imports, config keys, set/dict literals, doc bullet lists, table rows. |
  | `tests_behavioral` | Committed tests exercise behavior through the public surface. Unit tests are committed only when the Worklog justifies it. |

- **Reply**: exactly one JSON object:
  `{"approve": bool, "criteria_met": bool, "docs_clean": bool, "gates_passed": bool,
  "nothing_alarming": bool, "scope_ok": bool, "sorted_order": bool, "tests_behavioral": bool,
  "findings": ["..."]}`. `approve` can be `true` only if every item is `true`. If an item can't
  be verified, the answer is `false`.
- **Fail closed**: any of these is a rejection:
  - unparseable output
  - a missing or non-boolean key
  - `findings` that isn't a list of strings
  - `approve: true` alongside a `false` item

  Take the reply verbatim. Never edit or summarize it before judging it.
- **On rejection**:
  1. Record the findings in the task's Worklog and in the batch state's `critic` list.
  2. Increment `attempts.critic_rejection`.
  3. Return to `implement task`, or to `write tests` if the findings are about tests.
  4. Re-run `run tests`.
  5. Spawn a fresh critic.

  At `critic_rejection_attempts` rejections, raise the `critic_rejection` interrupt.
- **On approval**: go to `merge changes`. The findings from every round go into the per-task
  report.

#### `references/testing-strategy.md`

- **TDD, per acceptance criterion**:
  1. Write the behavioral test.
  2. Run it and confirm it fails *for the expected reason*: an assertion or behavior failure.
     An import error, syntax error or missing fixture means the test is broken; fix the test
     first.
  3. Implement until it passes, then move to the next criterion.
- **BDD**: test the surface, not the internals. Drive CLIs, script entry points, file outputs
  and skill-visible artifacts. Name tests after the behavior (`test_<behavior>_when_<condition>`).
  **Behavioral tests are committed**, in the project's normal test directory.
- **Unit tests are throwaway by default.** Write them under `tests/throwaway/`, which is
  gitignored but still collected by `test_command`. Delete them in `merge changes` after the
  squash merge. Unit tests go stale, becoming a burden, and their count balloons with little
  value per test, which bloats context.
- **Committing a unit test is rare**. It's allowed for code likely to change often, or code
  judged likely to regress. Record the justification in the Worklog; the critic's
  `tests_behavioral` item checks for it.
- **Prose-only changes** (a `SKILL.md`, docs): write a behavioral test where a mechanical check
  exists, for example that every referenced file exists or that the step names match. Everything
  else goes into the report's Manual testing section.
- **Manual steps**: the agent never runs steps that need a human's hands (real credentials,
  money, UI). They go into the per-task report's Manual testing section as numbered steps, each
  with its expected result.

#### `references/follow-up-tasks.md`

- **When to create one**:
  - The current task is too large and needs splitting.
  - Mid-task, you find a bug or a necessary feature outside the current task's scope.
- **How**:
  - Use the `add-task` skill with every answer pre-supplied, so it asks nothing: title, type,
    description, acceptance criteria, testing strategy, notes (citing the parent task and why),
    `blocked_by` (only for a real dependency) and `priority_mode: "end"` (the bottom of TODO).
  - Set `epic` only when the task clearly belongs to an existing epic; otherwise leave it
    `null`.
  - Create it on the current task branch, so it lands in that task's squash commit.
- **Splitting**: move the out-of-scope acceptance criteria to the new task, and note the split
  in the current task's Notes. The critic then judges the current task against its remaining
  criteria.
- **Limit**: before creating, count `follow_ups` with `created: true` in the batch state.
  - The limit is `autonomous_new_task_limit`: `null` means no cap, `0` means never create.
  - At the limit, create nothing. Record `{"created": false, "title", "why", "parent"}` in
    `follow_ups` and keep going. This isn't an interrupt. The recommendation appears in the
    per-task and batch reports.
- **Fully autonomous**: never stop to ask. The human reviews new tasks after the batch.

#### `references/interrupts.md`

An interrupt **pauses** the batch: the agent needs a decision from the human.

**Interrupt kinds:**

| Kind | Trigger |
|---|---|
| `context_usage_exceeded` | Usage checkpoint: estimated context usage ≥ `context_usage_halt_pct`. |
| `critic_rejection` | `critic_rejection_attempts` critic rejections on one task. |
| `guardrail_denial` | The same `PreToolUse` hook denies a retry `guardrail_denial_attempts` times in a row. |
| `infra_failure` | `git`/`gh` itself is broken: auth expired, network failure, rate limit, or a rejected push. |
| `needs_clarification` | The task is ambiguous, or its acceptance criteria contradict something found mid-implementation. |
| `quality_gate_failure` | One gate (`test_command`/`lint_command`/`format_command`/`sync check`) fails for the same reason `quality_gate_attempts` times in a row. |
| `token_budget_exceeded` | Usage checkpoint: `token_budget_per_batch` is set and the session's tokens used ≥ it. |
| `unexpected_blocker` | Something task-specific blocks progress, such as a dependency assumed done that isn't. |

**Attempt counters** live in the batch state per task. A counter counts consecutive failures
with the same reason, and resets when that gate passes or the human resolves the interrupt.

**Pausing**:

1. Append to the task's Worklog: the interrupt kind, the step, the detail, and the decision
   needed.
2. Commit it as `wip(TASK-NNN): <step name>`.
3. Set the batch state's `interrupt`. Leave `step` as it is.
4. Write the batch report with `Status: paused` (`batch complete`).
5. **STOP**, and ask the question.

**Resolving** happens on the next invocation (`detect interrupted batch`). The human picks one:

- **Resume**: continue at `step`, with the human's answer applied.
- **Skip the task (bail out)**: force-delete its branch and mark it `skipped` in the batch
  state. The task stays `todo` on `main`. Continue with the next task.
- **Discard the batch**: delete the state file and the active branch.

**Usage checkpoint** (run at `start task` and at `spawn critic`):

1. `context_pct` is the agent's honest estimate. No file records the context-window size, so it
   can't be measured exactly.
2. `tokens_used` is an exact sum from the session transcript:
   - The transcript is `~/.claude/projects/<escaped-cwd>/<session-id>.jsonl`, where those two
     components are the path segments just above `scratchpad` in the session's scratchpad
     directory.
   - Keep lines that have `message.usage`.
   - Drop streaming partials (entries with no `stop_reason`), except the last entry.
   - Sum `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
     `cache_creation_input_tokens`.
3. Check context first: `context_pct ≥ context_usage_halt_pct` raises `context_usage_exceeded`.
   Only then check tokens: a non-null budget with `tokens_used ≥` that budget raises
   `token_budget_exceeded`.
4. If the transcript can't be read or parsed, note it in the Worklog and check context only.
   That failure is never an interrupt itself.

The used/budget figures are recorded for the batch report's Usage section.

**Not interrupts**: reaching the follow-up limit, and a single test failure that the agent fixes.

#### `references/summary-report.md`

**Per-task** (`reports/task-NNN-<slug>.md`, written in `create summary report`):

```markdown
# TASK-NNN: <title>

- Epic: EPIC-NNN | none
- Branch: task-NNN-<slug>
- Squash commit: <short sha>
- Batch started: <ISO time>

## Summary
<2–5 sentences: what changed and why>

## Acceptance criteria
- [x] <each criterion>

## Tests
- Behavioral tests added/changed: <files>
- Throwaway unit tests: <count>, deleted
- Quality gates: <one line each>

## Critic
<rounds>; final verdict; findings from every round

## Manual testing
1. <step> — expected: <result>
(or "None")

## Follow-up tasks
- Created: TASK-NNN — <title> — <why>
- Recommended, not created (limit reached): <title> — <why>

## Notes
<deviations, surprises, anything the human should know>
```

**Batch** (`reports/batch-%Y-%m-%d-%H-%M-%S.md`, written in `batch complete`, and again at each
pause):

```markdown
# Batch <YYYY-MM-DD HH:MM:SS>

- Argument: <as given | none (top of TODO)>
- Status: complete | paused
- Started / ended: <times>
- Tasks: <N> selected, <M> merged

## Tasks implemented
| Task | Title | Squash commit | Report |

## Tasks not implemented
| Task | Title | Reason |   (paused at <step> / skipped / not started)

## Early stop
<kind, task, step, detail, decision needed>   (only when paused)

## New tasks created
| Task | Title | Why | From |

## Recommended tasks not created
- <title> — <why> (from TASK-NNN)

## Manual testing
<per task, copied from each per-task report>

## Usage
context <pct>% · tokens <used> (budget: <n | no cap>)
```

Every section is printed even when empty (`none`), so a reader never has to wonder whether it was
considered.

#### `references/guardrails.md`

None of v1's guardrails apply to v2. Guardrails will be rebuilt from the ground up in later work.
Only one of this repo's hooks blocks v2. `.claude/hooks/pretooluse_bash.py` denies pushing task
work to `default_branch`, which `merge changes` requires. Unregister it from this repo's
`.claude/settings.json`; the skeleton task does this. The other hooks stay registered and
active:

- `.claude/hooks/pretooluse_edit_write.py` blocks generated-region and epic-status edits, which
  v2 never needs.
- `.dev/hooks/check-portable-references.py` gates `gh pr create`, which v2 never runs.
- The `SessionStart` board-context hook.

The `pretooluse_bash.py` script and its init-project template registration are unchanged, so
vendored projects keep it. `tests/test_guardrails.py`'s settings-parity test is updated to
expect the unregistered hook. A denial from a hook that's still active counts toward
`guardrail_denial`.

### Automation candidates (later tasks, not this epic)

Each of these is deterministic and moves into a v2 script once the prose has settled:

- Batch state: read, write, advance, and progress/resume lookup.
- Batch argument parsing, resolution and validation. v1's `batch_select.py` is a starting point.
- Clean-repo, `gh`-present and update-`main` checks, including the resume exception.
- Critic prompt assembly, and fail-closed verdict parsing.
- `merge changes`: bookkeeping, `sync`, squash, push, branch deletion, throwaway-test cleanup.
- Quality-gate runner with same-reason attempt counters.
- Report rendering, per-task and batch.
- `start task` bookkeeping: branch, frontmatter, `sync`, commit.
- Usage checkpoint: transcript token sum and threshold check (v1's `compute_session_token_usage`
  / `check_usage_thresholds`).
- Follow-up limit check and recording.

### Docs

- `README.md`, `CLAUDE.md`, `.tasks/guidelines.md`, and its init-project template mirror all say
  that `implement-task-v2` is in development next to `implement-task`.
- `CLAUDE.md`'s Guardrails section notes v2's local squash-merge and push to `main`, and that
  `pretooluse_bash.py` is unregistered in this repo; the other hooks are still enforced.
- `.tasks/config.md` drops the v1-only keys listed under Config, along with their key notes. The
  remaining key notes say which skill reads each key.

<!-- BEGIN:epics (generated by sync — do not edit) -->
| Epic | Status | Progress |
|---|---|---|
| EPIC-005 | todo | 0/9 done |
<!-- END:epics -->
