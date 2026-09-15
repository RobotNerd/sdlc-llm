---
id: TASK-023
title: "Docs cleanup: remove redundant/deprecated info, relocate .tmp/ content, add README usage example"
type: refactor
status: done
epic: EPIC-001
created: 2026-09-13
branch: task-023-docs-cleanup
pr: "https://github.com/RobotNerd/sdlc-llm/pull/40"
merge_commit: 306778b1689b8d6ccd39e05b64c4a48f25aa4c9d
blocked_by: []
blocks: []
---

# TASK-023: Docs cleanup: remove redundant/deprecated info, relocate .tmp/ content, add README usage example

## Description

Several docs have accumulated redundant or stale content now that `.tasks/bin/sync` and the
skills actually exist — instructions written for a bootstrap phase that's now over, or prose that
just restates what `sync` already enforces mechanically. Clean up:

- `.tasks/guidelines.md` and `.claude/skills/init-project/templates/guidelines.md` — trim anything
  that only restates `sync`'s own mechanical behavior (region ownership, ID allocation, archiving,
  epic-status derivation) in favor of a pointer to `sync`/SPEC-001, keeping only what's still a
  human/LLM decision (the four-phase loop, guardrails, STOP markers). These two files are meant to
  mirror each other (TASK-014) — edit both, keep them consistent.
- `CLAUDE.md` — same redundancy pass.
- `.tmp/workflow-plan.md` and `.tmp/project-management-plan.md` — read both fully; anything still
  load-bearing (not already captured in `SPEC-001`/`CLAUDE.md`/`guidelines.md`) gets relocated to
  a permanent, non-`.tmp` home (candidates: fold into `SPEC-001`, into `guidelines.md`, or a new
  doc — implementation decides based on what's actually still true and where it fits); anything
  genuinely superseded is removed rather than carried forward. Reconsider whether
  `.tmp/session-handoff.md` (which currently points at `workflow-plan.md`) still needs to exist
  once this lands.
- `README.md` — add an "Example Usage" section: a concrete, step-by-step walkthrough of using this
  repo's actual skills end to end (e.g. `add-task` → `implement-task`'s phases), reflecting real
  skill/step names as they exist today, not the bootstrap-era description.

## Acceptance criteria

- [x] `.tasks/guidelines.md` and `.claude/skills/init-project/templates/guidelines.md` are trimmed
      of anything redundant with `sync`'s own mechanical behavior, and stay consistent with each
      other.
- [x] `CLAUDE.md` gets the same redundancy pass.
- [x] Nothing still load-bearing from `.tmp/workflow-plan.md` / `.tmp/project-management-plan.md`
      is lost — it's relocated to a permanent (non-`.tmp`) home; anything genuinely superseded is
      removed, not silently carried forward, and each removal is traceable (see Testing strategy).
- [x] `README.md` gains a step-by-step "Example Usage" section using this repo's real skills.
- [x] No dangling cross-reference: nothing else in the repo still points at a `.tmp/` doc (or a
      section of it) that this task removed or moved.

## Testing strategy

1. For every fact trimmed from `guidelines.md`/`CLAUDE.md`, confirm it's demonstrably still true
   and findable — in `sync`'s own code/docstrings, in `SPEC-001`, or wherever it was relocated —
   not just deleted.
2. Diff `.tasks/guidelines.md` against `.claude/skills/init-project/templates/guidelines.md` after
   the edit; confirm they're still consistent with each other (same intent as TASK-014's original
   mirroring).
3. `grep` the repo for references to whatever gets removed/moved from `.tmp/` (e.g.
   `.tmp/session-handoff.md`, `CLAUDE.md`) and confirm none point at a section that no longer
   exists there.
4. Read the new README "Example Usage" section end to end and confirm every skill/step name it
   references matches what's actually on disk today (e.g. `init-project`, not `init`).
5. `python3 .tasks/bin/sync check` stays clean throughout (docs aren't generated regions, but this
   confirms no incidental drift from editing adjacent files).

## Worklog

