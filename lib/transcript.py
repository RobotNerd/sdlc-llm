"""Reads a Claude Code session transcript, a JSON Lines file with one entry per line."""

import json
import re
from pathlib import Path

REPORT_ORIGINS = ("peer", "task-notification")
TASK_NOTIFICATION = re.compile(
    r"<task-id>([^<]+)</task-id>.*?<status>([^<]+)</status>\s*<summary>([^<]*)</summary>", re.DOTALL
)


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
    """Return the ids of background subagents that have started and whose task notification hasn't said finished."""
    running = set()
    for entry in entries:
        running -= {agent for agent, status, summary in task_notifications(entry) if has_finished(status, summary)}
        result = entry.get("toolUseResult")
        if entry.get("type") == "user" and isinstance(result, dict) and result.get("isAsync") and result.get("agentId"):
            running.add(result["agentId"])
    return running


def has_finished(status, summary):
    """A completed notification can mean the subagent only stopped to wait on background work of its own."""
    return status != "completed" or summary.endswith("finished")


def task_notifications(entry):
    """Return (agent id, status, summary) for each task notification an entry carries."""
    if entry.get("type") not in ("queue-operation", "user"):
        return []
    content = (
        entry.get("content") if entry.get("type") == "queue-operation" else entry.get("message", {}).get("content")
    )
    if not isinstance(content, str):
        return []
    return [(agent, status, summary) for agent, status, summary in TASK_NOTIFICATION.findall(content)]


def turn_started_by_finished_subagents(entries):
    """Whether the turn since the last Stop holds only reports from subagents that finished before that Stop."""
    last_stop = max((i for i, entry in enumerate(entries) if entry.get("subtype") == "stop_hook_summary"), default=None)
    if last_stop is None:
        return False
    still_running = running_background_subagents(entries[:last_stop])
    launched = {
        entry["toolUseResult"]["agentId"]
        for entry in entries[:last_stop]
        if isinstance(entry.get("toolUseResult"), dict) and entry["toolUseResult"].get("agentId")
    }
    reporters = set()
    for entry in entries[last_stop + 1 :]:
        origin = entry.get("origin")
        if entry.get("type") == "user" and isinstance(origin, dict) and origin.get("kind") in REPORT_ORIGINS:
            reporters.add(origin.get("from") or "")
            reporters.update(agent for agent, _, _ in task_notifications(entry))
        elif is_developer_prompt(entry) or entry.get("toolUseResult", {}).get("agentId"):
            return False
    return bool(reporters) and reporters <= launched - still_running
