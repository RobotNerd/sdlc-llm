#!/usr/bin/env bash
# Builds the scratch repo every refine-backlog case starts from: a small task-list CLI with a
# commit on each day of September 2026, so a task created before then has 30 active days.
set -euo pipefail

git init --quiet --initial-branch=main
mkdir -p .sdlc
cat > .sdlc/config.toml <<'TOML'
config_version = 1
default_branch = "main"
remote = "origin"
stale_active_days = 20

[docs]
backend = "outline"

[guidelines]
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

A command-line task list. `tasks.py add <title>` adds a task, and `tasks.py list` prints them.
MD
git add . && git -c user.email=eval@example.com -c user.name=eval commit --quiet -m "Initial commit" --date=2026-08-15T10:00:00Z
for day in $(seq -w 1 30); do
  echo "$day" > day.txt
  git add day.txt
  GIT_COMMITTER_DATE="2026-09-${day}T10:00:00Z" git -c user.email=eval@example.com -c user.name=eval \
    commit --quiet -m "Work on day $day" --date="2026-09-${day}T10:00:00Z"
done
