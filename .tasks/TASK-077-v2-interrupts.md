---
id: TASK-077
title: "implement-task-v2: pause the batch on interrupts, with attempt counters"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-077-v2-interrupts
pr: null
merge_commit: null
blocked_by: [TASK-075, TASK-076]
blocks: [TASK-078, TASK-079]
---

# TASK-077: implement-task-v2: pause the batch on interrupts, with attempt counters

## Description

Add `references/interrupts.md` (SPEC-005) and implement pausing. When one of the interrupt kinds
fires:

1. Write the kind, step, detail and needed decision to the Worklog.
2. `wip` commit.
3. Set the batch state's `interrupt`.
4. Write the batch report with `Status: paused` and its Early stop section.
5. STOP with the question.

Per-task attempt counters (`quality_gate`, `guardrail_denial`, `critic_rejection`) live in the
batch state. They count consecutive same-reason failures against `quality_gate_attempts`,
`guardrail_denial_attempts` and `critic_rejection_attempts`. TASK-075's critic STOP becomes the
`critic_rejection` pause. A rejected or failed push becomes `infra_failure`. Resolving a pause
is TASK-078's job, and the usage kinds' checkpoint is TASK-079's.

## Acceptance criteria

- [ ] `references/interrupts.md` lists all eight kinds with their triggers, the counter rules and the pause procedure. `SKILL.md` points to it wherever an interrupt can fire.
- [ ] `needs_clarification`, `unexpected_blocker`, `quality_gate_failure`, `guardrail_denial`, `infra_failure` and `critic_rejection` each pause as the procedure describes. The task branch, task status and batch state stay in place.
- [ ] Counters are per task and count consecutive same-reason failures. They're read from `.tasks/config.md`.
- [ ] A paused batch's report has `Status: paused`, and its Early stop section names the kind, task, step, detail and decision needed.
- [ ] Reaching the follow-up limit, or a single test failure that gets fixed, never pauses.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: with `quality_gate_attempts: 1` and a task seeded with a failing test the agent can't fix in one try, the batch pauses. Check the Worklog, the `wip` commit, `interrupt` in the state, and the batch report.
2. Manual: a task whose acceptance criteria contradict each other produces a `needs_clarification` pause.
3. Manual: point `origin` at a nonexistent path; the push produces `infra_failure`.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- v1 split interrupts into isolated, systemic and bail-out-halt routing. v2 always pauses, and the human decides.
