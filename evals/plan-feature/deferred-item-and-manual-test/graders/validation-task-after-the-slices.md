---
type: tool_order
before:
  tool: mcp__plugin_sdlc-llm_kaneo__create_task
  input_match: '"title"\s*:\s*"[^"]*[Ss]end[^"]*'
after:
  tool: mcp__plugin_sdlc-llm_kaneo__create_task
  input_match: '"title"\s*:\s*"Run the manual tests for '
---
