"""Stop hook: notify with the state a turn ended in, unless a skill already notified.

The plugin's hooks run in every project it's enabled in, so a project without
.sdlc/config.toml is skipped silently. The hook never blocks the stop: it prints
nothing on stdout and always exits 0.

The message is the first sentence of the agent's last reply. A turn that ended on a
usage limit says so instead, with the time the session reruns or the limit resets.
Claude Code writes the rerun time to the transcript only after this hook returns, so a
usage-limit stop hands the message to a detached copy of this script, which waits for it.
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.telegram import MARKDOWN_LINK
from lib.config import ConfigError, find_repo_root, load_config
from lib.notify import MARKER_PATH, notify, parse_arguments

AFTER_USAGE_LIMIT = "--after-usage-limit"
CLOCK_TIME = r"\d{1,2}(?::\d{2})?\s?[ap]m"
GENERIC_TEXT = "Claude Code is waiting for you"
# Room for a sentence that names a task and a PR, short enough to read on a lock screen.
MAX_TEXT_LENGTH = 200
RERUN = re.compile(rf"continuing automatically at ({CLOCK_TIME})", re.IGNORECASE)
RESET = re.compile(rf"resets ({CLOCK_TIME})(?: \(([^)]+)\))?", re.IGNORECASE)
# Claude Code wrote the rerun line 5 ms after the hook in a real session; this leaves ample margin.
RERUN_WAIT_SECONDS = 3
RERUN_POLL_SECONDS = 0.1
SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def main(argv):
    if argv[1:2] == [AFTER_USAGE_LIMIT]:
        return send_after_usage_limit(json.loads(argv[2]))
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
        send = settings.get("stop_hook", False) and not skill_already_notified
        if send and ended_on_usage_limit(stop_input):
            marker.unlink(missing_ok=True)
            hand_off(repo_root, stop_input)
            return 0
        if send:
            send_text(repo_root, describe(stop_input.get("last_assistant_message")))
        # A send above writes the marker too, and it mustn't suppress the next stop.
        marker.unlink(missing_ok=True)
    except Exception as error:  # noqa: BLE001 - a failing hook must never block the turn from ending
        warn(error)
    return 0


def ended_on_usage_limit(stop_input):
    if stop_input.get("hook_event_name") == "StopFailure":
        return stop_input.get("error") == "rate_limit"
    return usage_limit_note(stop_input.get("transcript_path")) == "wrap_up"


def usage_limit_note(transcript_path):
    """Return the usage-limit note in force for the current turn, or None."""
    note = None
    for entry in transcript_entries(transcript_path):
        if "usageLimitNote" in entry:
            note = entry["usageLimitNote"]
        elif is_developer_prompt(entry):
            note = None
    return note


def is_developer_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    return isinstance(content, str) or any(block.get("type") == "text" for block in content or [])


def transcript_entries(transcript_path):
    if not transcript_path:
        return []
    try:
        lines = Path(transcript_path).expanduser().read_text().splitlines()
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def hand_off(repo_root, stop_input):
    handoff = {
        "repo_root": str(repo_root),
        "stop_input": stop_input,
        "transcript_length": len(transcript_entries(stop_input.get("transcript_path"))),
    }
    subprocess.Popen(
        [sys.executable, __file__, AFTER_USAGE_LIMIT, json.dumps(handoff)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def send_after_usage_limit(handoff):
    repo_root = Path(handoff["repo_root"])
    stop_input = handoff["stop_input"]
    try:
        rerun = wait_for_rerun_time(stop_input.get("transcript_path"), handoff["transcript_length"])
        send_text(repo_root, usage_limit_text(stop_input, rerun))
        (repo_root / MARKER_PATH).unlink(missing_ok=True)
    except Exception as error:  # noqa: BLE001 - a detached sender has nobody to report to
        warn(error)
    return 0


def wait_for_rerun_time(transcript_path, transcript_length):
    deadline = time.monotonic() + RERUN_WAIT_SECONDS
    while True:
        for entry in transcript_entries(transcript_path)[transcript_length:]:
            match = RERUN.search(str(entry.get("content", "")))
            if entry.get("type") == "system" and match:
                return clock_time(match.group(1))
        if time.monotonic() >= deadline:
            return None
        time.sleep(RERUN_POLL_SECONDS)


def usage_limit_text(stop_input, rerun):
    if rerun:
        return f"usage limit reached; will automatically rerun at {rerun}"
    details = " ".join(str(stop_input.get(field) or "") for field in ("last_assistant_message", "error_details"))
    reset = RESET.search(details)
    if reset:
        return f"usage limit reached; resets at {clock_time(reset.group(1), reset.group(2))}"
    return "usage limit reached"


def clock_time(text, zone_name=None):
    """Turn a time such as 3:40pm into 1540 PDT, in the named zone or the local one."""
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s?([ap]m)", text.strip(), re.IGNORECASE)
    hour = int(match.group(1)) % 12 + (12 if match.group(3).lower() == "pm" else 0)
    try:
        now = datetime.now(ZoneInfo(zone_name)) if zone_name else datetime.now().astimezone()
    except (ZoneInfoNotFoundError, ValueError):
        return f"{text} ({zone_name})"
    return now.replace(hour=hour, minute=int(match.group(2) or 0)).strftime("%H%M %Z")


def describe(last_message):
    """Return the first sentence of the agent's last reply, or the generic text without one."""
    lines = [line.strip() for line in (last_message or "").splitlines() if line.strip()]
    if not lines:
        return GENERIC_TEXT
    first_line = re.sub(r"^(#+|[-*])\s+", "", lines[0]).replace("**", "").replace("`", "")
    sentence = SENTENCE_END.split(first_line, maxsplit=1)[0]
    if len(sentence) <= MAX_TEXT_LENGTH:
        return sentence
    # Cutting through a link would leave broken Markdown, so long text loses its links.
    plain = MARKDOWN_LINK.sub(r"\1", sentence)
    return plain if len(plain) <= MAX_TEXT_LENGTH else plain[: MAX_TEXT_LENGTH - 1] + "…"


def send_text(repo_root, text):
    result = notify(parse_arguments(["--kind", "STOP", "--skill", "session", "--text", text]), start=repo_root)
    if "warning" in result:
        print(f"warning: {result['warning']}", file=sys.stderr)


def warn(error):
    print(f"warning: stop notification not sent: {type(error).__name__}: {error}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
