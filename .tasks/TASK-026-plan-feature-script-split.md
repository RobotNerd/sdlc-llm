---
id: TASK-026
title: "plan-feature: move mechanical file-writing and cycle checking to a stdlib script"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-026-plan-feature-script-split
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-027]
---

# TASK-026: plan-feature: move mechanical file-writing and cycle checking to a stdlib script

## Description

Same pattern as TASK-021/022/024/025, applied to `plan-feature` (TASK-018): move its
deterministic steps into a stdlib-only Python script — allocating spec/epic ids
(`sync next-id spec`/`epic`), writing `SPEC-*.md`/`EPIC-*.md` from their templates given
already-decided content, running `sync`/`sync check`, and confirming the new epic appears in the
board `epics` panel and its `children` region. Also replaces the "eyeball it for cycles" step
(a placeholder for not having tooling yet, per `SKILL.md`'s own wording) with a real cycle check
over the proposed `blocked_by`/`blocks` graph among the new slices, run before the
restate-and-confirm STOP.

What stays as LLM/human judgment, unchanged: the interview (problem/goals/non-goals/alternatives),
the vertical-slice decomposition itself (what the slices are, where the real dependencies are),
and both STOP checkpoints (spec draft, and the full decomposition before task creation). The
script only writes what's already been decided and validates it.

## Acceptance criteria

- [ ] A stdlib-only Python script under `.claude/skills/plan-feature/` allocates spec/epic ids and
      writes `SPEC-*.md`/`EPIC-*.md` from their templates given filled-in content (Problem/
      Goals/Non-goals/Alternatives for the spec; Goal/In scope/Out of scope/Success criteria for
      each epic, with `spec:` set).
- [ ] The same or a sibling script runs `sync` and `sync check`, and reports whether the new
      epic(s) appear correctly in `BOARD.md`'s `epics` panel and their own `children` region.
- [ ] The script provides a real cycle check over a proposed `blocked_by`/`blocks` graph (a list
      of slices with their proposed dependencies) and reports any cycle found, replacing
      `SKILL.md`'s "eyeball it" step.
- [ ] `SKILL.md` is rewritten so its own prose covers only the interview, the decomposition
      judgment, and the two STOP checkpoints — each backed by one script invocation for the
      mechanical file-writing/validation part.
- [ ] Unit tests (`pytest`) cover: the cycle check against both an acyclic and a genuinely cyclic
      fixture graph, and spec/epic file templating given sample content.

## Testing strategy

1. Unit-test the cycle check against a small acyclic fixture graph and a deliberately cyclic one
   (e.g. A blocks B blocks C blocks A); confirm it correctly passes the first and flags the
   second with which edge closes the cycle.
2. Unit-test spec/epic templating against sample content; confirm the leading template comment is
   dropped and every placeholder is filled.
3. Dry-run the full script against a scratch feature (same throwaway-branch approach as TASK-018
   itself used) — confirm the same outcome TASK-018 already proved by hand.
4. Re-read `SKILL.md` and confirm its remaining prose is interview/decomposition/STOP-checkpoint
   only, with one script call per mechanical step it used to describe as prose.

## Worklog

_(empty — appended during implementation)_

## Notes

- No hard dependency — TASK-018 (what this refactors) is already done.
- Placed at the bottom of TODO — per the user's explicit instruction when this task was filed.
