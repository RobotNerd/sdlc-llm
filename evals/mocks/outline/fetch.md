---
expect:
  id: string
  resource: [document]
---

{"document": {"id": "{{input.id}}", "url": "https://outline.example.com/doc/{{input.id}}"}}

{{file:fixtures/{input.id}.md}}
