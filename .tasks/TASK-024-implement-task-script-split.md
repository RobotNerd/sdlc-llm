---
id: TASK-024
title: "implement-task: move deterministic git/gh actions to a stdlib script"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-13
branch: task-024-implement-task-script-split
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-027, TASK-028]
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

- [ ] A stdlib-only Python script under `.claude/skills/implement-task/` provides every git action
      above (dirty-tree check, fetch+branch, rebase with the prompts.md stash/pop, push with the
      plain-vs-`--force-with-lease` decision, post-merge checkout+pull, branch deletion).
- [ ] The same or a sibling script wraps every `gh` action above (`gh auth status`, `gh pr
      create` returning the URL, `gh pr view` polling, `gh pr checks`).
- [ ] The resume-detection table (§0) is a single script function/command, not re-derived by hand.
- [ ] The script also owns: TODO-picking (skipping blocked tasks), branch-name/slug construction,
      every `sync`/`sync check` call, and the frontmatter field edits (`status`, `branch`, `pr`,
      `merge_commit`) currently described as hand-edits.
- [ ] `SKILL.md`'s remaining prose covers only genuinely non-mechanical steps (plan approval,
      writing code/tests, judging what's automatable, composing commit/PR content, the bail-out
      judgment call) — each paired with exactly one script invocation for the mechanical part.
- [ ] Every git/gh guardrail already in `SKILL.md` is enforced *in the script*, not only
      documented in prose — e.g. the push function refuses `--force-with-lease` on any branch
      other than the current task's own, and refuses to push task work to `default_branch`
      (the phase-4 bookkeeping commit is the one scripted exception).
- [ ] Unit tests (`pytest`) cover: the resume-detection function against every row of §0's table,
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

_(empty — appended during implementation)_

## Notes

- No hard dependency — TASK-016 (what this refactors) is already done.
- Placed at the bottom of TODO, after TASK-023 — decided with the user via `add-task`'s
  priority-placement step.
- Likely the largest of the three script-extraction tasks (021/022/this one), given
  `implement-task` is itself "the largest skill" per its own Notes — flagged here in case
  implementation reveals it should split, rather than assumed to fit one sitting no matter what.
