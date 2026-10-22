"""Reads a Claude Code session transcript, a JSON Lines file with one entry per line."""

import json
import re
from pathlib import Path

TASK_NOTIFICATION = re.compile(r"<task-id>([^<]+)</task-id>")


def transcript_entries(transcript_path):
    """Return the transcript's entries, or an empty list when it is missing or unreadable."""
    if not transcript_path:
        return []
    try:
        lines = Path(transcript_path).expanduser().read_text().splitlines()
    except (OSError, ValueError):
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


def is_developer_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    return isinstance(content, str) or any(block.get("type") == "text" for block in content or [])


def usage_limit_note(entries):
    """Return the usage-limit note in force for the current turn, or None."""
    note = None
    for entry in entries:
        if "usageLimitNote" in entry:
            note = entry["usageLimitNote"]
        elif is_developer_prompt(entry):
            note = None
    return note


def running_background_subagents(entries):
    """Return the ids of background subagents that have started and not yet reported back."""
    running = set()
    for entry in entries:
        running -= finished_subagents(entry)
        result = entry.get("toolUseResult")
        if entry.get("type") == "user" and isinstance(result, dict) and result.get("isAsync") and result.get("agentId"):
            running.add(result["agentId"])
    return running


def finished_subagents(entry):
    """Return the agent ids an entry reports as finished: by task notification or by hand-back."""
    finished = set(TASK_NOTIFICATION.findall(json.dumps(entry)))
    origin = entry.get("origin")
    if entry.get("type") == "user" and isinstance(origin, dict) and origin.get("from"):
        finished.add(origin["from"])
    return finished
