---
id: TASK-002
title: "Create spec / epic / task templates in .tasks/templates/"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-10
branch: task-002-artifact-templates
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-014, TASK-015, TASK-016]
---

# TASK-002: Create spec / epic / task templates in .tasks/templates/

## Description

Three markdown templates — `spec.md`, `epic.md`, `task.md` — under `.tasks/templates/`, each with the frontmatter schema and body-section headings from SPEC-001 §Data model, and placeholder tokens (`{{id}}`, `{{title}}`, …) the skills substitute.

## Acceptance criteria

- [ ] `task.md` frontmatter matches SPEC-001 §'Task frontmatter' exactly: `id, title, type, status, epic, created, branch, pr, merge_commit, blocked_by, blocks`.
- [ ] `epic.md` frontmatter matches §'Epic frontmatter' (`id, title, spec, status, created`) and its body carries an empty `BEGIN:children` / `END:children` region.
- [ ] `spec.md` frontmatter matches the amended §'Spec frontmatter' (no `epics:` field) and its body carries an empty `BEGIN:epics` region.
- [ ] Body headings match §Data model: task = Description / Acceptance criteria / Testing strategy / Worklog / Notes; epic = Goal / In scope / Out of scope / Success criteria.
- [ ] Every placeholder token is documented in a comment block in each template.

## Testing strategy

1. Render each template with a dummy substitution map and confirm the result parses as valid frontmatter + markdown.
2. Diff each template's frontmatter keys against the SPEC-001 schema — zero drift.

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies.
- Blocks TASK-014, TASK-015, TASK-016 — the skills consume these templates. (TASK-004's parser
  targets the schema in SPEC-001 directly, not the templates, so that edge was dropped.)
