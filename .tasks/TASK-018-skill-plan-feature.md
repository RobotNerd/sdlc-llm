---
id: TASK-018
title: "plan-feature skill: spec -> epics -> vertical-slice tasks"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-10
branch: task-018-skill-plan-feature
pr: null
merge_commit: null
blocked_by: [TASK-015]
blocks: []
---

# TASK-018: plan-feature skill: spec -> epics -> vertical-slice tasks

## Description

Requirements-gathering skill. Interviews for the 'why', writes a `SPEC-*.md` in `.tasks/specs/` (problem, alternatives, non-goals), decomposes the feature into vertical slices capturing `blocked_by`/`blocks`, groups slices under one or more epics linked to the spec, then fans out to `add-task` per slice (SPEC-001 §`plan-feature`).

## Acceptance criteria

- [x] Skill is a checklist with STOP markers, including a checkpoint on the spec draft before any tasks are created.
- [x] Produces a `SPEC-*.md` from the template via `sync next-id spec`, with Problem / Goals / Non-goals / alternatives sections.
- [x] Decomposes into vertical slices — each independently shippable and testable — not horizontal phases; records `blocked_by`/`blocks` between slices.
- [x] Creates one or more `EPIC-*.md` (via `sync next-id epic`) with `spec:` set, then calls `add-task` for each slice with the epic pre-selected.
- [x] Ends with `sync` and a clean `sync check`; the new epic appears in the board `epics` panel.

## Testing strategy

1. Run `plan-feature` on a sample feature; confirm a spec file, at least one epic, and several linked tasks are created, and the dependency graph among the new tasks is acyclic.
2. Confirm the spec checkpoint STOP halts before tasks are generated.
3. Confirm the new epic's `children` region and the board `epics` panel populate after `sync`.

## Worklog

- 2026-09-14: Built `.claude/skills/plan-feature/SKILL.md` — pure prose, consistent with the
  other skills before their (actual or eventual) script-extraction pass; this task predates that
  pattern being applied here.
- **AC #4's "epic pre-selected" resolved without waiting on TASK-022**: `add-task`'s own
  parameterization (skip the interview when a value is pre-supplied) hasn't shipped yet — it's
  still in TODO. Decided this doesn't block TASK-018: `plan-feature` names the epic explicitly in
  each `add-task` invocation's args, and `add-task`'s current epic-prompt step degrades
  gracefully to a one-line confirmation rather than a blind menu, since the epic is already
  named. No new `blocked_by` added. Confirmed this works in practice below.
- **Tested end to end on a scratch branch** (`test-plan-feature-dryrun`, deleted afterward — no
  PR needed since this test is file-only, no `git`/`gh` mechanics involved) with a real sample
  feature: "`sync doctor` — explain why a task is blocked or why an epic has its derived status."
  - Interviewed myself through Problem/Goals/Non-goals/Alternatives, drafted `SPEC-002`, `sync
    check` confirmed the frontmatter and empty `epics` region were valid before continuing
    (simulated the checkpoint STOP here — see Testing strategy step 2).
  - Decomposed into two real vertical slices with a real dependency: `sync doctor <task-id>`
    (foundational) and `sync doctor <epic-id>` (needs the first one's subcommand scaffolding).
    Grouped both under a new `EPIC-002`, `spec: SPEC-002`.
  - Fanned out to the *real* `add-task` skill twice (not simulated) — `TASK-026` (epic
    pre-named, confirmed as a one-line "attach to EPIC-002?" rather than a full menu, exactly as
    designed) then `TASK-027` with `blocked_by: [TASK-026]`. `sync` correctly reconciled
    `TASK-026`'s `blocks` to `[TASK-027]` automatically — confirms the dependency graph came out
    acyclic by construction, not just by inspection (testing strategy step 1).
  - `EPIC-002` appeared in `BOARD.md`'s `epics` panel (`0/2 done`) and its own `children` region
    listed both tasks; `SPEC-002`'s `epics` region showed `EPIC-002` linked — testing strategy
    step 3, confirmed directly.
  - `TASK-027`'s TODO line correctly showed `⛔ blocked_by TASK-026`.
  - Cleanup: deleted `test-plan-feature-dryrun` (local and remote). No scratch spec/epic/tasks
    remain in the real backlog.
- `pytest` (211 passed) and `sync check` (exit 0) reconfirmed on this branch after restoring the
  real implementation — no Python touched, both are reconfirmations.

## Notes

- Blocked by TASK-015 (`add-task` is the fan-out target).
- This skill is how future work (beyond MVP) enters the system.
