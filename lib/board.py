"""Print the project's open Kaneo tasks, one line each: key, status, title, labels, open blockers, and id.

The Kaneo MCP board read returns every task's full description, which costs far more
context than a skill needs to pick or order work. A task is open unless it's in a final
column or archived. Exits 1 with the reason on stderr when the board can't be read.
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.kaneo import KaneoApi
from lib.backends.rest import RestError
from lib.config import ConfigError, find_repo_root, load_config
from lib.env import EnvError, load_env, require_secret

ARCHIVED = "archived"
# Kaneo has no bulk relations call, so each open task costs one request. These run in parallel.
MAX_PARALLEL_REQUESTS = 8
PLANNED = "planned"


def main(argv=None, start=None, api=None):
    arguments = parse_arguments(argv)
    try:
        repo_root = find_repo_root(start)
        settings = load_config(repo_root).get("kaneo", {})
        api = api or connect(repo_root, settings)
        lines = board_lines(api, settings, arguments.status)
    except (ConfigError, EnvError, RestError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--status",
        type=lambda text: [status.strip() for status in text.split(",") if status.strip()],
        help="print only these statuses, comma-separated, such as in-progress,needs-human",
    )
    return parser.parse_args(argv)


def connect(repo_root, settings):
    for key in ("project_id", "url"):
        if not settings.get(key):
            raise ConfigError(f"kaneo.{key} is not set in .sdlc/config.toml")
    env_path = repo_root / ".env"
    return KaneoApi(settings["url"], require_secret(load_env(env_path), "KANEO_API_KEY", env_path))


def board_lines(api, settings, statuses=None):
    columns, tasks = read_board(api, settings["project_id"])
    open_statuses = [column["slug"] for column in columns if not column["isFinal"]] + [PLANNED]
    shown = [
        task for task in tasks if task["status"] in open_statuses and (statuses is None or task["status"] in statuses)
    ]
    shown.sort(key=lambda task: (open_statuses.index(task["status"]), task["position"]))
    with ThreadPoolExecutor(MAX_PARALLEL_REQUESTS) as pool:
        relations = list(pool.map(lambda task: api.task_relations(task["id"]), shown))
    slug = settings.get("project_slug", "")
    return [describe(task, task_relations, slug) for task, task_relations in zip(shown, relations, strict=True)]


def read_board(api, project_id):
    """Return the columns and every task, with labels merged from each related page."""
    columns = []
    tasks = {}
    page = 1
    while True:
        related_page = 1
        while True:
            response = api.list_tasks(project_id, page, related_page)
            data = response["data"]
            columns = data["columns"] or columns
            for task in board_tasks(data):
                labels = tasks.setdefault(task["id"], {**task, "labels": []})["labels"]
                labels.extend(label for label in task.get("labels", []) if label not in labels)
            if related_page >= response["pagination"]["relatedTotalPages"]:
                break
            related_page += 1
        if page >= response["pagination"]["totalPages"]:
            return columns, list(tasks.values())
        page += 1


def board_tasks(data):
    yield from data.get("plannedTasks", [])
    yield from data.get("archivedTasks", [])
    for column in data["columns"]:
        yield from column.get("tasks", [])


def describe(task, relations, slug):
    parts = [task_key(slug, task["number"]), f"[{task['status']}]", task["title"]]
    labels = sorted(label["name"] for label in task.get("labels", []))
    if labels:
        parts.append(f"(labels: {', '.join(labels)})")
    blockers = sorted(
        relation["sourceTask"]["number"]
        for relation in relations
        if relation["relationType"] == "blocks"
        and relation["targetTaskId"] == task["id"]
        and is_open(relation["sourceTask"])
    )
    if blockers:
        parts.append(f"(blocked by: {', '.join(task_key(slug, number) for number in blockers)})")
    parts.append(f"id={task['id']}")
    return " ".join(parts)


def is_open(related_task):
    # A blocker outside the caller's workspace comes back as null, and can't be checked.
    return related_task is not None and not related_task["isCompleted"] and related_task["status"] != ARCHIVED


def task_key(slug, number):
    return f"{slug}-{number}" if slug else f"#{number}"


if __name__ == "__main__":
    sys.exit(main())
