---
id: TASK-033
title: "Structural edit guardrails hook: generated regions and epic status"
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-033-structural-edit-guardrails-hook
pr: null
merge_commit: null
blocked_by: [TASK-032]
blocks: [TASK-039, TASK-040]
---

# TASK-033: Structural edit guardrails hook: generated regions and epic status

## Description

Blocked on TASK-032 (hooks infrastructure + shared `guardrails.py` module).

One `PreToolUse`/`Edit|Write` hook, two checks added to `guardrails.py`:

1. The proposed edit's target lines fall inside a `BEGIN:`/`END:` region — reuse `find_region`
   from the vendored `sync` module directly; do not reimplement region detection.
2. The target is an `EPIC-*.md` file and the edit's frontmatter changes `status` to anything but
   `wont-do` — reuse `parse_frontmatter`.

Deny with a message naming the region/field and pointing at `sync` as the correct way to make the
change.

## Acceptance criteria

- [ ] An `Edit`/`Write` whose target range falls inside any generated region is denied.
- [ ] An epic frontmatter edit changing `status` to anything but `wont-do` is denied.
- [ ] Edits outside both cases are unaffected.
- [ ] `sync`'s own writes (which happen via the script, not this tool boundary) are unaffected.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests against `find_region`/`parse_frontmatter` fixtures already in `tests/`.
2. Hook-script tests with representative `Edit`/`Write` tool-input JSON for both in-region and
   out-of-region targets, and both a `wont-do` and non-`wont-do` epic status edit.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's `guardrails.py` module and hook-wiring pattern.
