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
# interrupt_routing: the five-condition taxonomy -- isolated (skip this task,
# continue the batch) vs. systemic (halt the batch).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind",
    ["needs_clarification", "unexpected_blocker", "quality_gate_failure", "guardrail_denial"],
)
def test_interrupt_routing_isolated_kinds_continue_the_batch(kind):
    assert implement_task_scaffold.interrupt_routing(kind) == {
        "routing": "isolated", "continue_batch": True,
    }


@pytest.mark.parametrize(
    "kind", ["infra_failure", "context_usage_exceeded", "token_budget_exceeded"],
)
def test_interrupt_routing_systemic_kinds_halt_the_batch(kind):
    assert implement_task_scaffold.interrupt_routing(kind) == {
        "routing": "systemic", "continue_batch": False,
    }


def test_interrupt_routing_raises_on_unknown_kind():
    with pytest.raises(ValueError, match="bogus"):
        implement_task_scaffold.interrupt_routing("bogus")


# ---------------------------------------------------------------------------
# check_usage_thresholds / render_usage_summary (TASK-043): the context/token
# safety-valve -- pure functions over caller-supplied usage figures (this
# harness exposes no tool that reports exact usage, so these are estimates).
# ---------------------------------------------------------------------------


def test_check_usage_thresholds_under_both_is_no_halt():
    result = implement_task_scaffold.check_usage_thresholds(
        context_pct=40, halt_pct=85, tokens_used=1000, token_budget=100000,
    )
    assert result == {"halt": False, "kind": None, "message": None}


def test_check_usage_thresholds_context_over_halts_and_names_it():
    result = implement_task_scaffold.check_usage_thresholds(
        context_pct=90, halt_pct=85, tokens_used=1000, token_budget=None,
    )
    assert result["halt"] is True
    assert result["kind"] == "context_usage_exceeded"
    assert "90" in result["message"]
    assert "85" in result["message"]


def test_check_usage_thresholds_token_budget_over_halts_and_names_it():
    result = implement_task_scaffold.check_usage_thresholds(
        context_pct=10, halt_pct=85, tokens_used=50000, token_budget=40000,
    )
    assert result["halt"] is True
    assert result["kind"] == "token_budget_exceeded"
    assert "50000" in result["message"]
    assert "40000" in result["message"]


def test_check_usage_thresholds_no_token_budget_never_triggers_it():
    result = implement_task_scaffold.check_usage_thresholds(
        context_pct=10, halt_pct=85, tokens_used=10_000_000, token_budget=None,
    )
    assert result == {"halt": False, "kind": None, "message": None}


def test_check_usage_thresholds_context_checked_before_token_budget():
    # both crossed at once -- context is reported, matching the checkpoint order in SKILL.md
    result = implement_task_scaffold.check_usage_thresholds(
        context_pct=95, halt_pct=85, tokens_used=50000, token_budget=40000,
    )
    assert result["kind"] == "context_usage_exceeded"


def test_render_usage_summary_includes_context_and_tokens_with_no_cap():
    summary = implement_task_scaffold.render_usage_summary(
        context_pct=42, tokens_used=12345, token_budget=None,
    )
    assert "42" in summary
    assert "12345" in summary
    assert "no cap" in summary


def test_render_usage_summary_includes_the_budget_when_set():
    summary = implement_task_scaffold.render_usage_summary(
        context_pct=42, tokens_used=12345, token_budget=100000,
    )
    assert "100000" in summary


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
    must not fail on it regardless); `pr view` reports the PR already MERGED (TASK-069's
    `finish-merge` tests). Prepend this directory to `PATH` to use it in a subprocess.
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
        "if args[:2] == ['pr', 'view']:\n"
        "    print('{\"state\": \"MERGED\", \"mergeCommit\": {\"oid\": \"abc1234\"}}')\n"
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


def test_cmd_classify_interrupt_isolated(tmp_path):
    result = _run_scaffold(tmp_path, "classify-interrupt", {"kind": "unexpected_blocker"})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"routing": "isolated", "continue_batch": True}


def test_cmd_classify_interrupt_systemic(tmp_path):
    result = _run_scaffold(tmp_path, "classify-interrupt", {"kind": "infra_failure"})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"routing": "systemic", "continue_batch": False}


def test_cmd_classify_interrupt_refuses_unknown_kind(tmp_path):
    result = _run_scaffold(tmp_path, "classify-interrupt", {"kind": "bogus"})

    assert result.returncode != 0
    assert "bogus" in result.stderr


def test_cmd_check_usage_thresholds_halts_on_context(tmp_path):
    result = _run_scaffold(tmp_path, "check-usage-thresholds", {
        "context_pct": 90, "halt_pct": 85, "tokens_used": 100, "token_budget": None,
    })

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["halt"] is True
    assert output["kind"] == "context_usage_exceeded"


def test_cmd_check_usage_thresholds_no_halt(tmp_path):
    result = _run_scaffold(tmp_path, "check-usage-thresholds", {
        "context_pct": 10, "halt_pct": 85, "tokens_used": 100, "token_budget": None,
    })

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"halt": False, "kind": None, "message": None}


def test_cmd_render_usage_summary(tmp_path):
    result = _run_scaffold(tmp_path, "render-usage-summary", {
        "context_pct": 42, "tokens_used": 12345, "token_budget": None,
    })

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)["summary"]
    assert "42" in summary
    assert "12345" in summary


# ---------------------------------------------------------------------------
# Persistent batch state (TASK-070): a local, untracked `.tmp/batch-state.json` so a lost
# session can pick a batch back up from repo state. Pure helpers first (path-in, no git), then
# the CLI subcommands and `resume-state` integration against a real scratch repo.
# ---------------------------------------------------------------------------

_SELECTION = {"mode": "list", "tasks": ["TASK-001", "TASK-002", "TASK-003"]}
_ORDER = ["TASK-001", "TASK-002", "TASK-003"]


