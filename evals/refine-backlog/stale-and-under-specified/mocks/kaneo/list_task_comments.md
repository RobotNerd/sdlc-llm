---
type: agent
expect:
  taskId: string
---

You are the Kaneo task tracker's list_task_comments tool. Answer with one line of JSON and nothing else.

- For taskId `mocktask0000000000000021`, answer:
  [{"id": "mockcomment000000000021", "taskId": "mocktask0000000000000021", "content": "needs-refinement\n\n- The target time for the test suite isn't measurable as written.", "createdAt": "2026-10-10T11:00:00.000Z", "updatedAt": "2026-10-10T11:00:00.000Z", "user": {"name": "LLM Agent", "image": null}}]
- For any other taskId, answer: []
