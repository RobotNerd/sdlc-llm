---
id: TASK-045
title: Opt-in, critic-gated, per-batch-capped auto-merge
type: feature
status: in-progress
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

- [x] `allow_auto_merge` defaults to `false`; auto-merge never happens unless a project explicitly
      sets it `true`.
- [x] The critic pass runs on a distinctly cheaper/faster model than the implementer, scoped to
      the checklist above — not an open-ended review.
- [x] A critic rejection skips auto-merge for that task only (isolated interrupt) and leaves the
      PR open for a human, without halting the batch.
- [x] `autonomous_merge_cap` halts the batch once reached, regardless of further approvals.
- [x] `gh pr merge` is only ever invoked through this path when enabled, and TASK-032's guardrail
      hook's marker check actually allows it in that case (verified against the real hook, not
      just this task's own code).
- [x] The end-of-batch summary includes critic findings per reviewed task.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

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

- Tests first (guardrail/marker: 27 failing; pure logic: 58 failing; CLI: 17 failing -- each for the expected reason: functions/subcommands absent), then implemented until green. Full suite 858 passed, `sync check` exit 0.
- **Merge path.** `scaffold.py auto-merge` is the only code that runs the merge. Gates in fixed order: `allow_auto_merge` is `true` -> `autonomous_merge_cap` not reached (a halt, regardless of critic/CI) -> PR still `OPEN` -> live head equals the head the critic reviewed (`--match-head-commit` pins the merge to it) -> `gh pr checks` green (pending waits; no CI is *not* green) -> changed files within `scope_paths` or `.tasks/` (a deterministic backstop for the critic's own scope check) -> critic approval. Every refusal exits 0 with `{merged:false, reason, halt, interrupt, findings}`.
- **Critic.** The script cannot call a model, so `SKILL.md` has the LLM launch a subagent on `haiku` with the script-built prompt (`critic-prompt`: four checklist items -- criteria met / in scope / gates passed / nothing alarming -- plus acceptance criteria, changed files, gates, diff, explicitly NOT a general code review; diff capped at 60k chars, and the critic is told to reject what it can't verify). `evaluate_critic_verdict` **fails closed**: approval needs a parseable object with `approve` and all four items exactly `true` and `findings` a list of strings; a false item alongside `approve: true`, a string `"true"`, prose, or `{}` are all rejections.
- **Marker + hook (verified against the real hook).** `guardrails.py`: `write_auto_merge_marker`/`clear_auto_merge_marker`/`auto_merge_marker_valid`; `evaluate_bash_command` now passes `marker_present=auto_merge_marker_valid(...)` into the unchanged-shape `check_gh_pr_merge`. A Bash merge is allowed only if `allow_auto_merge: true` AND a marker exists for exactly that PR AND the command carries `--match-head-commit <the marker's sha>` AND it hasn't expired (5 min TTL). `auto-merge` writes the marker, asks the real `evaluate_bash_command` about its own exact command before running it, and removes the marker in a `finally`. Tests run the actual hook scripts over stdin (allowed with the marker, denied without / wrong PR / wrong head / expired / opt-in off), and the CLI test's fake `gh` asserts the marker existed at the moment of the merge and is gone afterwards.
- **Tamper hardening.** Any Bash command naming the marker file, and any Edit/Write targeting it, is denied. Honest limit: it's a speed bump for a cooperative agent, not a security boundary (same posture as every other guardrail). Side effect worth knowing: *any* dev command mentioning that filename is denied too -- it blocked one of this task's own commands mid-implementation, working as intended (test code was written via the Write tool instead).
- **Human decision at plan approval -- critic rejection bails out and ENDS the batch** (changed from the originally proposed "skip and continue"): new routing `bail_out_halt` for `critic_rejection` (`continue_batch: false`): bail-out the task (`todo`), record it, print the summary, `batch-clear` (removes the batch state and any marker). The PR is deliberately left open on GitHub for the human -- closing a PR/branch is an outward-facing action left to them; the Worklog note tells them so. `auto_merge_cap_reached` is a new *systemic* kind (task untouched, PR open).
- **Summary** now opens with `render-batch-result`: tasks selected, tasks completed, which task (and interrupt kind/reason) ended it early, and which never started; plus `render-critic-summary` (findings per reviewed task, approvals included) fed by a new `critic_reviews` ledger in the batch state (optional key, old files read back with `[]`).
- Config: `autonomous_merge_cap: 5` (`null` unlimited, `0` never) in `templates/config.md` and this repo's `.tasks/config.md`; `allow_auto_merge` stays `false` here and in every scaffolded project; Key notes rewritten (they said "not currently read by anything"). `init-project`'s generic `migrate-config` adds the new key to existing projects and preserves their `allow_auto_merge`. `README.md`/`CLAUDE.md` guardrail text now names the one opt-in exception. `vendored-guardrails` mirrored byte-for-byte; the marker path is also in `.gitignore` and in every dirty-tree ignore list.
- Known limitation (pre-existing, not introduced here): non-critic refusals (`checks_not_green`, `scope_violation`, `head_moved`, `pr_not_open`) fall back to the ordinary human-merge wait; if a batch is ever left with two in-flight tasks, `resume-state` reports `ambiguous` and asks a human.
- **Testing strategy step 6 (real critic-approved auto-merge on a scratch project) is NOT run -- pending, human-run, per the human's decision to list it in the PR body.** It needs a scratch GitHub repo with `allow_auto_merge: true`: run a trivial task through a one-task batch to a real critic-approved merge, then confirm (a) the merge landed with `--match-head-commit`, (b) the marker file is gone, (c) `critic_reviews`/summary show it. I never ran a real `gh pr merge` in this session.

## Notes

- The single biggest behavior change in this epic — it's the one place this workflow's standing
  "a human always reviews and merges" guardrail gets a deliberate, capped, opt-in exception. Keep
  the default (`allow_auto_merge: false`) untouched by every other task in this repo.
- Coordinate the exact marker format with TASK-032 if that task is picked up by a different
  sitting than this one — its Notes point back here.
