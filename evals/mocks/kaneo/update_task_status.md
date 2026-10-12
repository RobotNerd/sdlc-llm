---
expect:
  status: [archived, done, in-progress, needs-human, planned, to-do]
  taskId: string
---

{"id": "{{input.taskId}}", "number": 12, "title": "Mock task title", "status": "{{input.status}}", "priority": "no-priority", "position": 0, "projectId": "mockproject0000000000001"}
