#!/usr/bin/env bash
# Builds the scratch repo every plan-feature case starts from: a small task-list CLI, set up for
# the mocked Outline collection.
set -euo pipefail

git init --quiet
mkdir -p .sdlc
cat > .sdlc/config.toml <<'TOML'
config_version = 1
branch_prefix = "ex-"

[docs]
backend = "outline"

[guidelines]
architecture = "00000000-0000-4000-8000-00000000a4c0"
doc_style = "00000000-0000-4000-8000-00000000d0c5"
task_style = "00000000-0000-4000-8000-0000000074a5"
testing = "00000000-0000-4000-8000-0000000075e5"

[kaneo]
columns = { done = "mockcolumndone0000000001", "in-progress" = "mockcolumnprogress000001", "needs-human" = "mockcolumnhuman000000001", "to-do" = "mockcolumntodo0000000001" }
project_id = "mockproject0000000000001"
project_slug = "EX"
url = "https://kaneo.example.com"
workspace_id = "mockworkspace00000000001"

[notify]
enabled = false

[outline]
collection_id = "00000000-0000-4000-8000-0000000c011e"
url = "https://outline.example.com"

[tracker]
backend = "kaneo"
TOML
cat > README.md <<'MD'
# tasks

A command-line task list. `tasks.py add <title>` adds a task, and `tasks.py list` prints them
as a table. Tasks are stored in `tasks.json`.
MD
cat > tasks.py <<'PY'
import json
import sys
from pathlib import Path

STORE = Path("tasks.json")


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else []


def main(argv):
    tasks = load()
    if argv[:1] == ["add"]:
        tasks.append({"title": " ".join(argv[1:]), "done": False})
        STORE.write_text(json.dumps(tasks))
    elif argv[:1] == ["list"]:
        for number, task in enumerate(tasks, start=1):
            print(f"{number:>3}  {'x' if task['done'] else ' '}  {task['title']}")


if __name__ == "__main__":
    main(sys.argv[1:])
PY
git add . && git -c user.email=eval@example.com -c user.name=eval commit --quiet -m "Initial commit"