def _entry(task_id, status="done", link="abc"):
    return {"task_id": task_id, "title": f"Title {task_id}", "status": status, "link": link}


def test_batch_state_path_is_under_dot_tmp(tmp_path):
    assert implement_task_scaffold.batch_state_path(tmp_path) == tmp_path / ".tmp" / "batch-state.json"


def test_new_batch_state_records_selection_order_and_empty_progress():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)

    assert state == {
        "selection": _SELECTION, "order": _ORDER, "accounted": [], "outcomes": [], "follow_ups": [],
        "critic_reviews": [],
    }


def test_batch_state_round_trips_through_the_file(tmp_path):
    path = implement_task_scaffold.batch_state_path(tmp_path)
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)

    implement_task_scaffold.write_batch_state(path, state)  # creates .tmp/ as needed

    assert implement_task_scaffold.read_batch_state(path) == state


def test_read_batch_state_is_none_when_missing_or_unreadable(tmp_path):
    path = implement_task_scaffold.batch_state_path(tmp_path)
    assert implement_task_scaffold.read_batch_state(path) is None

    path.parent.mkdir()
    path.write_text("{not json")
    assert implement_task_scaffold.read_batch_state(path) is None

    path.write_text(json.dumps({"order": ["TASK-001"]}))  # missing required keys
    assert implement_task_scaffold.read_batch_state(path) is None


def test_advance_batch_state_appends_outcome_and_marks_accounted_without_mutating():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)

    advanced = implement_task_scaffold.advance_batch_state(state, _entry("TASK-001"), accounted=True)

    assert advanced["accounted"] == ["TASK-001"]
    assert advanced["outcomes"] == [_entry("TASK-001")]
    assert state["accounted"] == [] and state["outcomes"] == []


def test_advance_batch_state_provisional_outcome_is_not_accounted_then_replaced_in_place():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)
    state = implement_task_scaffold.advance_batch_state(
        state, _entry("TASK-001", status="in-review", link="pr-url"), accounted=False
    )
    assert state["accounted"] == []

    state = implement_task_scaffold.advance_batch_state(state, _entry("TASK-001"), accounted=True)

    assert state["accounted"] == ["TASK-001"]
    assert state["outcomes"] == [_entry("TASK-001")]  # replaced, not duplicated


def test_advance_batch_state_rejects_a_task_outside_the_order():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)

    with pytest.raises(ValueError, match="TASK-099"):
        implement_task_scaffold.advance_batch_state(state, _entry("TASK-099"), accounted=True)


def test_batch_progress_names_next_task_and_remaining():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)
    state = implement_task_scaffold.advance_batch_state(state, _entry("TASK-001"), accounted=True)

    progress = implement_task_scaffold.batch_progress(state)

    assert progress["next_task_id"] == "TASK-002"
    assert progress["remaining"] == ["TASK-002", "TASK-003"]
    assert progress["accounted"] == ["TASK-001"]
    assert progress["order"] == _ORDER
    assert progress["selection"] == _SELECTION
    assert progress["outcomes"] == [_entry("TASK-001")]


def test_batch_progress_next_task_skips_accounted_tasks_out_of_order():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)
    state = implement_task_scaffold.advance_batch_state(state, _entry("TASK-002", status="todo"), accounted=True)

    assert implement_task_scaffold.batch_progress(state)["next_task_id"] == "TASK-001"


def test_batch_is_complete_once_every_task_is_accounted():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)
    assert not implement_task_scaffold.batch_is_complete(state)
    for task_id in _ORDER:
        state = implement_task_scaffold.advance_batch_state(state, _entry(task_id), accounted=True)
    assert implement_task_scaffold.batch_is_complete(state)
    assert implement_task_scaffold.batch_progress(state)["next_task_id"] is None


def test_clear_batch_state_removes_the_file_and_tolerates_absence(tmp_path):
    path = implement_task_scaffold.batch_state_path(tmp_path)
    implement_task_scaffold.write_batch_state(path, implement_task_scaffold.new_batch_state(_SELECTION, _ORDER))

    assert implement_task_scaffold.clear_batch_state(path) is True
    assert not path.exists()
    assert implement_task_scaffold.clear_batch_state(path) is False


def _run_batch(repo, command, answers):
    """Like `_run_scaffold`, but the answers file lives outside the repo so it never dirties it."""
    answers_path = repo.parent / f"{command}-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), command, str(answers_path)], cwd=repo, capture_output=True, text=True
    )


def _batch_state_file(repo):
    return repo / ".tmp" / "batch-state.json"


def _resume_state(repo):
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "resume-state"], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cmd_batch_init_writes_the_state_file(repo):
    result = _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})

    assert result.returncode == 0, result.stderr
    on_disk = json.loads(_batch_state_file(repo).read_text())
    assert on_disk == {
        "selection": _SELECTION, "order": _ORDER, "accounted": [], "outcomes": [], "follow_ups": [],
        "critic_reviews": [],
    }
    assert json.loads(result.stdout)["next_task_id"] == "TASK-001"


def test_cmd_batch_update_records_progress_and_keeps_file(repo):
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})

    result = _run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True})

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["complete"] is False
    assert output["next_task_id"] == "TASK-002"
    assert json.loads(_batch_state_file(repo).read_text())["accounted"] == ["TASK-001"]


def test_cmd_batch_update_deletes_file_when_last_task_accounted(repo):
    _run_batch(repo, "batch-init", {"selection": {"mode": "list", "tasks": ["TASK-001"]}, "order": ["TASK-001"]})

    result = _run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True})

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["complete"] is True
    assert output["outcomes"] == [_entry("TASK-001")]
    assert not _batch_state_file(repo).exists()


def test_cmd_batch_update_refuses_without_an_active_batch(repo):
    result = _run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True})

    assert result.returncode != 0
    assert "batch" in result.stderr


