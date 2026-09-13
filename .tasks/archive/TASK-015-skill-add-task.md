---
id: TASK-015
title: "add-task skill: interview, epic prompt, size check, priority placement"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-015-skill-add-task
pr: https://github.com/RobotNerd/sdlc-llm/pull/21
merge_commit: 0884e1fd37dcfb4221dafab2f3c291babf3235de
blocked_by: [TASK-002, TASK-010]
blocks: [TASK-018]
---

# TASK-015: add-task skill: interview, epic prompt, size check, priority placement

## Description

A skill that turns a rough description into a well-formed `TASK-*.md`: interviews for concrete acceptance criteria and a testing strategy, allocates the ID via `sync next-id`, prompts for epic assignment, size-checks against one-PR, and asks where the task ranks in TODO (SPEC-001 §`add-task`).

## Acceptance criteria

- [x] Skill is a checklist with STOP markers; if the description yields no concrete acceptance criteria or testing strategy, it asks follow-ups before writing anything.
- [x] Allocates the ID with `sync next-id task` — never by counting files itself.
- [x] Epic prompt offers: attach to an existing open epic (lists them), create a new epic now, or leave unassigned.
- [x] Size check: if the work looks larger than one PR / one sitting, it proposes a split and stops.
- [x] Asks for TODO rank rather than always appending; inserts the line at that position.
- [x] Writes the file from `.tasks/templates/task.md`, then runs `sync`.

## Testing strategy

1. Feed a vague one-liner; confirm the skill asks follow-ups and does not create a file until criteria exist.
2. Feed a well-specified task with an epic; confirm ID allocation, epic link, TODO insertion at the requested rank, and a clean `sync check` after.
3. Feed an oversized task; confirm the split proposal.

## Worklog

- 2026-09-13: Built `.claude/skills/add-task/SKILL.md` — no naming collision to resolve this time
  (unlike TASK-014's `init` → `init-project`), so it's named `add-task` directly per SPEC-001.
  Checklist order deliberately puts the write step (6) strictly after the interview gate (1) and
  the size-check gate (2), so a vague or oversized description structurally cannot reach a file
  write — there's no separate "don't write yet" flag to forget to check.
- **Priority placement design:** `sync`'s bare run only ever *appends* a newly-`todo` task at the
  end of TODO (by design — TODO order is entirely hand-maintained). To honor a requested rank
  other than "at the end," the skill runs `sync` first to get the new line in its exact canonical
  rendered form (dash, id, em-dash, title, epic tag, blocked marker), then relocates that literal
  line within `BOARD.md` — never hand-composes the line itself. Confirmed in testing that moving
  an already-correct line leaves `sync check` clean (TODO order isn't a generated region).
- All three testing-strategy scenarios run against a scratch copy of this real repo's `.tasks/`
  (not the real one — this creates real files):
  1. (Vague one-liner → no file until criteria exist.) Verified by construction, not a runtime
     probe: the write step is gated behind steps 1 and 2, so nothing downstream of an unanswered
     interview or an unresolved size check can execute.
  2. Well-specified task ("`sync`: add a `--dry-run` flag", `EPIC-001`, requested rank "before
     TASK-017"): `sync next-id task` → `TASK-021`; wrote the file from the template — **caught a
     real gap while filling it in**: the template's title placeholder appears *twice*
     (`title: "{{title}}"` in frontmatter and `# {{id}}: {{title}}` in the heading right below
     it) and it's easy to fill only the quoted one and miss the heading's. Fixed by calling this
     out explicitly in `SKILL.md` step 6.2. After fixing, ran bare `sync` (appended the TODO line
     + `EPIC-001`'s `children` region, both correct), moved the literal appended line to before
     `TASK-017`, then `sync check` exited `0`.
  3. (Oversized task → split proposal, not a write.) Same structural argument as scenario 1 — the
     size-check gate (step 2) precedes the write step (step 6).
- `pytest` (211 passed) and `python3 .tasks/bin/sync check` (exit 0) on the real repo — this task
  didn't touch any Python, both are reconfirmations, not new coverage.

## Notes

- Blocked by TASK-002 (task template) and TASK-010 (`next-id`).
- Blocks TASK-018 (`plan-feature` fans out to `add-task`).
