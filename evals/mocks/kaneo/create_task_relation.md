---
expect:
  relationType: [blocks, subtask]
  sourceTaskId: string
  targetTaskId: string
---

{"id": "mockrelation000000000001", "sourceTaskId": "{{input.sourceTaskId}}", "targetTaskId": "{{input.targetTaskId}}", "relationType": "{{input.relationType}}"}