def test_cmd_batch_clear_removes_the_file_on_a_systemic_halt(repo):
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})

    result = _run_batch(repo, "batch-clear", {})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cleared": True}
    assert not _batch_state_file(repo).exists()
    assert "batch" not in _resume_state(repo)


def test_resume_state_has_no_batch_key_without_a_state_file(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)

    assert _resume_state(repo) == {"phase": "phase1"}


def test_resume_state_reports_active_batch_at_phase1_with_next_task(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})
    _run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True})

    state = _resume_state(repo)

    assert state["phase"] == "phase1"
    assert state["batch"]["next_task_id"] == "TASK-002"
    assert state["batch"]["remaining"] == ["TASK-002", "TASK-003"]
    assert state["batch"]["order"] == _ORDER
    assert state["batch"]["outcomes"] == [_entry("TASK-001")]


def test_resume_state_keeps_task_phase_and_adds_batch_info_for_an_in_flight_task(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001", batch_mode=True)
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})

    state = _resume_state(repo)

    assert state["phase"] == "phase3"
    assert state["task_id"] == "TASK-001"
    assert state["batch"]["next_task_id"] == "TASK-001"


def test_batch_state_file_never_blocks_start_or_resume_even_when_not_gitignored(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})
    assert ".tmp/batch-state.json" in implement_task_scaffold.dirty_files(repo)  # genuinely untracked here

    assert _resume_state(repo)["phase"] == "phase1"  # not phase2
    started = _run_start(repo, task_id="TASK-001", batch_mode=True)
    assert started.returncode == 0, started.stderr
    assert _batch_state_file(repo).exists()  # start/checkout left it alone


# ---------------------------------------------------------------------------
# compute_session_token_usage / `session-token-usage` (TASK-068): an exact `tokens_used` summed
# from the session's own transcript JSONL, reproducing ccstatusline's dedup-then-sum algorithm.
# ---------------------------------------------------------------------------


def _usage_line(stop_reason, *, inp=0, out=0, cache_read=0, cache_create=0, kind="assistant"):
    return json.dumps({"type": kind, "message": {"stop_reason": stop_reason, "usage": {
        "input_tokens": inp, "output_tokens": out,
        "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": cache_create,
    }}})


def _write_transcript(path, lines):
    path.write_text("\n".join(lines) + "\n")
    return path


def test_compute_session_token_usage_sums_all_four_fields(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", [
        _usage_line("tool_use", inp=2, out=100, cache_read=0, cache_create=5000),
        _usage_line("end_turn", inp=3, out=50, cache_read=5000, cache_create=200),
    ])

    result = implement_task_scaffold.compute_session_token_usage(transcript)

    assert result == {
        "tokens_used": 2 + 100 + 5000 + 3 + 50 + 5000 + 200 + 0,
        "input_tokens": 5, "output_tokens": 150,
        "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 5200,
    }


def test_compute_session_token_usage_drops_streaming_partials(tmp_path):
    # A streaming partial (no stop_reason) followed by the final entry for the same message:
    # only the final one counts.
    transcript = _write_transcript(tmp_path / "t.jsonl", [
        _usage_line(None, inp=1, out=10),
        _usage_line("end_turn", inp=1, out=40),
        _usage_line("tool_use", inp=2, out=5),
    ])

    result = implement_task_scaffold.compute_session_token_usage(transcript)

    assert result["tokens_used"] == (1 + 40) + (2 + 5)


def test_compute_session_token_usage_keeps_a_trailing_unfinished_entry(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", [
        _usage_line("end_turn", inp=1, out=40),
        _usage_line(None, inp=2, out=7),  # the turn still in progress
    ])

    result = implement_task_scaffold.compute_session_token_usage(transcript)

    assert result["tokens_used"] == (1 + 40) + (2 + 7)


def test_compute_session_token_usage_skips_lines_without_usage_and_blank_lines(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
        "",
        json.dumps({"type": "summary"}),
        _usage_line("end_turn", inp=1, out=2),
    ])

    assert implement_task_scaffold.compute_session_token_usage(transcript)["tokens_used"] == 3


def test_compute_session_token_usage_raises_on_missing_file(tmp_path):
    with pytest.raises(implement_task_scaffold.TranscriptError, match="not found"):
        implement_task_scaffold.compute_session_token_usage(tmp_path / "nope.jsonl")


