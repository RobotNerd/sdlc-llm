"""The board script and the SessionStart hook that prints the open work."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from hooks import session_start
from lib import board

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "lib/board.py"
HOOK = ROOT / "hooks/session_start.py"

CONFIG = """\
config_version = 1

[kaneo]
project_id = "project-1"
project_slug = "EX"
url = "http://127.0.0.1:9"
"""
COLUMNS = [
    {"slug": "to-do", "isFinal": False},
    {"slug": "in-progress", "isFinal": False},
    {"slug": "in-review", "isFinal": False},
    {"slug": "done", "isFinal": True},
]


def task(task_id, number, status, position=0, labels=()):
    return {
        "id": task_id,
        "labels": [{"id": f"label-{name}", "name": name} for name in labels],
        "number": number,
        "position": position,
        "status": status,
        "title": f"Task {number}",
    }


def blocks(source, target, source_status="to-do"):
    return {
        "relationType": "blocks",
        "sourceTask": {"isCompleted": source_status == "done", "number": source["number"], "status": source_status},
        "targetTaskId": target["id"],
    }


class FakeKaneo:
    def __init__(self, tasks, relations):
        self.tasks = tasks
        self.relations = relations

    def list_tasks(self, project_id, page, related_page):
        columns = [
            {**column, "tasks": [item for item in self.tasks if item["status"] == column["slug"]]} for column in COLUMNS
        ]
        data = {
            "archivedTasks": [item for item in self.tasks if item["status"] == "archived"],
            "columns": columns,
            "plannedTasks": [item for item in self.tasks if item["status"] == "planned"],
        }
        return {"data": data, "pagination": {"relatedTotalPages": 1, "totalPages": 1}}

    def task_relations(self, task_id):
        return self.relations.get(task_id, [])


def make_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(CONFIG)
    return tmp_path


def messy_board():
    done = task("done-1", 1, "done")
    archived = task("archived-2", 2, "archived")
    blocker = task("open-3", 3, "to-do", position=0)
    blocked = task("open-4", 4, "in-progress", labels=("feature", "bug"))
    relations = {
        blocked["id"]: [blocks(blocker, blocked), blocks(done, blocked, "done"), blocks(archived, blocked, "archived")]
    }
    return FakeKaneo([done, archived, blocked, blocker], relations)


def run_board(tmp_path, capsys, *argv, api=None):
    exit_code = board.main(list(argv), start=make_repo(tmp_path), api=api or messy_board())
    return exit_code, capsys.readouterr()


def test_only_open_tasks_print_with_their_open_blockers(tmp_path, capsys):
    exit_code, output = run_board(tmp_path, capsys)

    assert exit_code == 0
    assert output.out.splitlines() == [
        "EX-3 [to-do] Task 3 id=open-3",
        "EX-4 [in-progress] Task 4 (labels: bug, feature) (blocked by: EX-3) id=open-4",
    ]


def test_status_filters_the_tasks(tmp_path, capsys):
    exit_code, output = run_board(tmp_path, capsys, "--status", "in-progress,in-review")

    assert exit_code == 0
    assert [line.split()[0] for line in output.out.splitlines()] == ["EX-4"]


def test_planned_tasks_are_open_and_follow_the_columns(tmp_path, capsys):
    api = FakeKaneo([task("planned-5", 5, "planned"), task("open-6", 6, "in-review")], {})

    _, output = run_board(tmp_path, capsys, api=api)

    assert [line.split()[0] for line in output.out.splitlines()] == ["EX-6", "EX-5"]


def test_a_missing_api_key_exits_1_and_names_it(tmp_path):
    repo = make_repo(tmp_path)
    (repo / ".env").write_text("DISCORD_WEBHOOK_URL=https://example.invalid\n")
    environment = {name: value for name, value in os.environ.items() if name != "KANEO_API_KEY"}

    result = subprocess.run(
        [sys.executable, str(BOARD)], capture_output=True, check=False, cwd=repo, env=environment, text=True
    )

    assert result.returncode == 1
    assert "KANEO_API_KEY" in result.stderr
    assert result.stdout == ""


def test_the_hook_prints_nothing_outside_a_set_up_repo(tmp_path):
    (tmp_path / ".git").mkdir()

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        input=json.dumps({"cwd": str(tmp_path)}),
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def run_hook(repo, monkeypatch, capsys, api):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": str(repo)})))
    exit_code = session_start.main(api=api)
    return exit_code, capsys.readouterr().out


def test_the_hook_prints_the_in_progress_and_in_review_tasks(tmp_path, monkeypatch, capsys):
    exit_code, output = run_hook(make_repo(tmp_path), monkeypatch, capsys, messy_board())

    assert exit_code == 0
    lines = output.splitlines()
    assert lines[0].startswith("Kaneo tasks in progress or needing review")
    assert [line.split()[0] for line in lines[1:]] == ["EX-4"]


def test_the_hook_says_so_when_nothing_is_open(tmp_path, monkeypatch, capsys):
    _, output = run_hook(make_repo(tmp_path), monkeypatch, capsys, FakeKaneo([], {}))

    assert output == "No Kaneo tasks are in progress or needing review.\n"


def test_the_hook_reports_a_board_it_cant_read_and_still_exits_0(tmp_path, monkeypatch, capsys):
    class BrokenKaneo(FakeKaneo):
        def list_tasks(self, *arguments):
            raise KeyError("data")

    exit_code, output = run_hook(make_repo(tmp_path), monkeypatch, capsys, BrokenKaneo([], {}))

    assert exit_code == 0
    assert output.startswith("sdlc-llm couldn't read the Kaneo board at session start: KeyError")


def test_hooks_file_runs_the_hook_on_session_start_from_the_plugin_root():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]

    commands = [hook["command"] for entry in hooks["SessionStart"] for hook in entry["hooks"]]

    assert commands == ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"']
