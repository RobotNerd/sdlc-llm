"""Unit/integration tests for `.claude/skills/refine-backlog/scaffold.py` (TASK-025).

`active_days_elapsed`/`underspecified_scan`/`blocked_chain_report`/`apply_reorder` are pure
functions, tested directly against the already-loaded `sync` module (see `conftest.py`) and small
fixtures -- `active_days_elapsed` against a real backdated git history (its whole point is real
commit dates), the rest against hand-built `Artifact` objects. `reorder`/`mark-wont-do`/`resync`
are exercised as real subprocesses against a scratch repo built by `init-project`'s and
`add-task`'s own scaffold scripts.
"""

import importlib.util
import json
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

import sync as sync_mod  # loaded by conftest.py from .tasks/bin/sync

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "refine-backlog"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"
INIT_PROJECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "init-project" / "scaffold.py"
ADD_TASK_SCRIPT = REPO_ROOT / ".claude" / "skills" / "add-task" / "scaffold.py"

_loader = SourceFileLoader("refine_backlog_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("refine_backlog_scaffold", _loader)
refine_backlog_scaffold = importlib.util.module_from_spec(_spec)
sys.modules["refine_backlog_scaffold"] = refine_backlog_scaffold
_loader.exec_module(refine_backlog_scaffold)


def _artifact(task_id, status, body="", **fields):
    return sync_mod.Artifact(
        id=task_id, kind="task", path=Path(f"{task_id}.md"),
        fields={"status": status, "title": task_id, "epic": None, **fields},
        order=list({"status": status, "title": task_id, "epic": None, **fields}.keys()),
        body=body,
    )


# ---------------------------------------------------------------------------
# active_days_elapsed -- real backdated git history
# ---------------------------------------------------------------------------


def _commit(cwd, date_str, content):
    env = os.environ.copy()
    ts = f"{date_str}T12:00:00"
    env["GIT_AUTHOR_DATE"] = ts
    env["GIT_COMMITTER_DATE"] = ts
    (cwd / "file.txt").write_text(content)
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(["git", "commit", "-q", "-m", content], cwd=cwd, env=env, check=True)


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_active_days_elapsed_ignores_a_long_dormant_gap(git_repo):
    # Task "created" 2020-01-01. A couple of active days right after, then a ~200-day
    # dormant gap, then a couple more active days on resume. Real wall-clock span from
    # creation to the last commit is >30 days, but active days elapsed is tiny.
    _commit(git_repo, "2020-01-01", "init")
    _commit(git_repo, "2020-01-02", "day2")
    _commit(git_repo, "2020-08-01", "resume1")
    _commit(git_repo, "2020-08-02", "resume2")

    elapsed = refine_backlog_scaffold.active_days_elapsed(git_repo, "main", "2020-01-01")

    assert elapsed == 3  # 01-02, 08-01, 08-02 -- creation day itself excluded
    assert elapsed <= refine_backlog_scaffold._STALE_THRESHOLD_ACTIVE_DAYS


def test_active_days_elapsed_flags_genuine_sustained_activity(git_repo):
    _commit(git_repo, "2020-01-01", "init")
    from datetime import date, timedelta
    d = date(2020, 1, 2)
    for _ in range(35):
        _commit(git_repo, d.isoformat(), f"day-{d.isoformat()}")
        d += timedelta(days=1)

    elapsed = refine_backlog_scaffold.active_days_elapsed(git_repo, "main", "2020-01-01")

    assert elapsed == 35
    assert elapsed > refine_backlog_scaffold._STALE_THRESHOLD_ACTIVE_DAYS


def test_stale_todo_scan_uses_the_active_days_threshold(git_repo):
    _commit(git_repo, "2020-01-01", "init")
    _commit(git_repo, "2020-01-02", "day2")

    tasks = {"TASK-001": _artifact("TASK-001", "todo", created="2020-01-01")}
    flagged = refine_backlog_scaffold.stale_todo_scan(git_repo, "main", tasks)

    assert flagged == []


def test_stale_todo_scan_skips_non_todo_tasks(git_repo):
    _commit(git_repo, "2020-01-01", "init")
    tasks = {"TASK-001": _artifact("TASK-001", "in-progress", created="2020-01-01")}
    assert refine_backlog_scaffold.stale_todo_scan(git_repo, "main", tasks) == []


# ---------------------------------------------------------------------------
# underspecified_scan
# ---------------------------------------------------------------------------


PLACEHOLDER_BODY = (
    "## Description\n\nSomething.\n\n"
    "## Acceptance criteria\n\n- [ ] {{criterion}}\n\n"
    "## Testing strategy\n\n1. {{step}}\n\n"
    "## Worklog\n\n_(empty)_\n"
)

FILLED_BODY = (
    "## Description\n\nSomething.\n\n"
    "## Acceptance criteria\n\n- [ ] The button turns blue when clicked\n"
    "- [ ] A second concrete criterion\n\n"
    "## Testing strategy\n\n1. Click the button and confirm the color\n"
    "2. Run the unit test suite\n\n"
    "## Worklog\n\n_(empty)_\n"
)

VAGUE_BODY = (
    "## Description\n\nSomething.\n\n"
    "## Acceptance criteria\n\n- [ ]\n\n"
    "## Testing strategy\n\n1.\n\n"
    "## Worklog\n\n_(empty)_\n"
)

# Regression fixture (TASK-025's own read-only pass against the real board caught this):
# a genuinely concrete criterion that merely *mentions* `{{...}}` syntax in prose, describing
# what not to do, must not be mistaken for an actual unfilled template placeholder.
MENTIONS_PLACEHOLDER_SYNTAX_BODY = (
    "## Description\n\nSomething.\n\n"
    "## Acceptance criteria\n\n"
    "- [ ] `config.md` includes `ignored_paths: []` as a fixed value (not a `{{placeholder}}`).\n"
    "- [ ] A second concrete criterion.\n\n"
    "## Testing strategy\n\n1. Run the test suite and confirm it passes\n\n"
    "## Worklog\n\n_(empty)_\n"
)


def test_underspecified_scan_flags_placeholder_body():
    tasks = {"TASK-001": _artifact("TASK-001", "todo", body=PLACEHOLDER_BODY)}
    flagged = refine_backlog_scaffold.underspecified_scan(tasks)
    assert flagged == [{"task_id": "TASK-001", "acceptance_criteria": True, "testing_strategy": True}]


def test_underspecified_scan_does_not_flag_filled_in_body():
    tasks = {"TASK-001": _artifact("TASK-001", "todo", body=FILLED_BODY)}
    assert refine_backlog_scaffold.underspecified_scan(tasks) == []


def test_underspecified_scan_flags_a_lone_vague_line():
    tasks = {"TASK-001": _artifact("TASK-001", "blocked", body=VAGUE_BODY)}
    flagged = refine_backlog_scaffold.underspecified_scan(tasks)
    assert flagged == [{"task_id": "TASK-001", "acceptance_criteria": True, "testing_strategy": True}]


def test_underspecified_scan_does_not_flag_prose_that_mentions_placeholder_syntax():
    tasks = {"TASK-001": _artifact("TASK-001", "todo", body=MENTIONS_PLACEHOLDER_SYNTAX_BODY)}
    assert refine_backlog_scaffold.underspecified_scan(tasks) == []


def test_underspecified_scan_skips_done_and_in_progress_tasks():
    tasks = {
        "TASK-001": _artifact("TASK-001", "done", body=PLACEHOLDER_BODY),
        "TASK-002": _artifact("TASK-002", "in-progress", body=PLACEHOLDER_BODY),
    }
    assert refine_backlog_scaffold.underspecified_scan(tasks) == []


# ---------------------------------------------------------------------------
# blocked_chain_report
# ---------------------------------------------------------------------------


BOARD_WITH_BLOCKS = (
    "# Board\n\n## Epics\n\n_(none)_\n\n## TODO\n\n"
    "- TASK-001 — First\n"
    "- TASK-002 — Second ⛔ blocked_by TASK-001\n"
    "- TASK-003 — Third ⛔ blocked_by TASK-001, TASK-002\n"
    "\n## In Progress\n\n_(none)_\n"
)


def test_blocked_chain_report_lists_each_blocked_line_with_blocker_status():
    tasks = {
        "TASK-001": _artifact("TASK-001", "in-progress"),
        "TASK-002": _artifact("TASK-002", "todo"),
        "TASK-003": _artifact("TASK-003", "todo"),
    }
    report = refine_backlog_scaffold.blocked_chain_report(BOARD_WITH_BLOCKS, tasks, sync_mod)
    assert report == [
        {"task_id": "TASK-002", "blocked_by": [{"id": "TASK-001", "status": "in-progress"}]},
        {
            "task_id": "TASK-003",
            "blocked_by": [
                {"id": "TASK-001", "status": "in-progress"},
                {"id": "TASK-002", "status": "todo"},
            ],
        },
    ]


def test_blocked_chain_report_empty_when_nothing_blocked():
    board = "# Board\n\n## Epics\n\n_(none)_\n\n## TODO\n\n- TASK-001 — First\n\n## In Progress\n\n_(none)_\n"
    tasks = {"TASK-001": _artifact("TASK-001", "todo")}
    assert refine_backlog_scaffold.blocked_chain_report(board, tasks, sync_mod) == []


# ---------------------------------------------------------------------------
# apply_reorder
# ---------------------------------------------------------------------------


BOARD_FOR_REORDER = (
    "# Board\n\n## Epics\n\n_(none)_\n\n## TODO\n\n"
    "- TASK-001 — First\n"
    "- TASK-002 — Second\n"
    "- TASK-003 — Third\n"
    "\n## In Progress\n\n_(none)_\n"
)


def _reorder_tasks():
    return {
        "TASK-001": _artifact("TASK-001", "todo", title="First"),
        "TASK-002": _artifact("TASK-002", "todo", title="Second"),
        "TASK-003": _artifact("TASK-003", "todo", title="Third"),
    }


def test_apply_reorder_applies_the_given_order():
    result = refine_backlog_scaffold.apply_reorder(
        BOARD_FOR_REORDER, ["TASK-003", "TASK-001", "TASK-002"], _reorder_tasks(), sync_mod
    )
    ids = [m.group(1) for m in map(sync_mod._TODO_LINE_RE.match, result.splitlines()) if m]
    assert ids[:3] == ["TASK-003", "TASK-001", "TASK-002"]


@pytest.mark.parametrize(
    "order,match",
    [
        (["TASK-001", "TASK-002"], "missing"),
        (["TASK-001", "TASK-002", "TASK-003", "TASK-999"], "unexpected"),
        (["TASK-001", "TASK-001", "TASK-002", "TASK-003"], "duplicate"),
    ],
    ids=["missing-task", "unexpected-task", "duplicate-task"],
)
def test_apply_reorder_refuses(order, match):
    with pytest.raises(ValueError, match=match):
        refine_backlog_scaffold.apply_reorder(BOARD_FOR_REORDER, order, _reorder_tasks(), sync_mod)


# ---------------------------------------------------------------------------
# Integration: reorder / mark-wont-do / resync against a real scratch repo
# ---------------------------------------------------------------------------


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
    "tdd_enforced": True,
}


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    # Don't rely on git's `init.defaultBranch` -- it's "main" on this machine but not
    # necessarily in CI (that mismatch is exactly what broke this fixture on GitHub
    # Actions: `default_branch: "main"` in config.md, but the actual initial branch
    # there wasn't literally named "main", so `git log main` failed with "unknown
    # revision"). Pin it explicitly, matching `git_repo`'s fixture above.
    _git(["checkout", "-q", "-b", "main"], cwd=tmp_path)
    _git(["config", "user.email", "t@example.com"], cwd=tmp_path)
    _git(["config", "user.name", "Test"], cwd=tmp_path)
    (tmp_path / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=tmp_path)
    _git(["commit", "-q", "-m", "init"], cwd=tmp_path)

    answers_path = tmp_path.parent / "init-answers.json"
    answers_path.write_text(json.dumps(INIT_PROJECT_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(INIT_PROJECT_SCRIPT), "run", str(answers_path)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return tmp_path


def _add_task(cwd, title, priority_mode="end"):
    answers = {"title": title, "type": "feature", "epic": None, "blocked_by": [], "priority_mode": priority_mode}
    answers_path = cwd.parent / "add-task-answers.json"
    answers_path.write_text(json.dumps(answers))
    result = subprocess.run(
        [sys.executable, str(ADD_TASK_SCRIPT), "run", str(answers_path)], cwd=cwd, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def _sync_check(cwd):
    return subprocess.run(
        [sys.executable, str(cwd / ".tasks" / "bin" / "sync"), "check"], cwd=cwd, capture_output=True, text=True
    )


def test_resync_reports_clean_repo(repo):
    result = subprocess.run([sys.executable, str(SCRIPT_PATH), "resync"], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_report_flags_add_tasks_unfilled_body_placeholders(repo):
    # `add-task run` (TASK-022) deliberately leaves the body's Acceptance criteria/Testing
    # strategy sections as `{{placeholder}}`s for the LLM's own step 2b -- report should
    # flag exactly that, real end to end, until that step happens.
    _add_task(repo, "First task")
    result = subprocess.run([sys.executable, str(SCRIPT_PATH), "report"], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["blocked_chain"] == []
    assert output["stale_todo"] == []
    assert output["underspecified"] == [
        {"task_id": "TASK-001", "acceptance_criteria": True, "testing_strategy": True}
    ]


def test_mark_wont_do_sets_status_and_archives(repo):
    _add_task(repo, "First task")
    answers_path = repo.parent / "wont-do-answers.json"
    answers_path.write_text(json.dumps({"task_id": "TASK-001"}))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "mark-wont-do", str(answers_path)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    assert (repo / ".tasks" / "archive" / "TASK-001-first-task.md").exists()
    assert _sync_check(repo).returncode == 0


def test_reorder_subcommand_applies_and_stays_clean(repo):
    _add_task(repo, "First task")
    _add_task(repo, "Second task")
    _add_task(repo, "Third task")
    answers_path = repo.parent / "reorder-answers.json"
    answers_path.write_text(json.dumps({"new_order": ["TASK-003", "TASK-001", "TASK-002"]}))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "reorder", str(answers_path)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    board_text = (repo / ".tasks" / "BOARD.md").read_text()
    ids = [m.group(1) for m in map(sync_mod._TODO_LINE_RE.match, board_text.splitlines()) if m]
    assert ids[:3] == ["TASK-003", "TASK-001", "TASK-002"]
    assert _sync_check(repo).returncode == 0


def test_reorder_subcommand_refuses_bad_order(repo):
    _add_task(repo, "First task")
    answers_path = repo.parent / "reorder-answers.json"
    answers_path.write_text(json.dumps({"new_order": ["TASK-999"]}))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "reorder", str(answers_path)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode != 0
    assert "TASK-999" not in (repo / ".tasks" / "BOARD.md").read_text()
