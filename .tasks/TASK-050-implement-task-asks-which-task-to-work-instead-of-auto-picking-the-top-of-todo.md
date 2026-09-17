---
id: TASK-050
title: implement-task asks which task to work instead of auto-picking the top of TODO
type: bug
status: in-progress
epic: EPIC-001
created: 2026-09-16
branch: task-050-implement-task-asks-which-task-to-work-instead-of-auto-picking-the-top-of-todo
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-050: implement-task asks which task to work instead of auto-picking the top of TODO

## Description

Running `/implement-task` with no argument on a clean tree with nothing in flight should go
straight from `resume-state` (`{"phase": "phase1"}`) into `start {"task_id": null}` — the
documented auto-pick default. Instead the skill stopped and asked:

> Still nothing in progress — ready to start a new task. Auto-pick the top of TODO, or work a
> specific task?

Transcript evidence (`151843ca-2d33-4988-823a-de714081c5c3.jsonl`, rows 733–737) shows the
mechanics were fine: `scaffold.py resume-state` correctly returned `phase1`. After the human
pushed back, the same invocation ran `start` with `{"task_id": null}` and picked TASK-031
correctly (rows 750–756) — so `scaffold.py` needs no change. The bug is entirely in
`.claude/skills/implement-task/SKILL.md`'s prose, which never states that phase1 proceeds directly
into `start` without asking:

- §0's resume table maps `phase1` to the passive `"Phase 1 — pick a task"`, reading as an
  invitation to interact rather than an instruction to run `start`.
- The **Parameter (optional)** note says a task id works "instead of auto-picking the top of TODO"
  but never says omitting it means auto-pick **without asking**.
- §1 places its hard STOP *after* `start` succeeds, so nothing forbids an extra confirmation turn
  *before* it.
- The **STOP semantics** paragraph enumerates the real STOPs but never declares that list
  complete, leaving room to invent one more.

`.tasks/guidelines.md:38` already says this unambiguously ("Pick the top unblocked TODO task") —
the drift is SKILL.md-only.

## Acceptance criteria

- [ ] §0's resume table `phase1` row is imperative — it says to run `start` (auto-picking the top
      of TODO when no task id was supplied), not merely "pick a task".
- [ ] The **Parameter (optional)** note states that omitting the task id means auto-pick, and that
      it is never a question to put to the human.
- [ ] §1 says explicitly: with no task id parameter, pass `{"task_id": null}` and do not ask which
      task — `start` reports what it picked and what it skipped, and the first human checkpoint is
      the plan-approval STOP that follows.
- [ ] The **STOP semantics** paragraph declares the listed STOPs the complete set: no extra
      confirmation may be inserted before any scripted step, at any phase boundary (this also
      covers e.g. `phase4_merged` → "record + clean up").
- [ ] No change to `scaffold.py` — `start` already auto-picks correctly given `{"task_id": null}`.
- [ ] Wording stays portable (no project-specific ids, paths, or "this repo's own …" phrasing),
      since `implement-task` ships to other repos via `init-project`.

**Out of scope:** `scaffold.py`; `.tasks/guidelines.md` (already correct); any new CI/prose-guard
test; the outstanding TASK-031 phase-4 bookkeeping (see Notes).

## Testing strategy

1. `python3 -m pytest tests/ -q` — full suite green (`test_portable_surface.py` in particular,
   which guards the shipped skills surface against project-specific references).
2. `python3 .tasks/bin/sync check` — exits 0.
3. Re-read the four edited passages end to end and confirm they agree with each other and with
   `.tasks/guidelines.md:38`.
4. **Human-run behavioral check** (not automatable — needs a fresh agent session): on a clean tree
   with nothing in flight, invoke `/implement-task` with no argument and confirm it runs
   `resume-state`, then immediately `start` with `{"task_id": null}`, stopping only at the
   post-plan STOP. Record the result in this task's Worklog.
5. **Human-run behavioral check:** invoke `/implement-task TASK-NNN` and confirm the supplied id is
   used and the auto-pick path is skipped.

## Worklog

- Edited `.claude/skills/implement-task/SKILL.md` only, four passages: the Parameter note, the
  STOP-semantics paragraph (added a "this is the complete set" sentence), §0's `phase1` table row,
  and §1 Start's opening sentence. No `scaffold.py` change.
- Testing strategy step 1 (`pytest tests/ -q` via the repo's `.venv`): **420 passed**, 0 failed.
- Testing strategy step 2 (`python3 .tasks/bin/sync check`): exit 0.
- Testing strategy step 3 (re-read the four passages together, and against
  `.tasks/guidelines.md:38`): consistent — all four now say "no task id ⇒ auto-pick immediately,
  never ask which task."
- Testing strategy steps 4–5 (human-run behavioral checks): **not run this session** — genuinely
  can't stage "nothing in progress" while this very task occupies phase 1–4 of the workflow the
  fix changes. This session's own phase-1 invocation *did* auto-pick TASK-050 without asking, but
  that's not a clean test of the fix (the assistant already knew the intended behavior from writing
  it, independent of what SKILL.md said). Recommend the human treat the *next* task's `/implement-task`
  kickoff (no argument, nothing in flight) as the real step-4 check, and a `/implement-task TASK-NNN`
  invocation as the step-5 check, and flag back here if either misbehaves.

## Notes

- Evidence: transcript `151843ca-2d33-4988-823a-de714081c5c3.jsonl` rows 733–737 (`resume-state` →
  `{"phase": "phase1"}` → the question) and rows 750–756 (the corrected `start` run).
- Files touched by the fix: `.claude/skills/implement-task/SKILL.md` only — the Parameter note,
  the STOP-semantics paragraph, the `phase1` table row, and §1 Start.
- Separate, pre-existing issue (not part of this task): `resume-state` currently reports
  `phase4_merged` for TASK-031 — PR #51 is merged on `main` but its phase-4 bookkeeping (record
  `merge_commit`, `status: done`, archive, unblock TASK-035) was never run, so the board still
  shows it in review.
