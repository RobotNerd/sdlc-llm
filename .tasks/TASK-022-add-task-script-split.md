---
id: TASK-022
title: "add-task: move deterministic portions to a stdlib script, define its parameters"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-13
branch: task-022-add-task-script-split
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-022: add-task: move deterministic portions to a stdlib script, define its parameters

## Description

Same pattern as TASK-021 (`init-project`'s scaffold script), applied to `add-task`: several of
its checklist steps are fully deterministic and shouldn't need the LLM to execute them by hand.
Move those into a stdlib-only Python script, and formalize the skill's own parameters in
`SKILL.md` so a future caller (SPEC-001 describes `plan-feature`, TASK-018, as "fanning out to
`add-task`" per slice) can pre-supply answers instead of triggering an interactive interview for
every one.

Specifically:

- **Open-epic listing** (current step 3's "read every `.tasks/EPIC-*.md`... list the ones whose
  status is not `done`/`wont-do`") — mechanical file-reading and filtering, no judgement.
- **Step 6.2 (write the task file) splits in two**: 2a is the script creating
  `.tasks/TASK-<id>-<slug>.md` from `.tasks/templates/task.md` with every frontmatter field
  mechanically filled (`id`, `type`, `epic`, `created`, `branch`, `blocked_by` — everything that
  isn't the LLM's own interview content); 2b is the LLM filling in the body's
  Description/Acceptance criteria/Testing strategy/Notes from what the interview produced. The
  file the script hands back to the LLM in 2a still has those body sections as placeholders.
- **Other deterministic steps found during implementation** — TODO placement at a requested rank
  (step 6.4, currently described as a manual cut-paste) and running `sync`/`sync check` (steps
  6.3/6.5) are strong candidates; confirm and fold in whatever else turns out mechanical once the
  script exists, same as TASK-021's own Worklog is expected to surface things.
- **Defined parameters**: `SKILL.md` gains an explicit parameter list (name, required/optional,
  default) — at minimum `description`, `type`, `epic`, `blocked_by`, `priority`. When a caller
  supplies one, the corresponding interview step is skipped rather than asked anyway; when it's
  omitted, the interview runs as it does today. This is what makes fan-out from `plan-feature`
  (not yet built) practical later without redesigning `add-task` again.

## Acceptance criteria

- [ ] A stdlib-only Python script under `.claude/skills/add-task/` lists every open epic (status
      not `done`/`wont-do`, scanning `.tasks/` and `.tasks/archive/`) instead of the LLM reading
      files by hand.
- [ ] The same or a sibling script provides step 2a: given an id/type/epic/branch/blocked_by (and
      today's date), writes `.tasks/TASK-<id>-<slug>.md` from the template with frontmatter (and
      both title occurrences) filled, leaving the body's Description/Acceptance
      criteria/Testing strategy/Notes as placeholders for the LLM to fill in (step 2b).
- [ ] TODO placement at a requested rank (append / top / after a named task) and the
      `sync` + `sync check` calls are also done by the script, not by hand — unless
      implementation surfaces a reason one of them can't be, which gets documented rather than
      silently dropped.
- [ ] `SKILL.md` documents `add-task`'s parameters explicitly (name, required/optional, default)
      — at least `description`, `type`, `epic`, `blocked_by`, `priority` — and the checklist skips
      the interview step for any parameter that's already supplied.
- [ ] Unit tests (`pytest`) cover: open-epic listing against a mixed-status fixture, step 2a's
      frontmatter templating, and TODO placement for at least "append" and "after a named task".
- [ ] `SKILL.md`'s remaining prose is still a numbered checklist with STOP/ASK only around
      genuinely non-deterministic steps (interview content, size-check judgement, confirmation).

## Testing strategy

1. Run the epic-listing function against a fixture with a mix of `todo`/`in-progress`/`done`/
   `wont-do` epics; confirm only open ones come back.
2. Run step 2a with sample values; confirm the frontmatter is correct, both title occurrences are
   filled, and the body sections are still placeholders for 2b.
3. Run the TODO-placement logic for "append" and "after TASK-NNN"; confirm `sync check` stays
   clean after each.
4. Run the new unit test suite (`pytest`).
5. Walk `SKILL.md`'s parameter section against a hypothetical fully-parameterized call (every
   parameter pre-supplied) and confirm no interview step would trigger.

## Worklog

_(empty — appended during implementation)_

## Notes

- No hard dependency on TASK-021 — different skill, independent code path — though implementing
  it second may reuse whatever script/testing shape TASK-021 settles on.
- Placed at the bottom of TODO, after TASK-021 — decided with the user via `add-task`'s
  priority-placement step.
- The parameter work here is what unblocks a future `plan-feature` (TASK-018) from fanning out to
  `add-task` per SPEC-001's description without redesigning this skill again.
