---
id: TASK-024
title: "implement-task: move deterministic git/gh actions to a stdlib script"
type: refactor
status: in-review
epic: EPIC-001
created: 2026-09-13
branch: task-024-implement-task-script-split
pr: https://github.com/RobotNerd/sdlc-llm/pull/34
merge_commit: null
blocked_by: []
blocks: [TASK-027, TASK-028, TASK-031]
---

# TASK-024: implement-task: move deterministic git/gh actions to a stdlib script

## Description

Same pattern as TASK-021/TASK-022, applied to `implement-task` — the largest and most
guardrail-sensitive skill, since it's the one actually running `git`/`gh`. Its own Notes already
anticipated this ("if the phase-3/4 git sequence proves unreliable as checklist prose, extract it
into a small helper... deferred for now"): move every deterministic git/gh action, and the other
mechanical steps identified below, into a stdlib-only Python script. `SKILL.md` shrinks to what's
genuinely judgment or content-authoring — restating the plan, writing code/tests, deciding what's
automatable, composing commit/PR text, the bail-out call itself — each followed by one script
invocation to actually perform the mechanical part.

Deterministic candidates:

- **Git actions**: dirty-tree check (ignoring `.tmp/prompts.md`), `git fetch` + branch creation
  from `<remote>/<default_branch>`, rebase onto it (stashing/popping `.tmp/prompts.md` around it),
  push (plain, or `--force-with-lease` only when the rebase actually rewrote pushed history),
  post-merge `checkout <default_branch> && pull --ff-only`, branch deletion (local + remote,
  tolerating an already-gone remote branch).
- **`gh` actions**: `gh auth status`, `gh pr create` (given title/body, returns the URL),
  `gh pr view --json state,mergeCommit,statusCheckRollup` (polling), `gh pr checks`.
- **Resume-detection (§0's table)**: given working-tree state, branch existence, frontmatter, and
  live `gh pr view` state, return which phase to resume at (or report an ambiguous state) as a
  single lookup, not re-derived by hand each invocation.
- **Other mechanical steps found on inspection**: picking the top unblocked TODO task (reading
  `BOARD.md`, skipping `⛔`-marked lines), branch-name construction
  (`<branch_prefix><id>-<slug>` from the task title), every `sync`/`sync check` invocation the
  skill currently calls out individually, and the frontmatter field edits (`status`, `branch`,
  `pr`, `merge_commit`) the skill currently describes as hand-edits.

## Acceptance criteria

- [x] A stdlib-only Python script under `.claude/skills/implement-task/` provides every git action
      above (dirty-tree check, fetch+branch, rebase with the prompts.md stash/pop, push with the
      plain-vs-`--force-with-lease` decision, post-merge checkout+pull, branch deletion).
- [x] The same or a sibling script wraps every `gh` action above (`gh auth status`, `gh pr
      create` returning the URL, `gh pr view` polling, `gh pr checks`).
- [x] The resume-detection table (§0) is a single script function/command, not re-derived by hand.
- [x] The script also owns: TODO-picking (skipping blocked tasks), branch-name/slug construction,
      every `sync`/`sync check` call, and the frontmatter field edits (`status`, `branch`, `pr`,
      `merge_commit`) currently described as hand-edits.
- [x] `SKILL.md`'s remaining prose covers only genuinely non-mechanical steps (plan approval,
      writing code/tests, judging what's automatable, composing commit/PR content, the bail-out
      judgment call) — each paired with exactly one script invocation for the mechanical part.
- [x] Every git/gh guardrail already in `SKILL.md` is enforced *in the script*, not only
      documented in prose — e.g. the push function refuses `--force-with-lease` on any branch
      other than the current task's own, and refuses to push task work to `default_branch`
      (the phase-4 bookkeeping commit is the one scripted exception).
- [x] Unit tests (`pytest`) cover: the resume-detection function against every row of §0's table,
      branch-name/slug construction, the push-mode decision, and TODO-picking with a mix of
      blocked/unblocked tasks.

## Testing strategy

1. Unit-test the resume-detection function against every row of §0's table (fixture inputs, no
   real git needed).
