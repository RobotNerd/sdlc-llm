"""SessionStart hook: put the in-progress and needs-human tasks in the session's context.

Claude Code adds this hook's stdout to the context. The plugin's hooks run in every
project it's enabled in, so a project without .sdlc/config.toml is skipped silently.
The hook never blocks the session: it always exits 0.
"""

import contextlib
import io
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib import board
from lib.config import ConfigError, find_repo_root, load_config

HEADING = "Kaneo tasks in progress or needing review (key, status, title, labels, blockers, id):"
STATUSES = "in-progress,needs-human"


def main(api=None):
    try:
        repo_root = find_repo_root(json.load(sys.stdin).get("cwd"))
        load_config(repo_root)
    except (ConfigError, ValueError):
        return 0

    output, errors = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            exit_code = board.main(["--status", STATUSES], start=repo_root, api=api)
    except Exception as error:  # noqa: BLE001 - a failing hook must never block the session from starting
        exit_code = 1
        errors.write(f"{type(error).__name__}: {error}")
    if exit_code != 0:
        print(f"sdlc-llm couldn't read the Kaneo board at session start: {errors.getvalue().strip()}")
    elif output.getvalue():
        print(f"{HEADING}\n{output.getvalue().rstrip()}")
    else:
        print("No Kaneo tasks are in progress or needing review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
