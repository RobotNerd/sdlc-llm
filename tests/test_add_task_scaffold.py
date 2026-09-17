"""Unit/integration tests for `.claude/skills/add-task/scaffold.py` (TASK-022).

`list_open_epics`/`render_task_file`/`reposition_todo_line` are pure functions, tested directly
against the already-loaded `sync` module (see `conftest.py`) and small ad hoc fixtures -- no full
repo needed. The `run`/`list-open-epics` subcommands are exercised as real subprocesses against a
scratch repo built by `init-project`'s own (already-tested) `scaffold.py`, since their whole job is
filesystem + `sync` side effects, not pure computation.
"""

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

import sync as sync_mod  # loaded by conftest.py from .tasks/bin/sync

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "add-task"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"
INIT_PROJECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "init-project" / "scaffold.py"
TASK_TEMPLATE_TEXT = (REPO_ROOT / ".tasks" / "templates" / "task.md").read_text()

_loader = SourceFileLoader("add_task_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("add_task_scaffold", _loader)
add_task_scaffold = importlib.util.module_from_spec(_spec)
sys.modules["add_task_scaffold"] = add_task_scaffold
_loader.exec_module(add_task_scaffold)


INIT_PROJECT_ANSWERS = {
    "test_command": "pytest",
    "lint_command": None,
    "format_command": None,
    "docs_paths": ["README.md"],
    "default_branch": "main",
    "branch_prefix": "task-",
    "remote": "origin",
    "rebase_before_pr": True,
    "merge_strategy": "squash",
    "delete_branch_after_merge": True,
    "ci_checks": [],
    "archive_done": True,
}


def _init_git_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("# scratch\n")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


@pytest.fixture
def repo(tmp_path):
    """A real git repo with a freshly-scaffolded `.tasks/` (via `init-project`'s own
    `scaffold.py`), so `add-task`'s script has real config/templates/`sync` to run
    against -- the same dogfooding chain the real skills use.
    """
    _init_git_repo(tmp_path)
    answers_path = tmp_path / "init-answers.json"
    answers_path.write_text(json.dumps(INIT_PROJECT_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(INIT_PROJECT_SCRIPT), "run", str(answers_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return tmp_path


def _run_add_task(cwd, answers: dict):
    answers_path = cwd / "add-task-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "run", str(answers_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _list_open_epics(cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "list-open-epics"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _sync_check(cwd):
    return subprocess.run(
        [sys.executable, str(cwd / ".tasks" / "bin" / "sync"), "check"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _todo_ids(board_text: str) -> list[str]:
    start = board_text.index(sync_mod._TODO_HEADING) + len(sync_mod._TODO_HEADING)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    return [
        m.group(1)
        for line in board_text[start:end].splitlines()
        if (m := sync_mod._TODO_LINE_RE.match(line))
    ]


BASE_ANSWERS = {
    "title": "Add a widget",
    "type": "feature",
    "epic": None,
    "blocked_by": [],
    "priority_mode": "end",
}


# ---------------------------------------------------------------------------
# Pure functions: missing_keys / slugify
# ---------------------------------------------------------------------------


def test_add_task_missing_keys_empty_when_all_present():
    assert add_task_scaffold.missing_keys(BASE_ANSWERS) == []


def test_add_task_missing_keys_reports_absent_ones():
    incomplete = dict(BASE_ANSWERS)
    del incomplete["title"]
    assert add_task_scaffold.missing_keys(incomplete) == ["title"]


def test_missing_keys_requires_priority_after_when_mode_is_after():
    answers = {**BASE_ANSWERS, "priority_mode": "after"}
    assert add_task_scaffold.missing_keys(answers) == ["priority_after"]


def test_add_task_slugify_normalizes_title():
    assert add_task_scaffold.slugify("Add a Widget: v2!") == "add-a-widget-v2"


def test_add_task_slugify_raises_on_unslugifiable_title():
    with pytest.raises(ValueError):
        add_task_scaffold.slugify("!!!")


# ---------------------------------------------------------------------------
# list_open_epics -- direct function test against a mixed-status fixture
# ---------------------------------------------------------------------------


def _write_epic(tasks_root, epic_id, status):
    (tasks_root / f"{epic_id}-fixture.md").write_text(
        f"---\nid: {epic_id}\ntitle: Fixture {epic_id}\nspec: null\nstatus: {status}\n"
        f"created: 2026-01-01\n---\n\n# {epic_id}: Fixture\n"
    )


def test_list_open_epics_returns_only_non_archived_statuses(tmp_path):
    (tmp_path / "archive").mkdir()
    _write_epic(tmp_path, "EPIC-001", "todo")
    _write_epic(tmp_path, "EPIC-002", "in-progress")
    _write_epic(tmp_path, "EPIC-003", "done")
    _write_epic(tmp_path, "EPIC-004", "wont-do")

    open_epics = add_task_scaffold.list_open_epics(tmp_path, sync_mod)

    assert open_epics == [
        {"id": "EPIC-001", "title": "Fixture EPIC-001"},
        {"id": "EPIC-002", "title": "Fixture EPIC-002"},
    ]


# ---------------------------------------------------------------------------
# render_task_file -- step 2a's frontmatter/heading templating
# ---------------------------------------------------------------------------


def test_render_task_file_fills_frontmatter_and_both_title_occurrences():
    text = add_task_scaffold.render_task_file(
        TASK_TEMPLATE_TEXT,
        task_id="TASK-099",
        title="Add a widget",
        type_="feature",
        epic="EPIC-001",
        created="2026-09-14",
        branch="task-099-add-a-widget",
        blocked_by=["TASK-001", "TASK-002"],
        sync_mod=sync_mod,
    )

    assert "{{" not in text.split("\n\n", 1)[0]  # frontmatter block has no leftover placeholders
    assert 'id: TASK-099' in text
    assert 'title: "Add a widget"' in text
    assert "type: feature" in text
    assert "epic: EPIC-001" in text
    assert "created: 2026-09-14" in text
    assert "branch: task-099-add-a-widget" in text
    assert "blocked_by: [TASK-001, TASK-002]" in text
    assert "status: todo" in text
    assert "pr: null" in text
    assert "merge_commit: null" in text
    assert "blocks: []" in text
    assert "# TASK-099: Add a widget" in text


def test_render_task_file_leaves_body_sections_as_placeholders():
    text = add_task_scaffold.render_task_file(
        TASK_TEMPLATE_TEXT,
        task_id="TASK-099",
        title="Add a widget",
        type_="feature",
        epic=None,
        created="2026-09-14",
        branch="task-099-add-a-widget",
        blocked_by=[],
        sync_mod=sync_mod,
    )

    assert "{{description}}" in text
    assert "{{criterion}}" in text
    assert "{{step}}" in text
    assert "{{note}}" in text


def test_render_task_file_renders_null_epic():
    text = add_task_scaffold.render_task_file(
        TASK_TEMPLATE_TEXT,
        task_id="TASK-099",
        title="Add a widget",
        type_="feature",
        epic=None,
        created="2026-09-14",
        branch="task-099-add-a-widget",
        blocked_by=[],
        sync_mod=sync_mod,
    )
    assert "epic: null" in text


# ---------------------------------------------------------------------------
# reposition_todo_line -- TODO placement logic
# ---------------------------------------------------------------------------


BOARD_TEXT = (
    "# Board\n\n## Epics\n\n_(none)_\n\n## TODO\n\n"
    "- TASK-001 — First\n"
    "- TASK-002 — Second\n"
    "- TASK-003 — Third\n"
    "\n## In Progress\n\n_(none)_\n"
)


def test_reposition_to_top():
    result = add_task_scaffold.reposition_todo_line(BOARD_TEXT, "TASK-003", "top", None, sync_mod)
    ids = [m.group(1) for m in map(sync_mod._TODO_LINE_RE.match, result.splitlines()) if m]
    assert ids[:3] == ["TASK-003", "TASK-001", "TASK-002"]


def test_reposition_after_named_task():
    result = add_task_scaffold.reposition_todo_line(
        BOARD_TEXT, "TASK-003", "after", "TASK-001", sync_mod
    )
    ids = [m.group(1) for m in map(sync_mod._TODO_LINE_RE.match, result.splitlines()) if m]
    assert ids[:3] == ["TASK-001", "TASK-003", "TASK-002"]


def test_reposition_end_is_a_noop_when_already_last():
    result = add_task_scaffold.reposition_todo_line(BOARD_TEXT, "TASK-003", "end", None, sync_mod)
    assert result == BOARD_TEXT


@pytest.mark.parametrize(
    "task_id,mode,after",
    [("TASK-404", "top", None), ("TASK-003", "after", "TASK-404")],
    ids=["task-not-found", "after-target-not-found"],
)
def test_reposition_raises(task_id, mode, after):
    with pytest.raises(ValueError):
        add_task_scaffold.reposition_todo_line(BOARD_TEXT, task_id, mode, after, sync_mod)


# ---------------------------------------------------------------------------
# `run` subcommand -- against a real scaffolded scratch repo
# ---------------------------------------------------------------------------


def test_run_refuses_if_missing_required_answer(repo):
    incomplete = dict(BASE_ANSWERS)
    del incomplete["title"]
    result = _run_add_task(repo, incomplete)
    assert result.returncode != 0
    assert "title" in result.stderr
    assert list((repo / ".tasks").glob("TASK-*.md")) == []


@pytest.mark.parametrize(
    "overrides,needle",
    [
        ({"type": "not-a-type"}, "not-a-type"),
        ({"epic": "EPIC-999"}, "EPIC-999"),
        ({"blocked_by": ["TASK-999"]}, "TASK-999"),
        ({"priority_mode": "sideways"}, "sideways"),
        ({"priority_mode": "after"}, "priority_after"),
    ],
    ids=["unknown-type", "unknown-epic", "unknown-blocked-by", "unknown-priority-mode", "missing-priority-after"],
)
def test_run_refuses_on_bad_answers(repo, overrides, needle):
    result = _run_add_task(repo, {**BASE_ANSWERS, **overrides})
    assert result.returncode != 0
    assert needle in result.stderr


def test_run_appends_at_end_and_sync_check_stays_clean(repo):
    result = _run_add_task(repo, {**BASE_ANSWERS, "title": "First task"})
    assert result.returncode == 0, result.stderr

    board_text = (repo / ".tasks" / "BOARD.md").read_text()
    assert _todo_ids(board_text) == ["TASK-001"]
    assert (repo / ".tasks" / "TASK-001-first-task.md").exists()
    assert _sync_check(repo).returncode == 0


def test_run_places_at_top_and_sync_check_stays_clean(repo):
    first = _run_add_task(repo, {**BASE_ANSWERS, "title": "First task"})
    assert first.returncode == 0, first.stderr

    second = _run_add_task(
        repo, {**BASE_ANSWERS, "title": "Second task", "priority_mode": "top"}
    )
    assert second.returncode == 0, second.stderr

    board_text = (repo / ".tasks" / "BOARD.md").read_text()
    assert _todo_ids(board_text) == ["TASK-002", "TASK-001"]
    assert _sync_check(repo).returncode == 0


def test_run_places_after_named_task_and_sync_check_stays_clean(repo):
    first = _run_add_task(repo, {**BASE_ANSWERS, "title": "First task"})
    assert first.returncode == 0, first.stderr
    second = _run_add_task(repo, {**BASE_ANSWERS, "title": "Second task"})
    assert second.returncode == 0, second.stderr

    third = _run_add_task(
        repo,
        {
            **BASE_ANSWERS,
            "title": "Third task",
            "priority_mode": "after",
            "priority_after": "TASK-001",
        },
    )
    assert third.returncode == 0, third.stderr

    board_text = (repo / ".tasks" / "BOARD.md").read_text()
    assert _todo_ids(board_text) == ["TASK-001", "TASK-003", "TASK-002"]
    assert _sync_check(repo).returncode == 0


def test_run_sets_blocked_by_and_epic(repo):
    (repo / ".tasks" / "EPIC-001-fixture.md").write_text(
        "---\nid: EPIC-001\ntitle: Fixture\nspec: null\nstatus: todo\n"
        "created: 2026-01-01\n---\n\n# EPIC-001: Fixture\n\n"
        "<!-- BEGIN:children (generated by sync — do not edit) -->\n_(none)_\n"
        "<!-- END:children -->\n"
    )
    first = _run_add_task(repo, {**BASE_ANSWERS, "title": "First task"})
    assert first.returncode == 0, first.stderr

    second = _run_add_task(
        repo,
        {
            **BASE_ANSWERS,
            "title": "Second task",
            "epic": "EPIC-001",
            "blocked_by": ["TASK-001"],
        },
    )
    assert second.returncode == 0, second.stderr

    task_text = (repo / ".tasks" / "TASK-002-second-task.md").read_text()
    assert "epic: EPIC-001" in task_text
    assert "blocked_by: [TASK-001]" in task_text
    assert _sync_check(repo).returncode == 0


def test_list_open_epics_subcommand_on_fresh_repo(repo):
    result = _list_open_epics(repo)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == []


def test_list_open_epics_subcommand_excludes_done_and_wont_do(repo):
    _write_epic(repo / ".tasks", "EPIC-001", "todo")
    _write_epic(repo / ".tasks", "EPIC-002", "done")
    result = _list_open_epics(repo)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [{"id": "EPIC-001", "title": "Fixture EPIC-001"}]