def test_compute_session_token_usage_raises_on_malformed_json_naming_the_line(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", [_usage_line("end_turn", inp=1), "{not json"])

    with pytest.raises(implement_task_scaffold.TranscriptError, match="line 2"):
        implement_task_scaffold.compute_session_token_usage(transcript)


def test_compute_session_token_usage_raises_when_no_usage_entries_at_all(tmp_path):
    # e.g. a future transcript-format change: parseable, but nothing recognisable inside.
    transcript = _write_transcript(tmp_path / "t.jsonl", [json.dumps({"type": "user"})])

    with pytest.raises(implement_task_scaffold.TranscriptError, match="usage"):
        implement_task_scaffold.compute_session_token_usage(transcript)


def test_cmd_session_token_usage_returns_total(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", [_usage_line("end_turn", inp=1, out=2, cache_read=3, cache_create=4)])

    result = _run_scaffold(tmp_path, "session-token-usage", {"transcript_path": str(transcript)})

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["tokens_used"] == 10
    assert output["cache_read_input_tokens"] == 3


def test_cmd_session_token_usage_fails_cleanly_on_a_missing_file(tmp_path):
    result = _run_scaffold(tmp_path, "session-token-usage", {"transcript_path": str(tmp_path / "nope.jsonl")})

    assert result.returncode != 0
    assert "not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_cmd_session_token_usage_fails_cleanly_on_a_malformed_file(tmp_path):
    transcript = _write_transcript(tmp_path / "t.jsonl", ["{not json"])

    result = _run_scaffold(tmp_path, "session-token-usage", {"transcript_path": str(transcript)})

    assert result.returncode != 0
    assert "line 1" in result.stderr
    assert "Traceback" not in result.stderr


# ---------------------------------------------------------------------------
# Bookkeeping commits stage only what they own (TASK-069): a stray untracked file in `.tasks/`
# (e.g. leftovers from an in-flight `add-task` run) must never be swept into `wrap-up`'s or `finish-merge`'s
# bookkeeping commit -- `finish-merge`'s is pushed straight to the default branch.
# ---------------------------------------------------------------------------

_STRAY = Path(".tasks") / "scratch-notes.txt"


def _committed_files(cwd, rev="HEAD"):
    return set(_git(["show", "--name-only", "--no-renames", "--format=", rev], cwd=cwd).stdout.split())


def _run_finish_merge(cwd, fake_gh, task_id="TASK-001"):
    answers_path = cwd.parent / "finish-merge-answers.json"
    answers_path.write_text(json.dumps({
        "task_id": task_id, "bookkeeping_commit_message": f"chore({task_id}): phase 4",
    }))
    env = os.environ.copy()
    env["PATH"] = f"{fake_gh}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "finish-merge", str(answers_path)],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def _wrapped_up_task(repo, fake_gh, stray=False):
    """A scratch repo with TASK-001 started, committed and wrapped up (PR "opened")."""
    _add_task(repo, "First task")
    _push_tasks(repo)
    started = _run_start(repo, task_id="TASK-001")
    assert started.returncode == 0, started.stderr
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "wip"], cwd=repo)
    (repo / "feature.txt").write_text("the change\n")
    if stray:
        (repo / _STRAY).write_text("stray file from unrelated in-flight work\n")
    return _run_wrap_up(repo, {
        "task_id": "TASK-001", "paths": ["feature.txt"],
        "commit_message": "feat(TASK-001): add the feature", "pr_title": "feat(TASK-001): add the feature",
        "pr_body": "body", "bookkeeping_commit_message": "chore(TASK-001): record PR, set status in-review",
    }, fake_gh)


def test_wrap_up_bookkeeping_commit_leaves_a_stray_untracked_tasks_file_alone(repo, fake_gh):
    result = _wrapped_up_task(repo, fake_gh, stray=True)

    assert result.returncode == 0, result.stderr
    bookkeeping = _committed_files(repo)  # HEAD is the bookkeeping commit
    assert ".tasks/TASK-001-first-task.md" in bookkeeping  # still stages what it owns
    assert str(_STRAY) not in bookkeeping
    assert str(_STRAY) not in _committed_files(repo, "HEAD~1")
    assert (repo / _STRAY).exists()
    assert str(_STRAY) in implement_task_scaffold.dirty_files(repo)  # still untracked


def _squash_merge_and_return(repo, branch):
    """Stand in for the human's squash-merge on GitHub: land `branch` on main, push, come back."""
    _git(["checkout", "-q", "main"], cwd=repo)
    _git(["merge", "--squash", branch], cwd=repo)
    _git(["commit", "-q", "-m", "squash-merge TASK-001"], cwd=repo)
    _git(["push", "-q", "origin", "main"], cwd=repo)
    _git(["checkout", "-q", branch], cwd=repo)


def test_finish_merge_commits_and_pushes_archive_board_and_epic_bookkeeping(repo, fake_gh):
    result = _wrapped_up_task(repo, fake_gh)
    assert result.returncode == 0, result.stderr
    _squash_merge_and_return(repo, "task-001-first-task")

    result = _run_finish_merge(repo, fake_gh)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"merged": True, "merge_commit": "abc1234"}
    bookkeeping = _committed_files(repo)
    assert ".tasks/archive/TASK-001-first-task.md" in bookkeeping  # the archived task file
    assert ".tasks/TASK-001-first-task.md" in bookkeeping  # ...and its removal from `.tasks/`
    assert ".tasks/BOARD.md" in bookkeeping
    assert not (repo / ".tasks" / "TASK-001-first-task.md").exists()
    assert implement_task_scaffold.dirty_files(repo) == []
    assert _sync_check(repo).returncode == 0
    # pushed to the default branch, not just committed locally
    _git(["fetch", "origin"], cwd=repo)
    assert _git(["rev-parse", "HEAD"], cwd=repo).stdout == _git(["rev-parse", "origin/main"], cwd=repo).stdout


def test_finish_merge_bookkeeping_commit_leaves_a_stray_untracked_tasks_file_alone(repo, fake_gh):
    result = _wrapped_up_task(repo, fake_gh)
    assert result.returncode == 0, result.stderr
    _squash_merge_and_return(repo, "task-001-first-task")
    (repo / _STRAY).write_text("stray file from unrelated in-flight work\n")

    result = _run_finish_merge(repo, fake_gh)

    assert result.returncode == 0, result.stderr
    bookkeeping = _committed_files(repo)
    assert ".tasks/archive/TASK-001-first-task.md" in bookkeeping  # still stages what it owns
    assert str(_STRAY) not in bookkeeping
    assert (repo / _STRAY).exists()
    assert implement_task_scaffold.dirty_files(repo) == [str(_STRAY)]  # still untracked
    _git(["fetch", "origin"], cwd=repo)
    remote_files = _git(["ls-tree", "-r", "--name-only", "origin/main"], cwd=repo).stdout.split()
    assert str(_STRAY) not in remote_files