- 2026-09-15: Read `.tmp/workflow-plan.md` and `.tmp/project-management-plan.md` fully before
  deciding anything. Findings:
  - `.tmp/project-management-plan.md` (the original analysis doc): every recommendation in it has
    already been implemented and is now documented properly (frontmatter schema in SPEC-001, `sync`
    built exactly as described, per-skill designs superseded by the real `SKILL.md`s, `config.md`
    schema matches). Zero unique unrecorded facts — deleted entirely.
  - `.tmp/workflow-plan.md` Part 2 (bootstrapping) was already self-marked "complete... historical
    record, not a live status table" — deleted; git history + archived task Worklogs preserve it
    for anyone curious. Part 1 (mental model) mostly restates SPEC-001 (already authoritative) or
    README's existing model table (the Jira-mapping analogy) — deleted, except two genuinely
    unique pieces relocated to permanent homes: the "two loops" skill diagram → README's Skills
    section; the auto-merge-rejection rationale (why `implement-task` never runs end to end) → a
    new bullet in SPEC-001 §"Resolved during planning". The EPIC-002/EPIC-003 "planned, not yet
    built" paragraphs are now themselves redundant with the real SPEC-002/SPEC-003/EPIC-002/
    EPIC-003 files that exist — dropped, not relocated.
  - `.tmp/session-handoff.md` reconsidered per the task's own prompt: its content described a
    single planning session's output (TASK-027–045, EPIC-002/003, SPEC-002/003) which is now
    fully real and reflected in `BOARD.md`/the task files themselves — the handoff had already
    served its purpose (used at the start of this very session to resume). Deleted; a live
    `BOARD.md` plus git log/archived Worklogs is the accurate "what happened" record going
    forward, not a point-in-time snapshot that goes stale the moment more work lands.
  - `.tasks/config.md`'s `docs_paths` dropped `.tmp/workflow-plan.md` (the file no longer exists).
- `CLAUDE.md`: removed "the five skills don't exist yet" (all five exist; four now have
  `scaffold.py` automation) and the full phase-by-phase `implement-task` restatement — replaced
  with a pointer to the skill's own `SKILL.md`/`scaffold.py`, since that's now the living source
  of truth and CLAUDE.md restating all four phases was one of (previously) four separate
  restatements of the same facts across CLAUDE.md/`guidelines.md`/README/workflow-plan.md.
- `.tasks/guidelines.md` and its portable-template mirror
  (`.claude/skills/init-project/templates/guidelines.md`): trimmed restatements of `sync`'s own
  mechanical behavior specifically (the ID-allocation scanning detail, the TODO-merge
  drop/append/re-annotate detail) down to pointers — the four-phase loop and guardrails
  themselves stay in full, per the task's own instruction, since that's still human/LLM process
  guidance, not `sync`-internal mechanics. Fixed the stale "until the implement-task skill exists
  (TASK-016)" conditional — the skill exists now. Diffed the two files after editing: identical
  except the three places `.tasks/guidelines.md` points at this repo's own SPEC-001 (the portable
  template correctly has no such pointer) — same shape of difference as before this task.
- `README.md`: fixed the stale "Skills ... still to be built" section (all five exist); folded in
  the relocated "two loops" diagram; added the new "Example usage" section — a `/plan-feature` →
  `/implement-task` (twice, once for the PR, once for the observed merge) → `/refine-backlog`
  walkthrough using real skill names and phase behavior, cross-checked against
  `.claude/skills/implement-task/scaffold.py`'s actual subcommand names
  (`resume-state`/`start`/`wrap-up`/`finish-merge`/`bail-out`) and `ls .claude/skills/` (all five
  present) rather than the bootstrap-era description.
- `SPEC-001`: fixed two dangling references to the now-deleted `.tmp/project-management-plan.md`
  (§Problem, rephrased to describe the superseded analysis without naming a path that no longer
  exists) and `.tmp/workflow-plan.md` (§Epics, the `render_spec_epics` region's explanatory
  prose); added the relocated auto-merge rationale to §"Resolved during planning". `SPEC-003`:
  fixed its own citation of `.tmp/workflow-plan.md`'s auto-merge quote to point at SPEC-001's new
  bullet instead.
- Deliberately left untouched (per scope discipline, not an oversight): `.tasks/archive/*` (frozen
  historical record — TASK-014/TASK-019 both still mention `.tmp/workflow-plan.md` in their own
  point-in-time Worklogs, correctly so) and `TASK-027`'s own AC (a future task's plan referencing
  `.tmp/workflow-plan.md` as something to grep for during the portable-surface cleanup — editing
  another task's description is out of this task's scope; the reference will simply be a no-op
  when TASK-027 is picked up, since the file will already be gone). `.tmp/prompts.md` was not read
  or acted on, per standing instruction, despite incidentally matching the cross-reference grep.
- Testing: `grep -rl` across the repo for `project-management-plan`/`workflow-plan`/
  `session-handoff` after all edits — the only remaining hits are the excluded archive/future-task
  files above and `.tmp/prompts.md`. `python3 .tasks/bin/sync check` exits `0`. Diffed the two
  guidelines files (above). Cross-checked README's new section against
  `.claude/skills/implement-task/scaffold.py` and `ls .claude/skills/` (above).

## Notes

- No hard dependency, but naturally lands after TASK-021/TASK-022 (the two skill-refactor tasks)
  since those may change what `guidelines.md`/`CLAUDE.md` need to say about how the skills work —
  priority placement (bottom of TODO) already puts it there.
- Placed at the bottom of TODO per the user's explicit instruction when this task was filed.
