"""A malformed `TASK-*.md`/`EPIC-*.md`/`SPEC-*.md` (TASK-072) must surface as a one-line error naming
the file and a non-zero exit -- never a Python traceback -- from `sync` itself and from every skill
script that calls `discover()` directly. The bad file must still fail every entry point (this is a
presentation fix, never a "skip the bad file" one).

Everything runs as a real subprocess against a scratch git repo scaffolded by `init-project`, with the
malformed file committed so unrelated guards (e.g. `start`'s dirty-tree check) can't mask the behavior
under test.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / ".claude" / "skills"
INIT_PROJECT_SCRIPT = SKILLS / "init-project" / "scaffold.py"
IMPLEMENT_TASK = SKILLS / "implement-task" / "scaffold.py"
BATCH_SELECT = SKILLS / "implement-task" / "batch_select.py"
ADD_TASK = SKILLS / "add-task" / "scaffold.py"
REFINE_BACKLOG = SKILLS / "refine-backlog" / "scaffold.py"

INIT_PROJECT_ANSWERS = {
    "test_command": "pytest", "lint_command": None, "format_command": None,
    "docs_paths": ["README.md"], "default_branch": "main", "branch_prefix": "task-",
    "remote": "origin", "rebase_before_pr": True, "merge_strategy": "squash",
    "delete_branch_after_merge": True, "ci_checks": [], "archive_done": True, "tdd_enforced": True,
}

MALFORMED_SHAPES = {
    "no-frontmatter": "just some notes, no frontmatter block\n",
    "unclosed-block": "---\nid: TASK-998\ntitle: half written\n",
    "missing-id": "---\ntitle: no id here\n---\nbody\n",
}


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def scratch(tmp_path):
    """A committed `init-project`-scaffolded repo with a clean tree."""
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q", "-b", "main"], cwd=work)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)
    (work / "README.md").write_text("# scratch\n")
    answers = tmp_path / "init-answers.json"
    answers.write_text(json.dumps(INIT_PROJECT_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(INIT_PROJECT_SCRIPT), "run", str(answers)],
        cwd=work, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "scaffold"], cwd=work)
    return work


def _plant(scratch, relpath="TASK-999-stray.md", shape="no-frontmatter"):
    path = scratch / ".tasks" / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MALFORMED_SHAPES[shape])
    _git(["add", "-A"], cwd=scratch)
    _git(["commit", "-q", "-m", "add malformed file"], cwd=scratch)
    return path


def _assert_clean_failure(result, offending, *, code=None):
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined, combined
    assert result.returncode != 0, combined  # never silently succeeds past a bad file
    if code is not None:
        assert result.returncode == code, combined
    assert offending.name in result.stderr, result.stderr
    assert len(result.stderr.strip().splitlines()) == 1, result.stderr  # one line, not a dump


# ---------------------------------------------------------------------------
# `.tasks/bin/sync` itself
# ---------------------------------------------------------------------------


def _run_sync(scratch, *args):
    return subprocess.run(
        [sys.executable, str(scratch / ".tasks" / "bin" / "sync"), *args],
        cwd=scratch, capture_output=True, text=True,
    )


@pytest.mark.parametrize("shape", sorted(MALFORMED_SHAPES))
@pytest.mark.parametrize("args,code", [((), 2), (("check",), 1), (("archive",), 2)])
def test_sync_reports_a_malformed_file_without_a_traceback(scratch, shape, args, code):
    bad = _plant(scratch, shape=shape)

    _assert_clean_failure(_run_sync(scratch, *args), bad, code=code)


@pytest.mark.parametrize("relpath", ["EPIC-999-stray.md", "specs/SPEC-999-stray.md", "archive/TASK-999-stray.md"])
def test_sync_check_reports_a_malformed_epic_spec_or_archived_file(scratch, relpath):
    bad = _plant(scratch, relpath)

    _assert_clean_failure(_run_sync(scratch, "check"), bad, code=1)


def test_sync_check_is_still_clean_on_a_well_formed_tasks_dir(scratch):
    result = _run_sync(scratch, "check")

    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# skill scripts that call `discover()` directly
# ---------------------------------------------------------------------------

_TASK_ANSWERS = {"task_id": "TASK-001", "bookkeeping_commit_message": "x"}
_WRAP_UP_ANSWERS = {
    "task_id": "TASK-001", "paths": [], "commit_message": "x", "pr_title": "x", "pr_body": "x",
    "bookkeeping_commit_message": "x",
}
_ADD_TASK_ANSWERS = {"title": "New thing", "type": "bug", "epic": None, "blocked_by": [], "priority_mode": "end"}

SCRIPT_CASES = [
    (IMPLEMENT_TASK, "resume-state", None),
    (IMPLEMENT_TASK, "start", {"task_id": "TASK-001"}),
    (IMPLEMENT_TASK, "wrap-up", _WRAP_UP_ANSWERS),
    (IMPLEMENT_TASK, "finish-merge", _TASK_ANSWERS),
    (IMPLEMENT_TASK, "bail-out", {"task_id": "TASK-001", "status": "todo"}),
    (BATCH_SELECT, "select", {"mode": "list", "tasks": ["TASK-001"]}),
    (ADD_TASK, "list-open-epics", None),
    (ADD_TASK, "run", _ADD_TASK_ANSWERS),
    (REFINE_BACKLOG, "report", None),
    (REFINE_BACKLOG, "resync", None),
    (REFINE_BACKLOG, "mark-wont-do", {"task_id": "TASK-001"}),
    (REFINE_BACKLOG, "reorder", {"new_order": []}),
]


@pytest.mark.parametrize("script,command,answers", SCRIPT_CASES, ids=[f"{s.parent.name}:{c}" for s, c, _ in SCRIPT_CASES])
def test_skill_script_reports_a_malformed_file_without_a_traceback(scratch, tmp_path, script, command, answers):
    bad = _plant(scratch)
    argv = [sys.executable, str(script), command]
    if answers is not None:
        answers_path = tmp_path / "answers.json"
        answers_path.write_text(json.dumps(answers))
        argv.append(str(answers_path))

    result = subprocess.run(argv, cwd=scratch, capture_output=True, text=True)

    _assert_clean_failure(result, bad)
