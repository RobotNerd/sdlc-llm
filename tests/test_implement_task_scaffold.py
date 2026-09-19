"""Unit/integration tests for `.claude/skills/implement-task/scaffold.py` (TASK-024/046).

The four pure functions AC7 calls out (`resume_phase`, `compute_branch_name`/`slugify`,
`decide_push_args`, `pick_top_unblocked`) are tested directly against the already-loaded `sync`
module (see `conftest.py`) and small fixtures -- no real git/gh needed. `cmd_start`/`cmd_bail_out`/
`cmd_resume_state` are exercised as real subprocesses against a scratch repo with a genuine bare
"origin" remote (built by `init-project`'s and `add-task`'s own scaffold scripts), since their job
is real git side effects. `wrap-up` is exercised the same way, with a fake `gh` stub on `PATH`
(TASK-046) standing in for `gh pr create`/`gh pr checks` -- deterministic, no network, but still a
real `git` subprocess end to end. `finish-merge`'s `gh pr view`-driven branching isn't covered this
way (out of TASK-046's scope) and is proven instead by a live dry run against a real scratch
branch/PR, documented in TASK-024's own Worklog -- same precedent TASK-016 itself set.
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
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "implement-task"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"
INIT_PROJECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "init-project" / "scaffold.py"
ADD_TASK_SCRIPT = REPO_ROOT / ".claude" / "skills" / "add-task" / "scaffold.py"

_loader = SourceFileLoader("implement_task_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("implement_task_scaffold", _loader)
implement_task_scaffold = importlib.util.module_from_spec(_spec)
sys.modules["implement_task_scaffold"] = implement_task_scaffold
_loader.exec_module(implement_task_scaffold)


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


# ---------------------------------------------------------------------------
# resume_phase -- every row of SPEC-001 §0's table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "in_flight,working_tree_dirty,gh_pr_state,expected",
    [
        (None, False, None, {"phase": "phase1"}),
        (
            {"id": "TASK-001", "status": "in-progress", "pr": None, "merge_commit": None, "branch_exists": False},
            False, None, {"phase": "phase1"},
        ),
        (
            {"id": "TASK-001", "status": "in-progress", "pr": None, "merge_commit": None, "branch_exists": True},
            True, None, {"phase": "phase2", "task_id": "TASK-001"},
        ),
        (
            {"id": "TASK-001", "status": "in-progress", "pr": None, "merge_commit": None, "branch_exists": True},
            False, None, {"phase": "phase3", "task_id": "TASK-001"},
        ),
        (
            {
                "id": "TASK-001", "status": "in-progress", "pr": "https://x/1",
                "merge_commit": None, "branch_exists": True,
            },
            False, None, "ambiguous",
        ),
        (
            {"id": "TASK-001", "status": "in-review", "pr": "https://x/1", "merge_commit": None, "branch_exists": True},
            False, "OPEN", {"phase": "phase4_open", "task_id": "TASK-001"},
        ),
        (
            {"id": "TASK-001", "status": "in-review", "pr": "https://x/1", "merge_commit": None, "branch_exists": True},
            False, "MERGED", {"phase": "phase4_merged", "task_id": "TASK-001"},
        ),
        (
            {
                "id": "TASK-001", "status": "in-review", "pr": "https://x/1",
                "merge_commit": "abc123", "branch_exists": True,
            },
            False, "MERGED", "ambiguous",
        ),
        (
            {"id": "TASK-001", "status": "in-review", "pr": "https://x/1", "merge_commit": None, "branch_exists": True},
            False, "CLOSED", {"phase": "phase4_closed_not_merged", "task_id": "TASK-001"},
        ),
        (
            {"id": "TASK-001", "status": "in-review", "pr": None, "merge_commit": None, "branch_exists": True},
            False, None, "ambiguous",
        ),
        (
            {"id": "TASK-001", "status": "blocked", "pr": None, "merge_commit": None, "branch_exists": True},
            False, None, "ambiguous",
        ),
    ],
    ids=[
        "no-in-flight-task", "in-flight-branch-gone", "in-progress-dirty", "in-progress-clean",
        "in-progress-with-pr", "in-review-open", "in-review-merged-not-recorded",
        "in-review-merged-already-recorded", "in-review-closed-not-merged", "in-review-no-pr",
        "unexpected-status",
    ],
)
def test_resume_phase(in_flight, working_tree_dirty, gh_pr_state, expected):
    result = implement_task_scaffold.resume_phase(
        in_flight=in_flight, working_tree_dirty=working_tree_dirty, gh_pr_state=gh_pr_state
    )
    if expected == "ambiguous":
        assert result["phase"] == "ambiguous"
    else:
        assert result == expected


# ---------------------------------------------------------------------------
# compute_branch_name / slugify
# ---------------------------------------------------------------------------


def test_compute_branch_name_formats():
    assert implement_task_scaffold.compute_branch_name("task-", "TASK-024", "my-slug") == "task-024-my-slug"


def test_implement_task_slugify_normalizes_title():
    assert implement_task_scaffold.slugify("Add a Widget: v2!") == "add-a-widget-v2"


def test_implement_task_slugify_raises_on_unslugifiable_title():
    with pytest.raises(ValueError):
        implement_task_scaffold.slugify("!!!")


def test_compute_branch_name_round_trips_every_real_task_branch():
    """Real task slugs in this repo are short, hand-chosen summaries, not a mechanical
    `slugify(full title)` -- see `compute_branch_name`'s docstring. What's actually
    testable against real data is the `<prefix><number>-<slug>` join/format logic
    itself: split every real archived+active task's own `branch` into its slug
    suffix, feed that back in, and confirm the formatting reproduces it exactly.
    """
    config = sync_mod.load_config(REPO_ROOT / ".tasks")
    branch_prefix = config["branch_prefix"]
    artifacts = sync_mod.discover(REPO_ROOT / ".tasks")
    tasks = [a for a in artifacts.values() if a.kind == "task" and a.fields.get("branch")]
    assert len(tasks) > 10  # sanity: this repo has plenty of real tasks to check against

    for task in tasks:
        branch = task.fields["branch"]
        number = task.id.split("-", 1)[1]
        prefix_and_number = f"{branch_prefix}{number}-"
        assert branch.startswith(prefix_and_number), f"{task.id}: {branch!r}"
        slug = branch[len(prefix_and_number):]
        assert implement_task_scaffold.compute_branch_name(branch_prefix, task.id, slug) == branch


# ---------------------------------------------------------------------------
# decide_push_args
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "force,expected",
    [
        (False, ["push", "origin", "task-001-x"]),
        (True, ["push", "--force-with-lease", "origin", "task-001-x"]),
    ],
    ids=["plain", "force-with-lease"],
)
def test_decide_push_args(force, expected):
    args = implement_task_scaffold.decide_push_args(
        current_branch="task-001-x", task_branch="task-001-x", default_branch="main", remote="origin", force=force
    )
    assert args == expected


@pytest.mark.parametrize(
    "current_branch,task_branch",
    [("main", "task-001-x"), ("main", "main")],
    ids=["wrong-branch", "default-branch"],
)
def test_decide_push_args_refuses(current_branch, task_branch):
    with pytest.raises(ValueError):
        implement_task_scaffold.decide_push_args(
            current_branch=current_branch, task_branch=task_branch,
            default_branch="main", remote="origin", force=False,
        )


# ---------------------------------------------------------------------------
# pick_top_unblocked
# ---------------------------------------------------------------------------


def _board_with_todo(todo_lines: list[str]) -> str:
    body = "\n".join(todo_lines)
    return f"# Board\n\n## Epics\n\n_(none)_\n\n## TODO\n\n{body}\n\n## In Progress\n\n_(none)_\n"


def test_pick_top_unblocked_takes_first_unblocked():
    board = _board_with_todo([
        "- TASK-001 — First",
        "- TASK-002 — Second",
    ])
    result = implement_task_scaffold.pick_top_unblocked(board, sync_mod)
    assert result == {"task_id": "TASK-001", "skipped": []}


def test_pick_top_unblocked_skips_blocked_lines():
    board = _board_with_todo([
        "- TASK-001 — First ⛔ blocked_by TASK-000",
        "- TASK-002 — Second",
        "- TASK-003 — Third",
    ])
    result = implement_task_scaffold.pick_top_unblocked(board, sync_mod)
    assert result["task_id"] == "TASK-002"
    assert result["skipped"] == [{"id": "TASK-001", "reason": "blocked_by TASK-000"}]


def test_pick_top_unblocked_all_blocked_returns_none():
    board = _board_with_todo([
        "- TASK-001 — First ⛔ blocked_by TASK-000",
        "- TASK-002 — Second ⛔ blocked_by TASK-000",
    ])
    result = implement_task_scaffold.pick_top_unblocked(board, sync_mod)
    assert result["task_id"] is None
    assert len(result["skipped"]) == 2


def test_pick_top_unblocked_empty_todo_returns_none():
    board = _board_with_todo([])
    result = implement_task_scaffold.pick_top_unblocked(board, sync_mod)
    assert result == {"task_id": None, "skipped": []}


# ---------------------------------------------------------------------------
# stop_required_for_phase1 (TASK-041): the announce-not-block decision for a
# batch task's phase 1 -- pure function of the one flag that decides it.
# ---------------------------------------------------------------------------


def test_stop_required_for_phase1_true_outside_batch_mode():
    assert implement_task_scaffold.stop_required_for_phase1(batch_mode=False) is True


def test_stop_required_for_phase1_false_in_batch_mode():
    assert implement_task_scaffold.stop_required_for_phase1(batch_mode=True) is False


# ---------------------------------------------------------------------------
# record_outcome / render_outcome_table (TASK-041): the batch loop's
# end-of-run outcome accumulation -- pure functions, no I/O.
# ---------------------------------------------------------------------------


def test_record_outcome_appends_without_mutating_input():
    outcomes = [{"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc123"}]
    entry = {"task_id": "TASK-002", "title": "Second", "status": "done", "link": "def456"}

    result = implement_task_scaffold.record_outcome(outcomes, entry)

    assert result == [
        {"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc123"},
        {"task_id": "TASK-002", "title": "Second", "status": "done", "link": "def456"},
    ]
    assert outcomes == [{"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc123"}]


def test_record_outcome_onto_empty_list():
    entry = {"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc123"}
    assert implement_task_scaffold.record_outcome([], entry) == [entry]


@pytest.mark.parametrize("missing_key", ["task_id", "title", "status"])
def test_record_outcome_raises_on_missing_required_key(missing_key):
    entry = {"task_id": "TASK-001", "title": "First", "status": "done", "link": None}
    del entry[missing_key]
    with pytest.raises(ValueError, match=missing_key):
        implement_task_scaffold.record_outcome([], entry)


def test_record_outcome_allows_link_to_be_none():
    entry = {"task_id": "TASK-001", "title": "First", "status": "todo", "link": None}
    assert implement_task_scaffold.record_outcome([], entry) == [entry]


def test_render_outcome_table_empty_is_header_only():
    table = implement_task_scaffold.render_outcome_table([])
    lines = table.splitlines()
    assert lines == ["| Task | Title | Status | PR/Merge |", "|---|---|---|---|"]


def test_render_outcome_table_renders_every_row_in_order():
    outcomes = [
        {"task_id": "TASK-001", "title": "First", "status": "done", "link": "https://x/pr/1"},
        {"task_id": "TASK-002", "title": "Second", "status": "in-review", "link": None},
    ]
    table = implement_task_scaffold.render_outcome_table(outcomes)
    lines = table.splitlines()
    assert lines[0] == "| Task | Title | Status | PR/Merge |"
    assert lines[2] == "| TASK-001 | First | done | https://x/pr/1 |"
    assert lines[3] == "| TASK-002 | Second | in-review | — |"


# ---------------------------------------------------------------------------
# Integration: cmd_start / cmd_bail_out / cmd_resume_state against a real
# scratch repo with a genuine bare "origin" remote
# ---------------------------------------------------------------------------


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def _set_ignored_paths(cwd, paths):
    """Rewrite the scaffolded `ignored_paths: []` line in `.tasks/config.md` -- not committed,
    caller's job (matches how other tests hand-edit frontmatter, e.g. `blocked_by`).
    """
    config_path = cwd / ".tasks" / "config.md"
    text = config_path.read_text().replace("ignored_paths: []", f"ignored_paths: [{', '.join(paths)}]")
    config_path.write_text(text)


def test_dirty_files_excludes_given_ignore_paths(tmp_path):
    _git(["init", "-q"], cwd=tmp_path)
    _git(["config", "user.email", "t@example.com"], cwd=tmp_path)
    _git(["config", "user.name", "Test"], cwd=tmp_path)
    (tmp_path / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=tmp_path)
    _git(["commit", "-q", "-m", "init"], cwd=tmp_path)

    (tmp_path / ".tmp").mkdir()
    (tmp_path / ".tmp" / "prompts.md").write_text("wip\n")
    (tmp_path / "other.txt").write_text("also dirty\n")

    all_dirty = implement_task_scaffold.dirty_files(tmp_path)
    assert set(all_dirty) == {".tmp/prompts.md", "other.txt"}

    ignoring_prompts = implement_task_scaffold.dirty_files(tmp_path, ignore=(".tmp/prompts.md",))
    assert ignoring_prompts == ["other.txt"]


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)

    work = tmp_path / "work"
    _git(["clone", "-q", str(origin), str(work)], cwd=tmp_path)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)
    (work / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "init"], cwd=work)
    _git(["branch", "-M", "main"], cwd=work)
    _git(["push", "-u", "origin", "main"], cwd=work)

    answers_path = work / "init-answers.json"
    answers_path.write_text(json.dumps(INIT_PROJECT_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(INIT_PROJECT_SCRIPT), "run", str(answers_path)],
        cwd=work, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "scaffold .tasks"], cwd=work)
    _git(["push"], cwd=work)
    return work


def _add_task(cwd, title, priority_mode="end", priority_after=None, blocked_by=None):
    answers = {
        "title": title,
        "type": "feature",
        "epic": None,
        "blocked_by": blocked_by or [],
        "priority_mode": priority_mode,
    }
    if priority_after:
        answers["priority_after"] = priority_after
    answers_path = cwd.parent / "add-task-answers.json"
    answers_path.write_text(json.dumps(answers))
    result = subprocess.run(
        [sys.executable, str(ADD_TASK_SCRIPT), "run", str(answers_path)],
        cwd=cwd, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def _push_tasks(cwd):
    _git(["add", "-A"], cwd=cwd)
    _git(["commit", "-q", "-m", "add tasks"], cwd=cwd)
    _git(["push"], cwd=cwd)


def _run_start(cwd, task_id=None, batch_mode=None):
    answers = {"task_id": task_id}
    if batch_mode is not None:
        answers["batch_mode"] = batch_mode
    answers_path = cwd.parent / "start-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "start", str(answers_path)], cwd=cwd, capture_output=True, text=True
    )


def _sync_check(cwd):
    return subprocess.run(
        [sys.executable, str(cwd / ".tasks" / "bin" / "sync"), "check"], cwd=cwd, capture_output=True, text=True
    )


FAKE_PR_URL = "https://example.invalid/pr/1"


@pytest.fixture
def fake_gh(tmp_path_factory):
    """A `gh` stub on its own directory: `pr create` prints a fixed fake PR URL (deterministic,
    no network); `pr checks` reports nothing configured (a plausible real response, and `wrap-up`
    must not fail on it regardless). Prepend this directory to `PATH` to use it in a subprocess.
    """
    bin_dir = tmp_path_factory.mktemp("fake-gh-bin")
    gh_path = bin_dir / "gh"
    gh_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['pr', 'create']:\n"
        f"    print({FAKE_PR_URL!r})\n"
        "    sys.exit(0)\n"
        "if args[:2] == ['pr', 'checks']:\n"
        "    print('no checks configured')\n"
        "    sys.exit(1)\n"
        "sys.exit(0)\n"
    )
    gh_path.chmod(0o755)
    return bin_dir


def _run_wrap_up(cwd, answers, fake_gh):
    answers_path = cwd.parent / "wrap-up-answers.json"
    answers_path.write_text(json.dumps(answers))
    env = os.environ.copy()
    env["PATH"] = f"{fake_gh}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "wrap-up", str(answers_path)],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def test_wrap_up_commits_and_pushes_its_own_bookkeeping(repo, fake_gh):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)  # phase 1's changes, committed as phase 2 would

    (repo / "feature.txt").write_text("the change\n")
    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["pr_url"] == FAKE_PR_URL

    # nothing left uncommitted after a successful run
    assert implement_task_scaffold.dirty_files(repo) == []

    # the remote branch's history, not just the local working tree, has the update
    _git(["fetch", "origin"], cwd=repo)
    remote_task_text = subprocess.run(
        ["git", "show", f"origin/task-001-first-task:.tasks/TASK-001-first-task.md"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout
    assert "status: in-review" in remote_task_text
    assert FAKE_PR_URL in remote_task_text
    assert _sync_check(repo).returncode == 0


def test_wrap_up_skips_empty_bookkeeping_commit(repo, fake_gh):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)

    # Pre-set the task file to exactly what `wrap-up` would end up writing (the fake PR URL,
    # `status: in-review`) and re-sync, so that when `wrap-up` sets those same fields again,
    # there's genuinely nothing left to commit for the bookkeeping step.
    task_path = repo / ".tasks" / "TASK-001-first-task.md"
    text = task_path.read_text()
    # `render_frontmatter` quotes any scalar containing a colon (a URL always does) --
    # match that canonical form here, or a later re-render would see a spurious diff.
    text = text.replace("pr: null", f'pr: "{FAKE_PR_URL}"').replace("status: in-progress", "status: in-review")
    task_path.write_text(text)
    subprocess.run([sys.executable, str(repo / ".tasks" / "bin" / "sync")], cwd=repo, check=True)
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "pre-set to what wrap-up will write"], cwd=repo)
    before_log = _git(["log", "--oneline"], cwd=repo).stdout

    (repo / "feature.txt").write_text("the change\n")
    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode == 0, result.stderr
    after_log = _git(["log", "--oneline"], cwd=repo).stdout
    # exactly one new commit (the "paths" commit) -- no separate, empty bookkeeping commit
    assert len(after_log.splitlines()) == len(before_log.splitlines()) + 1
    assert "record PR" not in after_log
    assert implement_task_scaffold.dirty_files(repo) == []


def _set_format_command(cwd, command):
    """Rewrite the scaffolded `format_command: null` line in `.tasks/config.md` -- same
    hand-edit-frontmatter technique as `_set_ignored_paths`.
    """
    config_path = cwd / ".tasks" / "config.md"
    text = config_path.read_text().replace("format_command: null", f"format_command: {command}")
    config_path.write_text(text)


def test_wrap_up_amends_format_command_changes_into_the_existing_commit(repo, fake_gh):
    _set_format_command(repo, "echo formatted >> feature.txt")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "configure format_command"], cwd=repo)
    _git(["push"], cwd=repo)

    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)
    before_log = _git(["log", "--oneline"], cwd=repo).stdout

    (repo / "feature.txt").write_text("the change\n")
    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode == 0, result.stderr
    assert (repo / "feature.txt").read_text() == "the change\nformatted\n"
    assert implement_task_scaffold.dirty_files(repo) == []

    # the formatter's change was folded into the existing commit, not added as a new one
    after_log = _git(["log", "--oneline"], cwd=repo).stdout
    assert len(after_log.splitlines()) == len(before_log.splitlines()) + 2  # paths commit + bookkeeping

    _git(["fetch", "origin"], cwd=repo)
    remote_feature_text = subprocess.run(
        ["git", "show", "origin/task-001-first-task:feature.txt"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout
    assert remote_feature_text == "the change\nformatted\n"
    assert _sync_check(repo).returncode == 0


def test_wrap_up_skips_format_step_when_null(repo, fake_gh):
    # `format_command: null` is the default -- confirm the step is a true no-op, not just
    # "happens to do nothing" (no new commit for it, working tree stays exactly as committed).
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)
    before_log = _git(["log", "--oneline"], cwd=repo).stdout

    (repo / "feature.txt").write_text("the change\n")
    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode == 0, result.stderr
    assert (repo / "feature.txt").read_text() == "the change\n"
    after_log = _git(["log", "--oneline"], cwd=repo).stdout
    assert len(after_log.splitlines()) == len(before_log.splitlines()) + 2  # paths commit + bookkeeping


def test_wrap_up_stops_on_format_command_failure(repo, fake_gh):
    _set_format_command(repo, "exit 1")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "configure format_command"], cwd=repo)
    _git(["push"], cwd=repo)

    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)

    (repo / "feature.txt").write_text("the change\n")
    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode != 0
    assert "format_command" in result.stderr

    # the paths commit happened (it precedes the format step), but nothing was pushed and no
    # PR was created -- the formatter failure stopped everything after it
    assert implement_task_scaffold.local_branch_exists(repo, "task-001-first-task")
    assert not implement_task_scaffold.remote_branch_exists(repo, "origin", "task-001-first-task")
    task_text = (repo / ".tasks" / "TASK-001-first-task.md").read_text()
    assert "status: in-progress" in task_text
    assert "pr: null" in task_text


def test_start_refuses_on_dirty_tree(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    (repo / "README.md").write_text("dirty\n")

    result = _run_start(repo)

    assert result.returncode != 0
    assert "dirty" in result.stderr
    assert implement_task_scaffold.current_branch(repo) == "main"


def test_start_auto_picks_top_unblocked_and_skips_blocked(repo):
    _add_task(repo, "First task")
    _add_task(repo, "Second task", blocked_by=["TASK-001"])
    _add_task(repo, "Third task")
    _push_tasks(repo)

    result = _run_start(repo)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["task_id"] == "TASK-001"
    assert output["skipped"] == []  # TASK-001 is first and unblocked, nothing to skip


def test_start_skips_blocked_task_when_it_is_first(repo):
    _add_task(repo, "First task")
    _add_task(repo, "Second task")
    _push_tasks(repo)
    # reorder so the blocked one is first: mark TASK-001 blocked_by TASK-002 by hand
    task_path = repo / ".tasks" / "TASK-001-first-task.md"
    text = task_path.read_text().replace("blocked_by: []", "blocked_by: [TASK-002]")
    task_path.write_text(text)
    subprocess.run([sys.executable, str(repo / ".tasks" / "bin" / "sync")], cwd=repo, check=True)
    _push_tasks(repo)

    result = _run_start(repo)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["task_id"] == "TASK-002"
    assert output["skipped"] == [{"id": "TASK-001", "reason": "blocked_by TASK-002"}]


def test_start_refuses_explicit_task_not_todo(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    first = _run_start(repo)
    assert first.returncode == 0, first.stderr
    # `start` only sets frontmatter + runs sync -- committing is phase 3's job. Commit
    # here (as phase 2 would before moving on) so the tree is clean and the second
    # `start` call actually reaches the status check instead of the dirty-tree one.
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)

    result = _run_start(repo, task_id="TASK-001")

    assert result.returncode != 0
    assert "resume" in result.stderr


def test_start_refuses_explicit_task_still_blocked(repo):
    _add_task(repo, "First task")
    _add_task(repo, "Second task", blocked_by=["TASK-001"])
    _push_tasks(repo)

    result = _run_start(repo, task_id="TASK-002")

    assert result.returncode != 0
    assert "TASK-001" in result.stderr


def test_start_creates_branch_and_sets_frontmatter(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)

    result = _run_start(repo, task_id="TASK-001")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["task_id"] == "TASK-001"
    assert implement_task_scaffold.current_branch(repo) == output["branch"]

    task_text = (repo / ".tasks" / "TASK-001-first-task.md").read_text()
    assert "status: in-progress" in task_text
    assert f"branch: {output['branch']}" in task_text
    assert _sync_check(repo).returncode == 0
    assert output["stop_required"] is True


def test_start_batch_mode_sets_stop_required_false(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)

    result = _run_start(repo, task_id="TASK-001", batch_mode=True)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["stop_required"] is False


def test_bail_out_reverts_status_to_todo(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr

    answers_path = repo.parent / "bail-answers.json"
    answers_path.write_text(json.dumps({"task_id": "TASK-001", "status": "todo"}))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "bail-out", str(answers_path)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    task_text = (repo / ".tasks" / "TASK-001-first-task.md").read_text()
    assert "status: todo" in task_text
    assert _sync_check(repo).returncode == 0


def test_bail_out_refuses_unknown_status(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    answers_path = repo.parent / "bail-answers.json"
    answers_path.write_text(json.dumps({"task_id": "TASK-001", "status": "done"}))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "bail-out", str(answers_path)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode != 0
    assert "done" in result.stderr


def test_resume_state_is_phase1_on_fresh_repo(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "resume-state"], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"phase": "phase1"}


def test_resume_state_is_phase2_when_in_progress_and_dirty(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    (repo / "scratch.txt").write_text("wip\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "resume-state"], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"phase": "phase2", "task_id": "TASK-001"}


def test_resume_state_is_phase3_when_in_progress_and_clean(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    # `start` leaves the frontmatter/sync changes uncommitted (that's phase 3's job) --
    # commit them so the tree is genuinely clean, matching "code already committed".
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "resume-state"], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"phase": "phase3", "task_id": "TASK-001"}


# ---------------------------------------------------------------------------
# `ignored_paths` (TASK-028): a dirty configured path never blocks start/resume, and gets
# stashed/restored around wrap-up's rebase same as `.tmp/prompts.md` used to be hardcoded to.
# ---------------------------------------------------------------------------


def test_start_ignores_dirty_configured_ignored_path(repo):
    _set_ignored_paths(repo, [".tmp/prompts.md"])
    _add_task(repo, "First task")
    _push_tasks(repo)
    (repo / ".tmp").mkdir(exist_ok=True)
    (repo / ".tmp" / "prompts.md").write_text("scratch notes\n")

    result = _run_start(repo)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["task_id"] == "TASK-001"


def test_start_still_refuses_on_a_dirty_file_not_in_ignored_paths(repo):
    _set_ignored_paths(repo, [".tmp/prompts.md"])
    _add_task(repo, "First task")
    _push_tasks(repo)
    (repo / ".tmp").mkdir(exist_ok=True)
    (repo / ".tmp" / "prompts.md").write_text("scratch notes\n")
    (repo / "README.md").write_text("dirty\n")

    result = _run_start(repo)

    assert result.returncode != 0
    assert "README.md" in result.stderr
    assert ".tmp/prompts.md" not in result.stderr


def test_resume_state_ignores_dirty_configured_ignored_path(repo):
    _set_ignored_paths(repo, [".tmp/prompts.md"])
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)
    (repo / ".tmp").mkdir(exist_ok=True)
    (repo / ".tmp" / "prompts.md").write_text("scratch notes\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "resume-state"], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    # dirty, but only the ignored path -- still phase3, not phase2
    assert json.loads(result.stdout) == {"phase": "phase3", "task_id": "TASK-001"}


def test_wrap_up_stashes_and_restores_dirty_ignored_paths_around_rebase(repo, fake_gh):
    _set_ignored_paths(repo, [".tmp/prompts.md"])
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)

    (repo / ".tmp").mkdir(exist_ok=True)
    (repo / ".tmp" / "prompts.md").write_text("scratch notes\n")
    (repo / "feature.txt").write_text("the change\n")

    result = _run_wrap_up(repo, {
        "task_id": "TASK-001",
        "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature",
        "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body",
        "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)

    assert result.returncode == 0, result.stderr
    # the ignored path survived the rebase, still dirty (never committed, never lost)
    assert (repo / ".tmp" / "prompts.md").read_text() == "scratch notes\n"
    assert ".tmp/prompts.md" in implement_task_scaffold.dirty_files(repo)
    # and it's genuinely not part of the pushed commit
    show = _git(["show", "--stat", "HEAD"], cwd=repo).stdout
    assert "prompts.md" not in show


# ---------------------------------------------------------------------------
# record-outcome / render-outcome-table CLI subcommands (TASK-041): thin,
# side-effect-free wrappers -- no scratch repo needed, just a tmp_path cwd.
# ---------------------------------------------------------------------------


def _run_scaffold(cwd, command, answers):
    answers_path = cwd / f"{command}-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), command, str(answers_path)], cwd=cwd, capture_output=True, text=True
    )


def test_cmd_record_outcome_appends_entry(tmp_path):
    existing = [{"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc"}]
    entry = {"task_id": "TASK-002", "title": "Second", "status": "done", "link": "def"}

    result = _run_scaffold(tmp_path, "record-outcome", {"outcomes": existing, "entry": entry})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"outcomes": existing + [entry]}


def test_cmd_record_outcome_refuses_incomplete_entry(tmp_path):
    entry = {"task_id": "TASK-001", "title": "First", "link": "abc"}  # no "status"

    result = _run_scaffold(tmp_path, "record-outcome", {"outcomes": [], "entry": entry})

    assert result.returncode != 0
    assert "status" in result.stderr


def test_cmd_render_outcome_table(tmp_path):
    outcomes = [{"task_id": "TASK-001", "title": "First", "status": "done", "link": "abc"}]

    result = _run_scaffold(tmp_path, "render-outcome-table", {"outcomes": outcomes})

    assert result.returncode == 0, result.stderr
    table = json.loads(result.stdout)["table"]
    assert "| TASK-001 | First | done | abc |" in table
