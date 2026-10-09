"""Set up a project for sdlc-llm. Every subcommand is idempotent.

provision <values.json>: ensure the Kaneo project, its columns and labels, and the Outline
collection with its structure and the default guideline docs. Prints the ids as JSON.

write <values.json> <ids.json>: write or merge .sdlc/config.toml, .env.example, .gitignore,
CLAUDE.md, and .claude/settings.json. ids.json is provision's output. Prints the paths changed.

check: check each backend in .sdlc/config.toml, and send a test notification to each channel.
Prints each result as JSON, and exits 1 when any fails.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT))

from repo_files import RepoFilesError, write_all

from lib.backends.interfaces import NotifierError
from lib.backends.kaneo import KaneoApi
from lib.backends.outline import OutlineApi
from lib.backends.rest import RestError
from lib.config import ConfigError, find_repo_root, load_config, lookup
from lib.env import EnvError, load_env, require_secret
from lib.notify import NotifyError, build_notifier, channels_in_order

# In board order. Only "done" is final.
COLUMNS = (
    ("to-do", "To Do", False),
    ("in-progress", "In Progress", False),
    ("needs-human", "Needs Human", False),
    ("done", "Done", True),
)
LABEL_COLORS = {
    "bug": "#DC2626",
    "chore": "#6B7280",
    "deferred": "#9CA3AF",
    "docs": "#0891B2",
    "epic": "#7C3AED",
    "feature": "#2563EB",
    "follow-up": "#D97706",
    "refactor": "#059669",
    "wont-do": "#4B5563",
}
DEFAULT_PROJECT_ICON = "Layout"
# Parents come before their children.
STRUCTURE = {
    "docs": "Finalized docs: architecture, design, tutorials.",
    "docs/guidelines": "The docs skills read as input.",
    "reports": "Epic and batch reports.",
    "reports/batches": "One report per implement-task batch.",
    "reports/epics": "One report per epic.",
    "spec": "Specs and PRDs, one per feature.",
}
GUIDELINES_PATH = "docs/guidelines"
DEFAULT_GUIDELINES = PLUGIN_ROOT / "lib/references/guidelines"
SKILL_EVALS_SECTION = "Skill evals"


class SetupError(Exception):
    pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subcommands = parser.add_subparsers(dest="command", required=True)
    provision_parser = subcommands.add_parser("provision", help="ensure the Kaneo project and Outline collection")
    provision_parser.add_argument("values", type=Path, help="JSON with the kaneo and outline settings")
    write_parser = subcommands.add_parser("write", help="write the repo's config, CLAUDE.md, and settings")
    write_parser.add_argument("values", type=Path, help="the values JSON given to provision, plus commands and notify")
    write_parser.add_argument("ids", type=Path, help="provision's output")
    subcommands.add_parser("check", help="check each backend and send a test notification")
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "provision":
            result = provision(arguments.values)
        elif arguments.command == "write":
            result = write(arguments.values, arguments.ids)
        else:
            result = check()
    except (ConfigError, EnvError, RepoFilesError, RestError, SetupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    if result.get("ok") is False:
        failing = [f"{entry['name']}: {entry['detail']}" for entry in result["checks"] if not entry["ok"]]
        print("error: " + "; ".join(failing), file=sys.stderr)
        return 1
    return 0


def provision(values_path):
    values = read_values(values_path)
    repo_root = find_repo_root()
    env_path = repo_root / ".env"
    secrets = load_env(env_path)
    created = []
    kaneo = KaneoApi(values["kaneo"]["url"], require_secret(secrets, "KANEO_API_KEY", env_path))
    outline = OutlineApi(values["outline"]["url"], require_secret(secrets, "OUTLINE_API_KEY", env_path))
    is_plugin = (repo_root / ".claude-plugin/plugin.json").is_file()
    return {
        "created": created,
        "kaneo": provision_kaneo(kaneo, values["kaneo"], created),
        "outline": provision_outline(outline, values["outline"], is_plugin, created),
    }


def write(values_path, ids_path):
    values = read_values(values_path)
    ids = read_json(ids_path)
    if not {"kaneo", "outline"} <= set(ids):
        raise SetupError(f"{ids_path} isn't provision's output: it needs kaneo and outline")
    repo_root = find_repo_root()
    is_plugin = (repo_root / ".claude-plugin/plugin.json").is_file()
    changed, kept = write_all(repo_root, values, ids, is_plugin)
    return {"changed": changed, "kept": kept}


def check():
    repo_root = find_repo_root()
    config = load_config(repo_root)
    env_path = repo_root / ".env"
    checks = [
        run_check("kaneo", lambda: check_kaneo(config, load_env(env_path), env_path)),
        run_check("outline", lambda: check_outline(config, load_env(env_path), env_path)),
    ]
    notify = config.get("notify", {})
    if not notify.get("enabled", False):
        checks.append({"detail": "notifications are off", "name": "notify", "ok": True})
    else:
        try:
            channels = channels_in_order(notify)
        except NotifyError as error:
            checks.append({"detail": str(error), "name": "notify", "ok": False})
        else:
            if not channels:
                checks.append({"detail": "no channels in notify.channels", "name": "notify", "ok": False})
            for channel in channels:
                checks.append(
                    run_check(channel.get("type", "unknown"), lambda channel=channel: send_test(channel, repo_root))
                )
    return {"checks": checks, "ok": all(entry["ok"] for entry in checks)}


def run_check(name, step):
    try:
        return {"detail": step(), "name": name, "ok": True}
    except (EnvError, NotifierError, NotifyError, RestError, SetupError) as error:
        return {"detail": str(error), "name": name, "ok": False}


def check_kaneo(config, secrets, env_path):
    kaneo = KaneoApi(required(config, "kaneo.url"), require_secret(secrets, "KANEO_API_KEY", env_path))
    project_id = required(config, "kaneo.project_id")
    projects = kaneo.list_projects(required(config, "kaneo.workspace_id"))
    project = next((project for project in projects if project["id"] == project_id), None)
    if project is None:
        raise SetupError(f"no project {project_id} in workspace {config['kaneo']['workspace_id']}")
    return f"project {project['slug']}"


def check_outline(config, secrets, env_path):
    outline = OutlineApi(required(config, "outline.url"), require_secret(secrets, "OUTLINE_API_KEY", env_path))
    collection_id = required(config, "outline.collection_id")
    collection = next(
        (collection for collection in outline.list_collections() if collection["id"] == collection_id), None
    )
    if collection is None:
        raise SetupError(f"no collection {collection_id}")
    return f"collection {collection['name']}"


def send_test(channel, repo_root):
    text = f"{repo_root.name} · setup-project · TEST: notifications reach {channel.get('type')} ({channel.get('role')})"
    build_notifier(channel, repo_root).send("TEST", text)
    return "test notification sent"


def required(config, key):
    value = lookup(config, key)
    if not value:
        raise SetupError(f"{key} isn't set in .sdlc/config.toml")
    return value


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise SetupError(f"can't read {path}: {error}") from None


def read_values(path):
    values = read_json(path)
    required = {
        "kaneo": ("project_name", "project_slug", "url", "workspace_id"),
        "outline": ("collection_name", "url"),
    }
    missing = [
        f"{section}.{key}" for section, keys in required.items() for key in keys if not values.get(section, {}).get(key)
    ]
    if missing:
        raise SetupError(f"{path} is missing: {', '.join(missing)}")
    return values


def provision_kaneo(kaneo, settings, created):
    workspace_id, slug = settings["workspace_id"], settings["project_slug"]
    project = next((project for project in kaneo.list_projects(workspace_id) if project["slug"] == slug), None)
    is_new = project is None
    if is_new:
        icon = settings.get("project_icon", DEFAULT_PROJECT_ICON)
        project = kaneo.create_project(workspace_id, settings["project_name"], slug, icon)
        created.append(f"Kaneo project {slug}")

    columns = ensure_columns(kaneo, project["id"], is_new, created)
    labels = ensure_labels(kaneo, workspace_id, created)
    required_slugs = {slug for slug, _, _ in COLUMNS}
    return {
        "columns": {column["slug"]: column["id"] for column in columns if column["slug"] in required_slugs},
        "extra_columns": [column["slug"] for column in columns if column["slug"] not in required_slugs],
        "labels": labels,
        "project_id": project["id"],
        "project_slug": project["slug"],
        "workspace_id": workspace_id,
    }


def ensure_columns(kaneo, project_id, is_new, created):
    columns = sorted(kaneo.list_columns(project_id), key=lambda column: column["position"])
    if is_new:
        # Kaneo gives a new project default columns we don't use, such as "in-review". A new
        # project has no tasks, so they're safe to delete. An existing project keeps its extras.
        required_slugs = {slug for slug, _, _ in COLUMNS}
        for column in [column for column in columns if column["slug"] not in required_slugs]:
            kaneo.delete_column(column["id"], column["slug"])
            columns.remove(column)
            created.append(f"Kaneo default column {column['slug']} removed")
    by_slug = {column["slug"]: column for column in columns}
    for slug, name, is_final in COLUMNS:
        if slug not in by_slug:
            column = kaneo.create_column(project_id, name, is_final)
            if column["slug"] != slug:
                raise SetupError(f"Kaneo named the new column {column['slug']!r}, not {slug!r}")
            columns.append(column)
            by_slug[slug] = column
            created.append(f"Kaneo column {slug}")
        elif is_final and not by_slug[slug]["isFinal"]:
            by_slug[slug].update(kaneo.mark_column_final(by_slug[slug]["id"], slug))
            created.append(f"Kaneo column {slug} marked final")

    # The board shows the required columns in order, then any others in their current order.
    required_ids = [by_slug[slug]["id"] for slug, _, _ in COLUMNS]
    current_required_order = [column["id"] for column in columns if column["id"] in required_ids]
    if current_required_order != required_ids:
        extras = [column["id"] for column in columns if column["id"] not in required_ids]
        kaneo.reorder_columns(project_id, required_ids + extras)
        created.append("Kaneo column order")
        columns.sort(key=lambda column: (required_ids + extras).index(column["id"]))
    return columns


def ensure_labels(kaneo, workspace_id, created):
    # A label with a taskId is one task's copy, not the workspace label itself.
    existing = {
        label["name"]: label["id"] for label in kaneo.list_workspace_labels(workspace_id) if label.get("taskId") is None
    }
    for name, color in LABEL_COLORS.items():
        if name not in existing:
            existing[name] = kaneo.create_label(workspace_id, name, color)["id"]
            created.append(f"Kaneo label {name}")
    return {name: existing[name] for name in sorted(LABEL_COLORS)}


def provision_outline(outline, settings, is_plugin, created):
    name = settings["collection_name"]
    collection = next((collection for collection in outline.list_collections() if collection["name"] == name), None)
    if collection is None:
        collection = outline.create_collection(name)
        created.append(f"Outline collection {name}")

    tree = outline.document_tree(collection["id"])
    paths = {}
    for path, description in STRUCTURE.items():
        parent_path, _, title = path.rpartition("/")
        node = find_child(tree if not parent_path else paths[parent_path]["children"], title)
        if node is None:
            document = outline.create_document(
                title, description, collection["id"], paths.get(parent_path, {}).get("id")
            )
            node = {"children": [], "id": document["id"], "title": title}
            (tree if not parent_path else paths[parent_path]["children"]).append(node)
            created.append(f"Outline doc {path}")
        paths[path] = node

    guidelines_node = paths[GUIDELINES_PATH]
    for title, text in default_guidelines(is_plugin):
        if find_child(guidelines_node["children"], title) is None:
            document = outline.create_document(title, text, collection["id"], guidelines_node["id"])
            guidelines_node["children"].append({"children": [], "id": document["id"], "title": title})
            created.append(f"Outline doc {GUIDELINES_PATH}/{title}")
    # Every guideline doc, the project's own as well as the defaults, so write can map each role.
    guidelines = {
        node["title"]: node["id"] for node in sorted(guidelines_node["children"], key=lambda node: node["title"])
    }

    return {
        "collection_id": collection["id"],
        "docs": {path: node["id"] for path, node in paths.items()},
        "guidelines": guidelines,
    }


def find_child(nodes, title):
    return next((node for node in nodes if node["title"] == title), None)


def default_guidelines(is_plugin):
    for path in sorted(DEFAULT_GUIDELINES.glob("*.md")):
        heading, _, body = path.read_text().partition("\n")
        title = heading.removeprefix("# ").strip()
        text = body.strip()
        if not is_plugin:
            text = without_section(text, SKILL_EVALS_SECTION)
        yield title, text + "\n"


def without_section(text, heading):
    """Drop a ## section and its Contents entry. Skill evals only apply to plugin repos."""
    text = re.sub(rf"^## {re.escape(heading)}\n.*?(?=^## |\Z)", "", text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(rf"^\* {re.escape(heading)}\n", "", text, flags=re.MULTILINE)
    return text.rstrip()


if __name__ == "__main__":
    sys.exit(main())
