---
type: tool_order
before:
  tool: mcp__plugin_sdlc-llm_kaneo__create_task
  input_match: '"title"\s*:\s*"[^"]*[Pp]rint[^"]*CSV'
after:
  tool: mcp__plugin_sdlc-llm_kaneo__create_task
  input_match: '"title"\s*:\s*"[^"]*(--output|[Ff]ile)'
---
