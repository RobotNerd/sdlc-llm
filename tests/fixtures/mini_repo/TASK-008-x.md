---
id: TASK-008
title: Task eight
type: feature
status: todo
epic: null
created: 2026-01-01
branch: task-008-x
pr: null
merge_commit: null
blocked_by: [TASK-001]
blocks: []
---

Body eight. Second link of the chain: its declared blocked_by (TASK-001) is already done,
so the TODO line's outstanding-blocker marker should be *absent* even though blocked_by is
non-empty -- the static-list-vs-outstanding-blockers distinction (TASK-009), exercised
end-to-end here.
