"""Time-tracking hook: record each turn's wall-clock time as a Kimai entry.

UserPromptSubmit starts an entry for the repo's project and activity, unless this repo's
entry is already running. Stop, StopFailure, and SessionEnd stop it, except that a Stop leaves
the entry running while a background subagent the session started hasn't reported back. The running entry lives
in .sdlc/local/time-entry.json, with the time the hook last ran. A UserPromptSubmit that finds another
session's entry still running stops it at that time, then starts one for this session.

Time tracking is on only when .sdlc/config.toml has a [time_tracking] section. A repo
without one is skipped silently. A failure is a warning on stderr, and the hook always
exits 0 with nothing on stdout.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.kimai import KimaiApi
from lib.backends.rest import RestError
from lib.config import ConfigError, find_repo_root, load_config
from lib.env import EnvError, load_env, require_secret
from lib.transcript import running_background_subagents, transcript_entries

REQUIRED_KEYS = ("url", "project_id", "activity_id", "agent_user")
STATE_PATH = ".sdlc/local/time-entry.json"
STOP_EVENTS = ("Stop", "StopFailure", "SessionEnd")
TOKEN_NAME = "KIMAI_API_TOKEN"


def main():
    try:
        hook_input = json.load(sys.stdin)
        repo_root = find_repo_root(hook_input.get("cwd"))
        settings = load_config(repo_root).get("time_tracking")
    except (ConfigError, ValueError):
        return 0
    if settings is None:
        return 0

    try:
        missing = [key for key in REQUIRED_KEYS if key not in settings]
        if missing:
            raise ConfigError(f"[time_tracking] is missing {', '.join(missing)}")
        event = hook_input.get("hook_event_name")
        if event == "UserPromptSubmit":
            start(repo_root, settings, hook_input.get("session_id"))
        elif event == "Stop" and running_background_subagents(transcript_entries(hook_input.get("transcript_path"))):
            touch(repo_root)
        elif event in STOP_EVENTS:
            stop(repo_root, settings)
    except (ConfigError, EnvError, RestError, OSError) as error:
        warn(error)
    except Exception as error:  # noqa: BLE001 - a failing hook must never block the session
        warn(f"unexpected {type(error).__name__}: {error}")
    return 0


def start(repo_root, settings, session_id):
    state = read_state(repo_root)
    if state.get("entry_id") is not None and state.get("session_id") != session_id:
        # A session that died without a Stop left this entry running: end it where that session was last seen.
        close_abandoned(repo_root, settings, state)
        state = {}
    if state.get("entry_id") is None:
        entry = client(repo_root, settings).start_entry(settings["project_id"], settings["activity_id"])
        state = {"entry_id": entry["id"], "session_id": session_id}
    touch(repo_root, state)


def close_abandoned(repo_root, settings, state):
    # The state clears even when the stop fails, so one bad entry can't block every later start.
    (repo_root / STATE_PATH).unlink(missing_ok=True)
    try:
        end = datetime.fromisoformat(state["last_seen"])
    except (KeyError, TypeError, ValueError):
        end = None
    client(repo_root, settings).stop_entry(state["entry_id"], end)


def touch(repo_root, state=None):
    """Record now as the running entry's last-seen time, if there is a running entry."""
    state = read_state(repo_root) if state is None else state
    if state.get("entry_id") is not None:
        state["last_seen"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_state(repo_root, state)


def stop(repo_root, settings):
    entry_id = read_state(repo_root).get("entry_id")
    if entry_id is None:
        return
    # The state clears even when the stop fails, so one bad entry can't block every later start.
    (repo_root / STATE_PATH).unlink(missing_ok=True)
    client(repo_root, settings).stop_entry(entry_id)


def client(repo_root, settings):
    token = require_secret(load_env(repo_root / ".env"), TOKEN_NAME, repo_root / ".env")
    return KimaiApi(settings["url"], token)


def read_state(repo_root):
    try:
        state = json.loads((repo_root / STATE_PATH).read_text())
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def write_state(repo_root, state):
    path = repo_root / STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def warn(error):
    print(f"warning: time not recorded: {error}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