# ---------------------------------------------------------------------------
# Autonomous follow-up task creation (TASK-044): a per-batch limit
# (`autonomous_new_task_limit`), the follow-up ledger in the batch-state file, and the
# `create-follow-up` / `render-follow-up-summary` subcommands.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("created,limit,allowed", [
    (0, 3, True), (2, 3, True), (3, 3, False), (5, 3, False),
    (0, 0, False),                       # 0 disables autonomous creation outright
    (0, None, True), (1000, None, True),  # null = unlimited
])
def test_check_follow_up_limit(created, limit, allowed):
    result = implement_task_scaffold.check_follow_up_limit(created=created, limit=limit)

    assert result["allowed"] is allowed
    if allowed:
        assert result["message"] is None
    else:
        assert str(limit) in result["message"] and str(created) in result["message"]


@pytest.mark.parametrize("bad", ["3", -1, 2.5, True])
def test_check_follow_up_limit_rejects_a_non_integer_or_negative_limit(bad):
    with pytest.raises(ValueError, match="autonomous_new_task_limit"):
        implement_task_scaffold.check_follow_up_limit(created=0, limit=bad)


def _follow_up(task_id="TASK-050", created=True, title="Split-off piece", why="original was oversized"):
    return {"task_id": task_id if created else None, "title": title, "why": why,
            "parent_task_id": "TASK-001", "created": created}


def test_record_follow_up_appends_without_mutating_and_counts_only_created():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)

    state2 = implement_task_scaffold.record_follow_up(state, _follow_up("TASK-050"))
    state3 = implement_task_scaffold.record_follow_up(state2, _follow_up(created=False))

    assert state["follow_ups"] == []
    assert len(state3["follow_ups"]) == 2
    assert implement_task_scaffold.count_created_follow_ups(state3) == 1


def test_read_batch_state_tolerates_a_state_file_written_before_follow_ups_existed(tmp_path):
    path = implement_task_scaffold.batch_state_path(tmp_path)
    legacy = {"selection": _SELECTION, "order": _ORDER, "accounted": [], "outcomes": []}
    path.parent.mkdir()
    path.write_text(json.dumps(legacy))

    state = implement_task_scaffold.read_batch_state(path)

    assert state["follow_ups"] == []


def test_batch_progress_includes_follow_ups():
    state = implement_task_scaffold.new_batch_state(_SELECTION, _ORDER)
    state = implement_task_scaffold.record_follow_up(state, _follow_up())

    assert implement_task_scaffold.batch_progress(state)["follow_ups"] == [_follow_up()]


def test_render_follow_up_summary_lists_created_with_why_and_flags_the_rest():
    text = implement_task_scaffold.render_follow_up_summary([
        _follow_up("TASK-050", title="Piece A", why="oversized"),
        _follow_up(created=False, title="Piece B", why="also oversized"),
    ])

    assert "| TASK-050 | Piece A | oversized | TASK-001 |" in text
    assert "Piece B" in text and "also oversized" in text
    assert text.index("Piece A") < text.index("Piece B")
    assert "not created" in text.lower()


def test_render_follow_up_summary_when_none():
    assert "none" in implement_task_scaffold.render_follow_up_summary([]).lower()


def _set_config_line(repo, key, value):
    """Set (or add, or -- with `None` as the *string* sentinel "__drop__" -- remove) a config key."""
    config_path = repo / ".tasks" / "config.md"
    lines = config_path.read_text().splitlines()
    out = []
    replaced = False
    for line in lines:
        if line.startswith(f"{key}:"):
            replaced = True
            if value != "__drop__":
                out.append(f"{key}: {value}")
        else:
            out.append(line)
    if not replaced and value != "__drop__":
        out.insert(out.index("---", 1), f"{key}: {value}")
    config_path.write_text("\n".join(out) + "\n")


def _follow_up_answers(title="Split-off piece", **overrides):
    answers = {"title": title, "type": "chore", "why": "the original task was oversized", "parent_task_id": "TASK-001"}
    answers.update(overrides)
    return answers


