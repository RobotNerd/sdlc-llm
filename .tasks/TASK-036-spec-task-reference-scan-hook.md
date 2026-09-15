---
id: TASK-036
title: SPEC/TASK-reference scan hook (repo-only, never copied)
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-036-spec-task-reference-scan-hook
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-027]
blocks: [TASK-039, TASK-040]
---

# TASK-036: SPEC/TASK-reference scan hook (repo-only, never copied)

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-027 (strip project-specific references from
the portable surface — so this hook starts from a clean baseline instead of failing on day one).

A script (e.g. `.dev/hooks/check-portable-references.py`, **outside** `.claude/hooks/** ` so it is
trivially excluded from `init-project`'s copy list and from `upgrade`'s managed files) that greps
the portable surface (`.claude/skills/**`, as established in TASK-027) for
`\b(TASK|EPIC|SPEC)-\d{3}\b` and denies `gh pr create` if any are found, listing the offending
files/lines.

Registered **only in this repo's own** `.claude/settings.json` — not in
`init-project/templates/settings.json` — so a scaffolded project never inherits a check that
would be meaningless (and possibly always-failing, since `TASK-NNN` placeholders are legitimate
template content) in someone else's repo.

## Acceptance criteria

- [ ] The hook denies `gh pr create` when a concrete `TASK-`/`EPIC-`/`SPEC-` id exists under
      `.claude/skills/` in the diff.
- [ ] The hook passes on the current (post-TASK-027) tree.
- [ ] The hook file and its `.claude/settings.json` registration are absent from every file
      `init-project`/`upgrade` write to another repo.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit test on the grep/scan function with fixture files containing and lacking concrete ids.
2. A test asserting this hook's own path is excluded from `managed_files()`'s output (or the
   scaffold's copy list) and from a freshly-scaffolded project's tree — extends TASK-029's
   data-loss-guard test with one more excluded path.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-027's cleanup.
- Deliberately the one hook in this epic that is never portable — see SPEC-002's Goals.
