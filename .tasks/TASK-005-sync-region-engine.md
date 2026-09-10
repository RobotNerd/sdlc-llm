---
id: TASK-005
title: "sync: generated-region find / replace / append engine"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-005-sync-region-engine
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-007, TASK-008]
---

# TASK-005: sync: generated-region find / replace / append engine

## Description

The text machinery every renderer sits on: locate a `<!-- BEGIN:<name> ... -->` / `<!-- END:<name> -->` pair, replace only the lines strictly between them, and append a region in a caller-specified position if it is missing (SPEC-001 §'Generated regions').

## Acceptance criteria

- [ ] `find_region(text, name)` returns the span between markers, or `None` if absent; tolerates extra text after the name inside the `BEGIN` comment.
- [ ] `replace_region(text, name, body)` swaps only the inter-marker lines and is a no-op when `body` already matches — byte-for-byte.
- [ ] `ensure_region(text, name, body, anchor)` appends `BEGIN`/body/`END` at the anchor when the region is absent.
- [ ] Emitter follows SPEC-001 §'Rendering details': no leading blank line after `BEGIN`, single trailing newline before `END`, `_(none)_` for an empty body.
- [ ] Unit tests: missing region, empty region, region with content, two regions in one file, and the idempotent-replace case.

## Testing strategy

1. Construct a fixture markdown string with two regions; run every engine function and assert on exact output.
2. Run `replace_region` twice with the same body and confirm the second call changes nothing.

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies — pure string handling.
- Blocks TASK-007, TASK-008 (both renderers use it).
