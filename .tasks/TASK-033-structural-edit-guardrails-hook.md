---
id: TASK-033
title: "Structural edit guardrails hook: generated regions and epic status"
type: feature
status: in-progress
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

Added two pure functions to `guardrails.py`: `region_edit_violation(path_name, old_content,
new_content)` -- for each region name valid for the file kind (`children` for `EPIC-*.md`,
`epics` for `SPEC-*.md`, `epics`/`in-progress`/`in-review`/`blocked`/`done` for `BOARD.md`),
calls `sync.find_region` on both old and new text and returns the first region name whose
content actually changed or whose markers were removed -- `None` otherwise; and
`epic_status_edit_violation(path_name, old_content, new_content)` -- parses old/new
frontmatter via `sync.parse_frontmatter` for an `EPIC-*.md` file and returns the new `status`
if it changed to anything but `wont-do`. Deliberately diff-based (compares actual before/after
content), not "any edit to a region-bearing file," so an unrelated edit to the same file isn't
falsely blocked -- matches AC #3.

`check_region_edit`/`check_epic_status_edit` wrap these for a real tool call: read the file
fresh off disk for "old" content (the hook fires before the edit applies), compute "new"
content (`Edit`: apply `old_string`->`new_string` in memory, allowing if `old_string` isn't
found or isn't unique without `replace_all`, matching how the tool itself would refuse;
`Write`: use `tool_input.content` directly). `evaluate_edit_write` runs both, same pattern as
TASK-032's `evaluate_bash_command`.

New hook script `.claude/hooks/pretooluse_edit_write.py`, registered in `.claude/settings.json`
with `"matcher": "Edit|Write"` alongside the existing `Bash` entry. Vendored at
`.claude/skills/init-project/vendored-hooks/pretooluse_edit_write.py`, picked up automatically
by the existing `vendored-hooks/` -> `.claude/hooks/` loop in `managed_files()` -- no
`scaffold.py` change needed there. Extended the full-skill-table scaffold test for the new file.

AC #4 ("`sync`'s own writes... are unaffected") holds by construction: `sync` writes files via
plain Python file I/O in its own subprocess, never through Claude's `Edit`/`Write` tool
machinery, so this hook never sees its writes at all.

Testing strategy:
1. Unit tests for both pure functions against text fixtures (`tests/test_structural_edit_guardrails.py`),
   matching `test_region_engine.py`/`test_derivation.py`'s style -- region-content-changed,
   markers-removed, TODO-section-edit (never a violation, not a BEGIN/END region), a file with
   no known regions, status changed/unchanged/changed-to-wont-do, non-epic files, and
   unparseable frontmatter. **Pass.**
2. Hook-script tests: real subprocess invocation with the documented `PreToolUse` stdin shape
   for both `Edit` and `Write`, in-region and out-of-region targets, and both a `wont-do` and
   non-`wont-do` epic status edit -- all confirmed denied/allowed as expected; a non-`Edit`/`Write`
   tool call confirmed to pass through with exit 0 and no output. **Pass.**
3. `python3 -m pytest -q` -- 464 passed (438 + 26 new), no regressions. **Pass.**
4. `python3 .tasks/bin/sync check` -- exit 0. **Pass.**

## Notes

- Depends on TASK-032's `guardrails.py` module and hook-wiring pattern.
