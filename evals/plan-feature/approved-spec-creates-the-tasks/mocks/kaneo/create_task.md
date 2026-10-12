---
type: agent
expect:
  description: string
  priority: [no-priority, low, medium, high, urgent]
  projectId: mockproject0000000000001
  status: string
  title: string
---

You are the Kaneo task tracker's create_task tool. Answer with one line of JSON and nothing else:

{"id": "mock-<title>", "number": <number>, "title": "<title>", "status": "<status>", "priority": "<priority>", "position": 3, "projectId": "mockproject0000000000001"}

- `<title>`, `<status>`, and `<priority>` are the call's input, exactly as given.
- `<number>` is 13 for the first create_task call in this run, and one more for each call after it: 13, 14, 15, and so on.
