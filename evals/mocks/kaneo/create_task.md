---
expect:
  description: string
  priority: [no-priority, low, medium, high, urgent]
  projectId: string
  status: string
  title: string
---

{"id": "mocktask0000000000000001", "number": 13, "title": "{{input.title}}", "status": "{{input.status}}", "priority": "{{input.priority}}", "position": 3, "projectId": "{{input.projectId}}"}
