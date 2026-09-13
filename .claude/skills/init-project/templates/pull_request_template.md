<!--
  This template mirrors the body of .tasks/TASK-NNN-slug.md (SPEC-001
  §"Task frontmatter") so that implement-task phase 3 (SPEC-001
  §implement-task) can fill this PR in by copying the task file's
  sections with checkboxes marked off, not by rewriting them from
  scratch. PR title: a conventional commit citing the task, e.g.
  `feat(TASK-NNN): short summary` (SPEC-001 / CLAUDE.md §Guardrails,
  .tasks/guidelines.md).
-->

## Task

TASK-NNN — <!-- task title -->

## Description

<!-- Copy the task's "## Description" section, or summarize the change. -->

## Acceptance criteria

<!-- Copy the task's "## Acceptance criteria" checklist verbatim, checked off. -->

- [ ]

## Test results

<!-- Walk the task's "## Testing strategy" steps and report what happened for each. -->

- `test_command` (`pytest`): <!-- pass/fail, or n/a -->
- `lint_command`: <!-- pass/fail, or n/a if null in .tasks/config.md -->

1.

### Non-automatable steps (run by a human)

<!--
  Steps that need real credentials, cost money, or otherwise can't be
  scripted (SPEC-001 §implement-task phase 2). List each one, who ran
  it, and the result — mirror this into the task file's Worklog too.
-->

- [ ]

## Notes

<!-- Deviations from the task, follow-ups filed, anything a reviewer should know. -->
