---
expect:
  id: string
  resource: [document]
---

{"document": {"id": "{{input.id}}", "title": "Guideline doc", "url": "https://outline.example.com/doc/{{input.id}}"}}

{{file:fixtures/{input.id}.md}}