def _repo_in_a_batch(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": ["TASK-001"]})
    return repo


def _todo_ids(repo):
    board = (repo / ".tasks" / "BOARD.md").read_text()
    todo = board.split("## TODO", 1)[1]
    return [line.split()[1] for line in todo.splitlines() if line.startswith("- TASK-")]


def test_cmd_create_follow_up_creates_a_well_formed_task_at_the_bottom_of_todo(repo):
    _repo_in_a_batch(repo)

    result = _run_batch(repo, "create-follow-up", _follow_up_answers())

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["created"] is True
    assert output["task_id"] == "TASK-002"
    task_path = repo / output["path"]
    assert task_path.is_file() and task_path.name.startswith("TASK-002-")
    assert "epic: null" in task_path.read_text()  # unassigned unless the caller says otherwise
    assert _todo_ids(repo) == ["TASK-001", "TASK-002"]  # bottom of TODO, after the existing task
    assert _sync_check(repo).returncode == 0


def test_cmd_create_follow_up_records_it_in_the_batch_state(repo):
    _repo_in_a_batch(repo)

    _run_batch(repo, "create-follow-up", _follow_up_answers(title="Piece A", why="oversized"))

    state = json.loads(_batch_state_file(repo).read_text())
    assert state["follow_ups"] == [{
        "task_id": "TASK-002", "title": "Piece A", "why": "oversized",
        "parent_task_id": "TASK-001", "created": True,
        "path": ".tasks/" + next(p.name for p in (repo / ".tasks").glob("TASK-002-*.md")),
    }]


def test_cmd_create_follow_up_honours_the_caller_epic_blocked_by_and_priority(repo):
    _repo_in_a_batch(repo)

    result = _run_batch(repo, "create-follow-up", _follow_up_answers(
        blocked_by=["TASK-001"], priority_mode="top",
    ))

    assert result.returncode == 0, result.stderr
    assert _todo_ids(repo)[0] == "TASK-002"
    assert "blocked_by: [TASK-001]" in (repo / json.loads(result.stdout)["path"]).read_text()


def test_cmd_create_follow_up_stops_at_the_limit_flags_and_does_not_fail(repo):
    _repo_in_a_batch(repo)
    _set_config_line(repo, "autonomous_new_task_limit", "2")

    outputs = [
        _run_batch(repo, "create-follow-up", _follow_up_answers(title=f"Piece {n}", why=f"reason {n}"))
        for n in (1, 2, 3)
    ]

    assert [r.returncode for r in outputs] == [0, 0, 0]  # reaching the limit never halts the batch
    parsed = [json.loads(r.stdout) for r in outputs]
    assert [p["created"] for p in parsed] == [True, True, False]
    assert parsed[2]["flagged"] is True and "2" in parsed[2]["message"]
    assert len(list((repo / ".tasks").glob("TASK-*.md"))) == 3  # TASK-001 + two follow-ups, no third
    state = json.loads(_batch_state_file(repo).read_text())
    assert [f["created"] for f in state["follow_ups"]] == [True, True, False]
    assert state["follow_ups"][2]["title"] == "Piece 3" and state["follow_ups"][2]["why"] == "reason 3"
    assert _sync_check(repo).returncode == 0


def test_cmd_create_follow_up_null_limit_never_refuses(repo):
    _repo_in_a_batch(repo)
    _set_config_line(repo, "autonomous_new_task_limit", "null")

    results = [json.loads(_run_batch(repo, "create-follow-up", _follow_up_answers(title=f"Piece {n}")).stdout)
               for n in range(5)]

    assert all(r["created"] for r in results)


def test_cmd_create_follow_up_defaults_the_limit_to_three_when_the_key_is_absent(repo):
    _repo_in_a_batch(repo)
    _set_config_line(repo, "autonomous_new_task_limit", "__drop__")

    results = [json.loads(_run_batch(repo, "create-follow-up", _follow_up_answers(title=f"Piece {n}")).stdout)
               for n in range(4)]

    assert [r["created"] for r in results] == [True, True, True, False]


def test_cmd_create_follow_up_refuses_outside_a_batch(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)

    result = _run_batch(repo, "create-follow-up", _follow_up_answers())

    assert result.returncode != 0
    assert "batch" in result.stderr
    assert len(list((repo / ".tasks").glob("TASK-*.md"))) == 1


def test_cmd_create_follow_up_surfaces_an_add_task_failure_and_records_nothing(repo):
    _repo_in_a_batch(repo)

    result = _run_batch(repo, "create-follow-up", _follow_up_answers(epic="EPIC-999"))

    assert result.returncode != 0
    assert "EPIC-999" in result.stderr
    assert json.loads(_batch_state_file(repo).read_text())["follow_ups"] == []
    assert len(list((repo / ".tasks").glob("TASK-*.md"))) == 1


@pytest.mark.parametrize("missing", ["title", "type", "why", "parent_task_id"])
def test_cmd_create_follow_up_requires_its_core_answers(repo, missing):
    _repo_in_a_batch(repo)
    answers = _follow_up_answers()
    del answers[missing]

    result = _run_batch(repo, "create-follow-up", answers)

    assert result.returncode != 0
    assert missing in result.stderr


def test_cmd_batch_update_completion_hands_back_the_follow_ups_for_the_summary(repo):
    _repo_in_a_batch(repo)
    _run_batch(repo, "create-follow-up", _follow_up_answers(title="Piece A"))

    result = _run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True})

    output = json.loads(result.stdout)
    assert output["complete"] is True
    assert [f["title"] for f in output["follow_ups"]] == ["Piece A"]
    assert not _batch_state_file(repo).exists()


def test_cmd_render_follow_up_summary(tmp_path):
    result = _run_scaffold(tmp_path, "render-follow-up-summary", {"follow_ups": [_follow_up("TASK-050", title="Piece A")]})

    assert result.returncode == 0, result.stderr
    assert "| TASK-050 | Piece A |" in json.loads(result.stdout)["summary"]


# ---------------------------------------------------------------------------
# Critic-gated, capped auto-merge (TASK-045): `critic-prompt`, `auto-merge`, the two renderers, and
# `batch-clear` cleaning up the marker. The pure logic is in `test_auto_merge.py`, the marker/hook
# in `test_auto_merge_guardrail.py`; here it's the real subprocess wiring against a scratch repo
# and a configurable `gh` stub that logs every call (and whether the marker existed at that moment).
# ---------------------------------------------------------------------------

_AM_SHA = "a" * 40
_MARKER_REL = ".tmp/auto-merge-marker.json"
_FAKE_GH_AM = r"""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
state_path = os.environ.get("FAKE_GH_STATE")
state = json.load(open(state_path)) if state_path and os.path.exists(state_path) else {}
log_path = os.environ.get("FAKE_GH_LOG")
if log_path:
    with open(log_path, "a") as f:
        f.write(json.dumps({"args": args, "marker_present": os.path.exists(".tmp/auto-merge-marker.json")}) + "\n")
if args[:2] == ["pr", "create"]:
    print("https://example.invalid/pr/1"); sys.exit(0)
if args[:2] == ["pr", "view"]:
    print(json.dumps({"headRefOid": state.get("head_sha", "a" * 40), "state": state.get("pr_state", "OPEN"),
                      "mergeCommit": {"oid": "abc1234"}})); sys.exit(0)
if args[:2] == ["pr", "checks"]:
    print(state.get("checks_out", "all checks passed")); sys.exit(state.get("checks_rc", 0))
if args[:2] == ["pr", "diff"]:
    if "--name-only" in args:
        print("\n".join(state.get("diff_names", [])))
    else:
        print(state.get("diff", "diff --git a/feature.txt b/feature.txt\n+the change\n"))
    sys.exit(0)
if args[:2] == ["pr", "merge"]:
    sys.exit(state.get("merge_rc", 0))
sys.exit(0)
"""


