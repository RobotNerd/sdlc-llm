#!/usr/bin/env python3
"""`PreToolUse`/`Edit|Write` hook: the structural backstop for this workflow's generated
regions and derived epic status.

Reads the hook's stdin JSON, and -- for an `Edit` or `Write` tool call -- runs every check in
`.tasks/bin/guardrails.py::evaluate_edit_write` against `tool_input`. Exits `2` with the
violation's reason on stderr for the first denial found; exits `0` with no output otherwise,
letting the call through untouched. Any input this script can't make sense of (malformed
JSON, a tool other than `Edit`/`Write`, missing fields) is treated the same way as "no
opinion" -- exit `0`.

Vendored into every scaffolded project at this same relative path -- see
`.claude/skills/init-project/vendored-hooks/pretooluse_edit_write.py` and `managed_files()`
in `init-project/scaffold.py`. Registered in `.claude/settings.json`.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".tasks" / "bin"))
import guardrails  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in ("Edit", "Write"):
        return 0
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or ".")

    result = guardrails.evaluate_edit_write(tool_name, tool_input, cwd)
    if not result.allow:
        print(result.reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
