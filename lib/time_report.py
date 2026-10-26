"""Print the project's time report as JSON: hours from Kimai, and each done epic's date and days from the start.

Agent hours are the time_tracking.agent_user's entries, and human hours are everyone else's.
`--markdown` prints the same report as tables. Exits 1 with the reason on stderr when the report can't be built.
"""

import argparse
import json
import sys
from datetime import datetime
from functools import cache
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.kimai import ENTRY_PAGE_SIZE, KimaiApi
from lib.backends.rest import RestError
from lib.board import connect as connect_kaneo
from lib.board import read_board
from lib.config import ConfigError, find_repo_root, load_config
from lib.env import EnvError, load_env, require_secret

EPIC_LABEL = "epic"
REQUIRED_KEYS = ("url", "project_id", "agent_user")
SECONDS_PER_HOUR = 3600


def main(argv=None, start=None):
    arguments = parse_arguments(argv)
    try:
        repo_root = find_repo_root(start)
        config = load_config(repo_root)
        settings = config.get("time_tracking")
        if settings is None:
            raise ConfigError("no [time_tracking] section in .sdlc/config.toml, so there is no Kimai project to report")
        missing = [key for key in REQUIRED_KEYS if key not in settings]
        if missing:
            raise ConfigError(f"[time_tracking] is missing {', '.join(missing)}")
        env_path = repo_root / ".env"
        token = require_secret(load_env(env_path), "KIMAI_API_TOKEN", env_path)
        kimai = KimaiApi(settings["url"], token)
        kaneo_settings = config.get("kaneo", {})
        kaneo = connect_kaneo(repo_root, kaneo_settings)
        report = build_report(kimai, kaneo, settings, kaneo_settings)
    except (ConfigError, EnvError, RestError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(markdown(report) if arguments.markdown else json.dumps(report, indent=2))
    return 0


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true", help="print tables instead of JSON")
    return parser.parse_args(argv)


def build_report(kimai, kaneo, settings, kaneo_settings):
    entries = read_entries(kimai, settings["project_id"])
    usernames = cache(lambda: {listed["id"]: listed["username"] for listed in kimai.list_users()})
    seconds = {"agent": 0, "human": 0}
    for entry in entries:
        who = "agent" if entry_user(entry, usernames) == settings["agent_user"] else "human"
        seconds[who] += entry_seconds(entry)
    begins = [entry["begin"] for entry in entries]
    start = min(begins, key=parse_time) if begins else None
    return {
        "hours": {
            "total": hours(seconds["agent"] + seconds["human"]),
            "agent": hours(seconds["agent"]),
            "human": hours(seconds["human"]),
        },
        "start": start,
        "milestones": milestones(kaneo, kaneo_settings, start),
    }


def read_entries(kimai, project_id):
    entries = []
    page = 1
    while True:
        batch = kimai.list_entries(project_id, page)
        entries.extend(batch)
        if len(batch) < ENTRY_PAGE_SIZE:
            return entries
        page += 1


def entry_user(entry, usernames):
    """The entry's username. Kimai may send the user as an id, which the users list resolves."""
    user = entry.get("user")
    return user.get("username") if isinstance(user, dict) else usernames().get(user)


def entry_seconds(entry):
    if entry.get("duration"):
        return entry["duration"]
    if entry.get("end"):
        return (parse_time(entry["end"]) - parse_time(entry["begin"])).total_seconds()
    # A running entry counts up to now.
    begin = parse_time(entry["begin"])
    return (datetime.now(begin.tzinfo) - begin).total_seconds()


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hours(seconds):
    return round(seconds / SECONDS_PER_HOUR, 2)


def milestones(kaneo, settings, start):
    columns, tasks = read_board(kaneo, settings["project_id"])
    final = {column["slug"] for column in columns if column["isFinal"]}
    rows = []
    for task in tasks:
        if task["status"] not in final or EPIC_LABEL not in [label["name"] for label in task.get("labels", [])]:
            continue
        done = done_date(kaneo.task_activity(task["id"]), task["status"])
        days = (done - parse_time(start).date()).days if start and done else None
        rows.append(
            {"title": task["title"], "number": task["number"], "done": done.isoformat() if done else None, "days": days}
        )
    return sorted(rows, key=lambda row: (row["done"] is None, row["done"] or ""))


def done_date(activity, status):
    """The date of the latest move into `status`."""
    moves = [
        item["createdAt"]
        for item in activity
        if item["type"] == "status_changed" and item.get("eventData", {}).get("newStatus") == status
    ]
    return parse_time(max(moves)).date() if moves else None


def markdown(report):
    figures = report["hours"]
    lines = [
        "| Hours | |",
        "|---|---|",
        f"| Total | {figures['total']:.2f} |",
        f"| Agent | {figures['agent']:.2f} |",
        f"| Human | {figures['human']:.2f} |",
        "",
        f"Project start: {report['start'] or 'no entries'}",
        "",
        "| Milestone | Done | Days from start |",
        "|---|---|---|",
    ]
    for row in report["milestones"]:
        lines.append(f"| {row['title']} | {row['done'] or ''} | {'' if row['days'] is None else row['days']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
