---
id: TASK-023
title: "Docs cleanup: remove redundant/deprecated info, relocate .tmp/ content, add README usage example"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-13
branch: task-023-docs-cleanup
pr: null
merge_commit: null
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

- [ ] `.tasks/guidelines.md` and `.claude/skills/init-project/templates/guidelines.md` are trimmed
      of anything redundant with `sync`'s own mechanical behavior, and stay consistent with each
      other.
- [ ] `CLAUDE.md` gets the same redundancy pass.
- [ ] Nothing still load-bearing from `.tmp/workflow-plan.md` / `.tmp/project-management-plan.md`
      is lost — it's relocated to a permanent (non-`.tmp`) home; anything genuinely superseded is
      removed, not silently carried forward, and each removal is traceable (see Testing strategy).
- [ ] `README.md` gains a step-by-step "Example Usage" section using this repo's real skills.
- [ ] No dangling cross-reference: nothing else in the repo still points at a `.tmp/` doc (or a
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

_(empty — appended during implementation)_

## Notes

- No hard dependency, but naturally lands after TASK-021/TASK-022 (the two skill-refactor tasks)
  since those may change what `guidelines.md`/`CLAUDE.md` need to say about how the skills work —
  priority placement (bottom of TODO) already puts it there.
- Placed at the bottom of TODO per the user's explicit instruction when this task was filed.
