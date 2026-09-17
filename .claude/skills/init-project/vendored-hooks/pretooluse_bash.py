#!/usr/bin/env python3
"""`PreToolUse`/`Bash` hook: the structural backstop for this workflow's
mechanically-checkable guardrails.

Reads the hook's stdin JSON, and -- for a `Bash` tool call -- runs every check in
`.tasks/bin/guardrails.py::evaluate_bash_command` against `tool_input.command`. Exits `2`
with the violation's reason on stderr (Claude Code shows this to the model and refuses the
call) for the first denial found; exits `0` with no output otherwise, letting the call
through untouched. Any input this script can't make sense of (malformed JSON, a tool other
than `Bash`, no `command`) is treated the same way as "no opinion" -- exit `0`.

Vendored into every scaffolded project at this same relative path -- see
`.claude/skills/init-project/vendored-hooks/pretooluse_bash.py` and `managed_files()` in
`init-project/scaffold.py`. Registered in `.claude/settings.json`.
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

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command")
    if not command:
        return 0
    cwd = Path(payload.get("cwd") or ".")

    result = guardrails.evaluate_bash_command(command, cwd)
    if not result.allow:
        print(result.reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
