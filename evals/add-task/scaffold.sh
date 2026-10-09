#!/usr/bin/env bash
# Builds the scratch repo every add-task case starts from: a git repo set up for the mocked
# Kaneo project EX and Outline collection.
set -euo pipefail

git init --quiet
mkdir -p .sdlc
cat > .sdlc/config.toml <<'TOML'
config_version = 1
branch_prefix = "ex-"

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
printf '# example\n\nA small example project.\n\nTeh tests live in tests/.\n' > README.md
git add . && git -c user.email=eval@example.com -c user.name=eval commit --quiet -m "Initial commit"
