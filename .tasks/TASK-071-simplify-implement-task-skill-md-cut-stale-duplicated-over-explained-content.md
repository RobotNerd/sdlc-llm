---
id: TASK-071
title: "Simplify implement-task/SKILL.md: cut stale/duplicated/over-explained content"
type: docs
status: todo
epic: null
created: 2026-09-19
branch: task-071-simplify-implement-task-skill-md-cut-stale-duplicated-over-explained-content
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-071: Simplify implement-task/SKILL.md: cut stale/duplicated/over-explained content

## Description

A close read of `.claude/skills/implement-task/SKILL.md` (grown across TASK-024/046 and then
TASK-040/041/042/043 layering batch mode, TDD mode, and the interrupt/usage systems on top) found
concrete, specific cuts — not a vague "make it shorter" pass:

1. **Stale, now-contradictory content.** The top intro block's STOP-semantics paragraph still says
   "every other STOP in this file (a phase 2 decision, a rebase conflict, `phase4_closed_not_merged`,
   `ambiguous`, a `gh`/`git` failure) still applies exactly as written and halts the whole batch
   when it fires." That was true when TASK-041 wrote it, but TASK-042 replaced it: those conditions
   are now routed through "Interrupts" (isolated vs. systemic), not a blanket halt. The "Batch
   mode" section's own intro already states this correctly — the top block's restatement is both
   wrong and redundant with it. Delete the stale claim from the top block; point to "Batch mode"
   instead of re-describing it.
2. **A duplicated parameter explanation.** Step 1's opening ("with no task id parameter, that
   means `{"task_id": null}` right away, not a question to the human") repeats the top intro's
   Parameter paragraph almost verbatim. Keep it in one place.
3. **Two near-identical steps that should be one.** Batch mode's steps 3.1 and 3.4 ("Usage
   checkpoint, before this task starts" / "Usage checkpoint again, same call as step 3.1") run the
   exact same `check-usage-thresholds` procedure, described twice. State the checkpoint procedure
   once, and note the two points in the loop it runs at, instead of two full step write-ups.
4. **Internal mechanism narration that's already encoded in `scaffold.py` and doesn't change what
   the LLM does.** Step 3 (Wrap up)'s point 3 spells out `wrap-up`'s internal git sequence in
   detail (stash/pop around the rebase, exactly when `--force-with-lease` fires, the format-amend
   step) — useful as code comments (and they already exist there, in `cmd_wrap_up`), but the LLM
   only needs: what to pass in, what comes back, and what to do on the two failure exits (rebase
   conflict, non-zero `format_command`) — which are handled identically (STOP, fix by hand, re-run
   `wrap-up`) and are currently two separate bullets (point 4) that could be one. Similarly, the
   Guardrails section's "`wrap-up`'s push refuses outright..." bullet just re-narrates
   `decide_push_args`'s own docstring — it doesn't inform any LLM decision (the LLM never
   constructs push args by hand), so it can be dropped rather than kept as a third copy of the same
   fact (code, docstring, `SKILL.md`).
5. **General over-explanation pass.** Several parentheticals across the file justify *why* a rule
   exists (e.g. the merge-carve-out rationale in step 4, various asides in "Batch mode") where the
   *what to do* is what the LLM actually needs at run time. Where a justification doesn't change
   the action, trim it — but keep any rationale that helps the LLM judge an edge case correctly
   (e.g. why `context_pct` is a self-estimate stays, since that shapes how much to trust it).

Guiding test for every cut: **does removing this sentence change what the LLM should actually do at
that step?** If no, cut or shorten it. If yes, keep it.

## Acceptance criteria

- [ ] The stale post-TASK-042 STOP-semantics claim in the top intro block is removed or corrected
      to match "Batch mode"/"Interrupts", with no duplicate restatement of that routing.
- [ ] Step 1's parameter explanation no longer duplicates the top intro's Parameter paragraph.
- [ ] Batch mode's two usage-checkpoint steps (3.1/3.4) are consolidated into one described
      procedure, referenced at both points in the loop, not repeated in full twice.
- [ ] Step 3 (Wrap up)'s internal git-mechanism narration is trimmed to inputs/outputs/failure-mode
      handling; the rebase-conflict and format-command-failure bullets are merged (both resolve
      identically).
- [ ] The Guardrails section's bullet that only re-narrates `decide_push_args` is removed.
- [ ] Every phase's actual behavior (STOP points, ASK points, `scaffold.py` calls and their
      inputs/outputs, the Interrupts routing table) is unchanged — this is a wording/structure
      edit, not a behavior change.
- [ ] `python3 .tasks/bin/sync check` passes (docs aren't a generated region, but this confirms no
      incidental drift).

## Testing strategy

1. Line-by-line diff review: confirm every `scaffold.py` subcommand this file references
   (`resume-state`, `start`, `wrap-up`, `finish-merge`, `bail-out`, `record-outcome`,
   `render-outcome-table`, `classify-interrupt`, `check-usage-thresholds`, `render-usage-summary`,
   `gh-auth-status`) is still named with its correct inputs/outputs after the edit.
2. Confirm every STOP/ASK point present before the edit is still present after it (a simplification
   pass must not silently drop a checkpoint).
3. `python3 .tasks/bin/sync check` → exit 0.
4. No `pytest` run needed — this task touches no code, only `SKILL.md` prose.

## Worklog

_(empty — appended during implementation)_

## Notes

- Scope is deliberately limited to `.claude/skills/implement-task/SKILL.md` itself, per the
  request that prompted this task — not `scaffold.py`'s docstrings or other skills' `SKILL.md`
  files, even though some carry the same "historical decision" phrasing style.
- Not urgent: a pure readability/maintainability cleanup with no behavior change, hence end of
  TODO rather than competing with queued feature work.
