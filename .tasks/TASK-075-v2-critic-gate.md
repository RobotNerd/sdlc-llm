---
id: TASK-075
title: "implement-task-v2: haiku critic gate with a bounded rework loop"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-075-v2-critic-gate
pr: null
merge_commit: null
blocked_by: [TASK-074]
blocks: [TASK-077]
---

# TASK-075: implement-task-v2: haiku critic gate with a bounded rework loop

## Description

Implement **spawn critic** and add `references/critic.md` (SPEC-005). After `run tests` is green,
launch a read-only critic with the Agent tool and `model: "haiku"`.

- The critic reads the task file and `git diff <default_branch>...<branch>` itself, and answers
  the seven-item checklist as one JSON object. Anything unparseable or inconsistent counts as a
  rejection.
- On rejection: record the findings in the Worklog, go back to `implement task` or
  `write tests`, re-run the tests, and spawn a fresh critic.
- After `critic_rejection_attempts` rejections: STOP with the findings. TASK-077 turns this into
  the `critic_rejection` pause.
- Critic rounds and findings go into the per-task report's Critic section.

## Acceptance criteria

- [ ] `references/critic.md` has SPEC-005's launch instructions, the seven-item checklist (`criteria_met`, `docs_clean`, `gates_passed`, `nothing_alarming`, `scope_ok`, `sorted_order`, `tests_behavioral`), the reply format, and the fail-closed rules.
- [ ] `spawn critic` uses the Agent tool with `model: "haiku"`, and tells the critic it's read-only.
- [ ] No merge happens without an approving verdict that parses cleanly.
- [ ] A rejection loops back to rework, and the next round spawns a fresh critic. The count toward `critic_rejection_attempts` is visible in the Worklog.
- [ ] Reaching `critic_rejection_attempts` stops the run without merging, and shows the findings.
- [ ] The per-task report's Critic section lists every round's verdict and findings.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: a clean dummy task is approved on the first round and merges.
2. Manual: a dummy task with a deliberately unsorted config list or stale doc line is rejected. Check that the findings name the problem, and that it merges after rework.
3. Manual: with `critic_rejection_attempts: 1` and a task seeded to fail review, the run stops unmerged and shows the findings.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- The checklist comes from v1's `CRITIC_CHECKLIST`, extended with `docs_clean`, `sorted_order` and `tests_behavioral`. See SPEC-005.