class _FakeGh:
    def __init__(self, root):
        self.dir = root / "bin"
        self.dir.mkdir()
        (self.dir / "gh").write_text(_FAKE_GH_AM)
        (self.dir / "gh").chmod(0o755)
        self.state_path = root / "fake-gh-state.json"
        self.log_path = root / "fake-gh-log.jsonl"
        self.set()

    def set(self, **state):
        base = {"head_sha": _AM_SHA, "checks_rc": 0, "merge_rc": 0,
                "diff_names": ["feature.txt", ".tasks/TASK-001-first-task.md", ".tasks/BOARD.md"]}
        self.state_path.write_text(json.dumps({**base, **state}))

    def env(self):
        env = os.environ.copy()
        env["PATH"] = f"{self.dir}{os.pathsep}{env['PATH']}"
        env["FAKE_GH_STATE"] = str(self.state_path)
        env["FAKE_GH_LOG"] = str(self.log_path)
        return env

    def calls(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]

    def merges(self):
        return [c for c in self.calls() if c["args"][:2] == ["pr", "merge"]]


@pytest.fixture
def fake_gh_am(tmp_path_factory):
    return _FakeGh(tmp_path_factory.mktemp("fake-gh-am"))


def _run_am(repo, fake, command, answers):
    answers_path = repo.parent / f"{command}-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), command, str(answers_path)],
        cwd=repo, capture_output=True, text=True, env=fake.env(),
    )


_APPROVE = json.dumps({
    "approve": True, "criteria_met": True, "scope_ok": True, "gates_passed": True,
    "nothing_alarming": True, "findings": ["all criteria met"],
})
_REJECT = json.dumps({
    "approve": False, "criteria_met": False, "scope_ok": True, "gates_passed": True,
    "nothing_alarming": True, "findings": ["second criterion is not met"],
})


def _auto_merge_answers(verdict=_APPROVE, **overrides):
    answers = {"task_id": "TASK-001", "verdict": verdict, "head_sha": _AM_SHA, "scope_paths": ["feature.txt"]}
    answers.update(overrides)
    return answers


def _am_repo(repo, fake, *, allow="true", cap="5"):
    """TASK-001 wrapped up (PR "open", status in-review) inside an active one-task batch."""
    result = _wrapped_up_task(repo, fake.dir)
    assert result.returncode == 0, result.stderr
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": ["TASK-001"]})
    _set_config_line(repo, "allow_auto_merge", allow)
    _set_config_line(repo, "autonomous_merge_cap", cap)
    fake.log_path.unlink(missing_ok=True)
    return repo


def _reviews(repo):
    return json.loads(_batch_state_file(repo).read_text())["critic_reviews"]


def test_auto_merge_merges_after_every_gate_passes_under_the_real_hook(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["merged"] is True and output["pr"] == 1
    (merge,) = fake_gh_am.merges()
    assert merge["args"][:3] == ["pr", "merge", "1"]
    assert "--squash" in merge["args"]  # `merge_strategy: squash` from config
    assert merge["args"][merge["args"].index("--match-head-commit") + 1] == _AM_SHA
    assert merge["marker_present"] is True  # the marker existed at the moment of the merge...
    assert not (repo / _MARKER_REL).exists()  # ...and is gone afterwards
    (review,) = _reviews(repo)
    assert review["task_id"] == "TASK-001" and review["outcome"] == "auto_merged"
    assert review["findings"] == ["all criteria met"] and review["approve"] is True


def test_auto_merge_uses_the_configured_merge_strategy(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)
    _set_config_line(repo, "merge_strategy", "rebase")

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())

    assert result.returncode == 0, result.stderr
    assert "--rebase" in fake_gh_am.merges()[0]["args"]


def test_auto_merge_is_refused_unless_the_project_opted_in(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am, allow="false")

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["merged"] is False and output["reason"] == "disabled"
    assert output["interrupt"] is None
    assert fake_gh_am.merges() == []
    assert _reviews(repo) == []


def test_a_critic_rejection_does_not_merge_and_names_the_bail_out_interrupt(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers(verdict=_REJECT))

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["merged"] is False and output["reason"] == "critic_rejected"
    assert output["interrupt"] == "critic_rejection"
    assert output["findings"] == ["second criterion is not met"]
    assert fake_gh_am.merges() == []
    (review,) = _reviews(repo)
    assert review["outcome"] == "critic_rejected" and review["approve"] is False


@pytest.mark.parametrize("verdict", ["looks good!", "{}", json.dumps({"approve": True})])
def test_an_unusable_critic_answer_is_a_rejection_never_an_approval(repo, fake_gh_am, verdict):
    _am_repo(repo, fake_gh_am)

    output = json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers(verdict=verdict)).stdout)

    assert output["merged"] is False and output["interrupt"] == "critic_rejection"
    assert fake_gh_am.merges() == []


def _seed_auto_merged(repo, count):
    path = _batch_state_file(repo)
    state = json.loads(path.read_text())
    state["critic_reviews"] = [
        {"task_id": f"TASK-9{n}", "pr": n, "head_sha": "x", "approve": True, "findings": [],
         "checklist": {}, "outcome": "auto_merged"} for n in range(count)
    ]
    path.write_text(json.dumps(state))


def test_the_cap_halts_the_batch_regardless_of_an_approving_critic(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am, cap="2")
    _seed_auto_merged(repo, 2)

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["merged"] is False and output["reason"] == "cap_reached"
    assert output["halt"] is True and output["interrupt"] == "auto_merge_cap_reached"
    assert fake_gh_am.merges() == []
    assert _reviews(repo)[-1]["outcome"] == "skipped:cap_reached"


def test_under_the_cap_it_still_merges(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am, cap="2")
    _seed_auto_merged(repo, 1)

    output = json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers()).stdout)

    assert output["merged"] is True


def test_a_null_cap_never_halts(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am, cap="null")
    _seed_auto_merged(repo, 50)

    assert json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers()).stdout)["merged"] is True


