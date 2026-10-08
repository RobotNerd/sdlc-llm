"""Set up a project for sdlc-llm. Every subcommand is idempotent.

provision <values.json>: ensure the Kaneo project, its columns and labels, and the Outline
collection with its structure and the default guideline docs. Prints the ids as JSON.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.kaneo import KaneoApi
from lib.backends.outline import OutlineApi
from lib.backends.rest import RestError
from lib.config import ConfigError, find_repo_root
from lib.env import EnvError, load_env, require_secret

# In board order. Only "done" is final.
COLUMNS = (("to-do", "To Do", False), ("in-progress", "In Progress", False), ("needs-human", "Needs Human", False),
           ("done", "Done", True))
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
    arguments = parser.parse_args(argv)

    try:
        result = provision(arguments.values)
    except (ConfigError, EnvError, RestError, SetupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
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


def read_values(path):
    try:
        values = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise SetupError(f"can't read {path}: {error}") from None
    required = {
        "kaneo": ("project_name", "project_slug", "url", "workspace_id"),
        "outline": ("collection_name", "url"),
    }
    missing = [f"{section}.{key}" for section, keys in required.items() for key in keys
               if not values.get(section, {}).get(key)]
    if missing:
        raise SetupError(f"{path} is missing: {', '.join(missing)}")
    return values


def provision_kaneo(kaneo, settings, created):
    workspace_id, slug = settings["workspace_id"], settings["project_slug"]
    project = next((project for project in kaneo.list_projects(workspace_id) if project["slug"] == slug), None)
    if project is None:
        icon = settings.get("project_icon", DEFAULT_PROJECT_ICON)
        project = kaneo.create_project(workspace_id, settings["project_name"], slug, icon)
        created.append(f"Kaneo project {slug}")

    columns = ensure_columns(kaneo, project["id"], created)
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


def ensure_columns(kaneo, project_id, created):
    columns = sorted(kaneo.list_columns(project_id), key=lambda column: column["position"])
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
    existing = {label["name"]: label["id"] for label in kaneo.list_workspace_labels(workspace_id)
                if label.get("taskId") is None}
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
            document = outline.create_document(title, description, collection["id"], paths.get(parent_path, {}).get("id"))
            node = {"children": [], "id": document["id"], "title": title}
            (tree if not parent_path else paths[parent_path]["children"]).append(node)
            created.append(f"Outline doc {path}")
        paths[path] = node

    guidelines = {}
    guidelines_node = paths[GUIDELINES_PATH]
    for title, text in default_guidelines(is_plugin):
        node = find_child(guidelines_node["children"], title)
        if node is None:
            node = outline.create_document(title, text, collection["id"], guidelines_node["id"])
            created.append(f"Outline doc {GUIDELINES_PATH}/{title}")
        guidelines[title] = node["id"]

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