2. Unit-test branch-name/slug construction against real task titles already in `.tasks/archive/`.
3. Dry-run the script's git/gh wrapper functions against a scratch task on a scratch branch (same
   throwaway approach TASK-016 itself used) — confirm the mechanical steps it now owns produce
   the identical outcome TASK-016 already proved by hand.
4. Confirm the script's push function refuses `--force-with-lease` on any branch but the current
   task's own, and refuses to push task work to `default_branch`.
5. Re-read `SKILL.md` and confirm its remaining prose is judgment/content-authoring only, with
   exactly one script call for every mechanical step it used to describe as prose.

## Worklog

- 2026-09-14: Built `.claude/skills/implement-task/scaffold.py` (stdlib only). Rather than one
  action per git/gh call, subcommands are consolidated per phase-checkpoint (matching "each paired
  with exactly one script invocation"): `resume-state` (§0, no input), `start` (phase 1: dirty
  check, TODO-pick or validate a given id, fetch+branch, set status/branch, sync), `wrap-up`
  (phase 3: add+commit, rebase w/ prompts.md stash/pop, push, `gh pr create`, record pr/status,
  sync, `gh pr checks`), `finish-merge` (phase 4: `gh pr view`, and if `MERGED` — checkout+pull,
  record merge_commit/status, sync/archive, branch cleanup, `sync check`, the phase-4 bookkeeping
  commit+push), `bail-out`, and `gh-auth-status`. Imports the repo's own `.tasks/bin/sync` by file
  path (same technique TASK-022 used) and reuses `discover`/`load_config`/`Artifact.write()`/
  `_TODO_HEADING`/`_TODO_LINE_RE` rather than re-implementing any of that.
- Four pure, unit-tested decision functions carry the logic AC7 asks for, kept separate from all
  git/gh/filesystem I/O so they're testable with plain fixtures:
  - `resume_phase(in_flight, working_tree_dirty, gh_pr_state)` — SPEC-001 §0's table as a pure
    function; the real gathering (branch existence, `gh pr view`) lives only in `cmd_resume_state`.
  - `pick_top_unblocked(board_text, sync_mod)` — reuses `sync`'s own `_TODO_LINE_RE` to find the
    first TODO line without a `⛔` marker, returning the skipped ones too.
  - `decide_push_args(...)` — raises before building any command if `current_branch` isn't the
    task's own branch, or if it's `default_branch`; otherwise returns plain or
    `--force-with-lease` push args. This *is* the guardrail enforcement AC6 asks for, not just
    documentation of it.
  - `compute_branch_name(prefix, id, slug)` / `slugify(title)` — see the surprise below.
- **Implementation surprise worth flagging:** AC/testing-strategy step 2 describes "branch-name/
  slug construction... against real task titles already in `.tasks/archive/`" as if a slug were
  mechanically derivable from a task's full title. It isn't, in this repo's real data — e.g.
  TASK-016's title "implement-task skill: four phases, STOP markers, resumable, bail-out" got the
  branch `task-016-skill-implement-task`, not a `slugify(full title)` result. Real slugs are short,
  separately hand-chosen summaries. What's actually mechanical (and what `compute_branch_name`
  does) is the `<prefix><number>-<slug>` *join*, given a slug from somewhere — normally a task's
  already-set `branch:` field (the common case, since `add-task` always sets it at creation);
  `slugify(title)` only exists as a last-resort fallback for a task with no `branch:` set at all,
  and the dry run below exercised exactly that path. Tested the join formula against every real
  archived+active task by round-tripping: split each one's stored `branch` into its slug suffix,
  feed it back through `compute_branch_name`, confirm it reproduces the original exactly (24+ real
  branches, all pass) — documented in the test itself so this doesn't look like an AC shortcut.
- TODO placement: `pick_top_unblocked` skips every `⛔`-marked line and reports why; `start` refuses
  outright (no branch created) if an explicitly-given task is still blocked or not `todo`.