def test_the_cap_defaults_to_five_when_the_key_is_absent(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)
    _set_config_line(repo, "autonomous_merge_cap", "__drop__")
    _seed_auto_merged(repo, 5)

    output = json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers()).stdout)

    assert output["reason"] == "cap_reached"


def test_pending_checks_wait_without_recording_a_review(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)
    fake_gh_am.set(checks_rc=8)

    output = json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers()).stdout)

    assert output["merged"] is False and output["reason"] == "checks_pending" and output["interrupt"] is None
    assert fake_gh_am.merges() == [] and _reviews(repo) == []


@pytest.mark.parametrize("state,reason", [
    ({"checks_rc": 1}, "checks_not_green"),
    ({"diff_names": ["feature.txt", "unrelated/other.py"]}, "scope_violation"),
    ({"head_sha": "b" * 40}, "head_moved"),
    ({"pr_state": "MERGED"}, "pr_not_open"),
])
def test_other_refusals_skip_the_merge_and_are_recorded_but_do_not_end_the_batch(repo, fake_gh_am, state, reason):
    _am_repo(repo, fake_gh_am)
    fake_gh_am.set(**state)

    output = json.loads(_run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers()).stdout)

    assert output["merged"] is False and output["reason"] == reason
    assert output["interrupt"] is None and output["halt"] is False
    assert fake_gh_am.merges() == []
    assert _reviews(repo)[-1]["outcome"] == f"skipped:{reason}"


def test_a_failed_merge_call_surfaces_the_error_and_still_removes_the_marker(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)
    fake_gh_am.set(merge_rc=1)

    result = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())

    assert result.returncode != 0
    assert not (repo / _MARKER_REL).exists()
    assert all(r["outcome"] != "auto_merged" for r in _reviews(repo))


def test_auto_merge_refuses_outside_a_batch_and_for_a_task_not_in_review(repo, fake_gh_am):
    _add_task(repo, "First task")
    _push_tasks(repo)
    no_batch = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())
    assert no_batch.returncode != 0 and "batch" in no_batch.stderr

    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": ["TASK-001"]})
    _set_config_line(repo, "allow_auto_merge", "true")
    not_in_review = _run_am(repo, fake_gh_am, "auto-merge", _auto_merge_answers())
    assert not_in_review.returncode != 0 and "in-review" in not_in_review.stderr
    assert fake_gh_am.merges() == []


def test_critic_prompt_is_built_from_the_task_file_and_the_pr(repo, fake_gh_am):
    _am_repo(repo, fake_gh_am)
    fake_gh_am.set(head_sha=_AM_SHA, diff_names=["feature.txt", ".tasks/BOARD.md"], diff="diff --git a/feature.txt\n+the change\n")

    result = _run_am(repo, fake_gh_am, "critic-prompt", {
        "task_id": "TASK-001", "scope_paths": ["feature.txt"], "gates": "pytest: pass\nsync check: exit 0",
    })

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["head_sha"] == _AM_SHA
    assert output["changed_files"] == ["feature.txt", ".tasks/BOARD.md"]
    prompt = output["prompt"]
    assert "TASK-001" in prompt and "First task" in prompt
    assert "{{criterion}}" in prompt  # the task file's own acceptance-criteria section, verbatim
    assert "feature.txt" in prompt and "+the change" in prompt and "pytest: pass" in prompt
    assert "criteria_met" in prompt


def test_cmd_render_critic_summary_and_batch_result(tmp_path):
    reviews = [{"task_id": "TASK-001", "outcome": "auto_merged", "findings": ["clean"]}]
    summary = json.loads(_run_scaffold(tmp_path, "render-critic-summary", {"critic_reviews": reviews}).stdout)["summary"]
    assert "| TASK-001 | auto_merged | clean |" in summary

    result = json.loads(_run_scaffold(tmp_path, "render-batch-result", {
        "order": ["TASK-001", "TASK-002"],
        "outcomes": [{"task_id": "TASK-001", "title": "t", "status": "done", "link": None}],
        "halt": {"task_id": "TASK-002", "kind": "critic_rejection", "reason": "criteria_met failed"},
    }).stdout)["summary"]
    assert "2 tasks" in result and "1 completed" in result and "TASK-002" in result and "critic_rejection" in result


def test_batch_clear_also_removes_a_leftover_auto_merge_marker(repo):
    _run_batch(repo, "batch-init", {"selection": _SELECTION, "order": _ORDER})
    marker = repo / _MARKER_REL
    marker.write_text("{}")

    result = _run_batch(repo, "batch-clear", {})

    assert result.returncode == 0, result.stderr
    assert not marker.exists() and not _batch_state_file(repo).exists()


def test_batch_update_completion_hands_back_the_critic_reviews_for_the_summary(repo):
    _run_batch(repo, "batch-init", {"selection": {"mode": "list", "tasks": ["TASK-001"]}, "order": ["TASK-001"]})
    state = json.loads(_batch_state_file(repo).read_text())
    state["critic_reviews"] = [{"task_id": "TASK-001", "outcome": "auto_merged", "findings": []}]
    _batch_state_file(repo).write_text(json.dumps(state))

    output = json.loads(_run_batch(repo, "batch-update", {"entry": _entry("TASK-001"), "accounted": True}).stdout)

    assert output["complete"] is True
    assert [r["task_id"] for r in output["critic_reviews"]] == ["TASK-001"]


def test_the_auto_merge_marker_never_counts_as_a_dirty_tree(repo):
    _add_task(repo, "First task")
    _push_tasks(repo)
    marker = repo / _MARKER_REL
    marker.parent.mkdir(exist_ok=True)
    marker.write_text("{}")

    assert _resume_state(repo)["phase"] == "phase1"
    assert _run_start(repo, task_id="TASK-001").returncode == 0
