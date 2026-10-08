"""Stop hook: send a generic notification when the agent ends a turn, unless a skill already did.

The plugin's hooks run in every project it's enabled in, so a project without
.sdlc/config.toml is skipped silently. The hook never blocks the stop: it prints
nothing on stdout and always exits 0.
"""

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import ConfigError, find_repo_root, load_config
from lib.notify import MARKER_PATH, notify, parse_arguments

GENERIC_MESSAGE = ["--kind", "STOP", "--skill", "session", "--text", "Claude Code is waiting for you"]


def main():
    try:
        stop_input = json.load(sys.stdin)
        repo_root = find_repo_root(stop_input.get("cwd"))
        config = load_config(repo_root)
    except (ConfigError, ValueError):
        return 0

    try:
        marker = repo_root / MARKER_PATH
        # The marker always comes from this turn: every stop clears it, even with the flag off.
        skill_already_notified = marker.exists()
        settings = config.get("notify", {})
        if settings.get("stop_hook", False) and not skill_already_notified:
            result = notify(parse_arguments(GENERIC_MESSAGE), start=repo_root)
            if "warning" in result:
                print(f"warning: {result['warning']}", file=sys.stderr)
        # A send above writes the marker too, and it mustn't suppress the next stop.
        marker.unlink(missing_ok=True)
    except Exception as error:
        print(f"warning: stop notification not sent: {type(error).__name__}: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