- **Live dry run** (testing strategy step 3, same throwaway approach TASK-016 itself used): cloned
  the real repo into an isolated scratch directory (so it couldn't touch this feature branch or the
  real backlog), added a throwaway `TASK-900` scratch task, committed it *locally only* (never
  pushed) so the scratch clone's tree was clean, then invoked the real (uncommitted)
  `implement-task/scaffold.py` from this branch against that clone via `cwd`:
  1. `start --task_id TASK-900` (branch field deliberately left `null` in the scratch task, to
     exercise the `slugify` fallback for real) — created `task-900-scratch-dry-run-...`, correctly
     recreated the task file post-checkout (from its in-memory `Artifact`, since the file didn't
     exist on real `origin/main`), set `status`/`branch`, ran `sync`.
  2. `wrap-up` — committed, rebased (no-op, nothing new upstream), pushed (plain — first push),
     `gh pr create` opened a real throwaway PR (#33, base `main`) against `RobotNerd/sdlc-llm`,
     recorded `pr:`, ran `sync`, reported `gh pr checks` (initially none configured yet).
  3. `finish-merge` while the PR was still `OPEN` → `{"merged": false, "state": "OPEN", ...}`, real
     CI checks now visible (`sync-check` pass, `test` pending) — confirms the not-yet-merged
     reporting path against live GitHub state.
  4. Closed PR #33 without merging (`gh pr close`, never `gh pr merge`); re-ran `finish-merge` →
     `{"merged": false, "state": "CLOSED", ...}` — confirms that branch too.
  5. Cleanup: deleted the remote throwaway branch, deleted the entire scratch clone. Confirmed the
     real repo carries zero residue (`git status` on the real feature branch unaffected throughout;
     PR #33 closed, branch gone).
  - `finish-merge`'s `MERGED` branch (checkout+pull, record `merge_commit`, archive, branch
    cleanup, bookkeeping commit+push) was **not** re-proven by actually merging something —
    running `gh pr merge` even on a throwaway PR would mean personally executing the exact command
    this workflow forbids, undercutting the guardrail rather than testing it (same call TASK-016's
    own Worklog made). Citing the strongest evidence instead: this exact sequence is precisely what
    TASK-022's own real phase 4 required by hand earlier this session (checkout+pull, set
    `merge_commit`/`status`, `sync`, `branch -d` falling back to `-D` on the squash-merge case,
    `sync check`, commit+push to `main`) — the script's `finish-merge` is a direct, unmodified
    port of those same steps.
- Testing-strategy step 4 (push-mode/guardrail refusals): covered as pure `decide_push_args` unit
  tests (wrong branch, `default_branch`) rather than live git — no real command is even built in
  the refusal case, so there's nothing further a live run would prove.
- **Tests** (`tests/test_implement_task_scaffold.py`, 34 new): the four pure functions above
  (resume_phase's every table row + ambiguous cases, compute_branch_name/slugify + the real-data
  round trip, decide_push_args' plain/force/both-refusal cases, pick_top_unblocked's
  first-unblocked/skip/all-blocked/empty cases); `cmd_start`/`cmd_bail_out`/`cmd_resume_state`
  exercised as real subprocesses against a scratch repo with a genuine bare "origin" remote (built
  via `init-project`'s and `add-task`'s own scaffold scripts) — dirty-tree refusal, auto-pick with
  a blocked task skipped, explicit-id refusals (not `todo`, still blocked), successful start
  (branch + frontmatter + `sync check` clean), bail-out (revert + refuse-unknown-status),
  resume-state's phase1/phase2/phase3 against real repo state.
- Full suite: `pytest` 280 passed (246 prior + 34 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout, including immediately after the live dry run's cleanup.
- Re-read `SKILL.md` end to end (testing strategy step 5): every remaining numbered step is either
  content/judgment (interview-equivalent restatement, code+tests, composing commit/PR text, the
  bail-out decision) or exactly one `scaffold.py` call — no leftover hand-edit instructions.

## Notes

- No hard dependency — TASK-016 (what this refactors) is already done.
- Placed at the bottom of TODO, after TASK-023 — decided with the user via `add-task`'s
  priority-placement step.
- Likely the largest of the three script-extraction tasks (021/022/this one), given
  `implement-task` is itself "the largest skill" per its own Notes — flagged here in case
  implementation reveals it should split, rather than assumed to fit one sitting no matter what.
