"""Unit/integration tests for `.claude/skills/implement-task/batch_select.py` (TASK-039).

The per-mode resolvers and `validate_and_order`/`select_batch` are pure functions of an
in-memory `tasks: dict[str, Artifact]` (plus a `board_text` string for the "stopping" mode) --
tested directly against hand-built fixtures, the same style `tests/test_derivation.py` uses for
`sync`'s own pure functions. The `select` CLI subcommand is additionally exercised as a real
subprocess against a small hand-authored `.tasks/` tree in a scratch git repo (mirroring
`tests/fixtures/mini_repo`'s conventions), since that's the only way to prove the JSON-file-in,
JSON-stdout-out, non-zero-exit-on-refusal wiring actually works end to end.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from sync import Artifact
import sync as sync_mod

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "implement-task"
SCRIPT_PATH = SKILL_DIR / "batch_select.py"

_loader = SourceFileLoader("batch_select", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("batch_select", _loader)
batch_select = importlib.util.module_from_spec(_spec)
sys.modules["batch_select"] = batch_select
_loader.exec_module(batch_select)

BatchSelectionError = batch_select.BatchSelectionError


# ---------------------------------------------------------------------------
# Fixture builders -- same shape as test_derivation.py's make_epic/make_task
# ---------------------------------------------------------------------------


def make_epic(epic_id: str = "EPIC-001", status: str = "todo") -> Artifact:
    fields = {"id": epic_id, "title": "Fixture epic", "spec": "SPEC-001", "status": status}
    return Artifact(id=epic_id, kind="epic", path=Path(f"{epic_id}.md"), fields=fields, order=list(fields), body="")


def make_task(task_id: str, status: str, epic: str | None = None, blocked_by: list[str] | None = None) -> Artifact:
    fields = {
        "id": task_id, "title": f"Title of {task_id}", "type": "feature", "status": status,
        "epic": epic, "blocked_by": blocked_by or [], "blocks": [],
    }
    return Artifact(id=task_id, kind="task", path=Path(f"{task_id}.md"), fields=fields, order=list(fields), body="")


def todo_board_text(task_ids: list[str]) -> str:
    lines = "\n".join(f"- {tid} — Title of {tid}" for tid in task_ids)
    return f"# Board\n\n## TODO\n\n{lines}\n\n## In Progress\n\n_(none)_\n"


# ---------------------------------------------------------------------------
# resolve_epic
# ---------------------------------------------------------------------------


def test_resolve_epic_returns_non_terminal_children_in_ascending_id_order():
    tasks = {
        "EPIC-001": make_epic(),
        "TASK-003": make_task("TASK-003", "todo", epic="EPIC-001"),
        "TASK-001": make_task("TASK-001", "in-progress", epic="EPIC-001"),
        "TASK-002": make_task("TASK-002", "done", epic="EPIC-001"),  # excluded
        "TASK-004": make_task("TASK-004", "wont-do", epic="EPIC-001"),  # excluded
        "TASK-005": make_task("TASK-005", "todo", epic="EPIC-002"),  # different epic
    }
    assert batch_select.resolve_epic("EPIC-001", tasks) == ["TASK-001", "TASK-003"]


def test_resolve_epic_no_such_epic_raises():
    tasks = {"TASK-001": make_task("TASK-001", "todo")}
    with pytest.raises(BatchSelectionError, match="no such epic"):
        batch_select.resolve_epic("EPIC-999", tasks)


def test_resolve_epic_wrong_kind_raises():
    tasks = {"EPIC-001": make_task("EPIC-001", "todo")}  # a task id masquerading as an epic id
    with pytest.raises(BatchSelectionError, match="no such epic"):
        batch_select.resolve_epic("EPIC-001", tasks)


# ---------------------------------------------------------------------------
# resolve_range
# ---------------------------------------------------------------------------


def test_resolve_range_slices_the_board_order_not_numeric_id_order():
    # TASK-034 is *higher* priority (listed first) than TASK-032 here -- board order, not id
    # order, is what must win.
    board_text = todo_board_text(["TASK-034", "TASK-005", "TASK-032"])
    assert batch_select.resolve_range("TASK-034..TASK-032", board_text, sync_mod) == [
        "TASK-034", "TASK-005", "TASK-032",
    ]


def test_resolve_range_single_task_slice_when_endpoints_are_equal():
    board_text = todo_board_text(["TASK-001", "TASK-002", "TASK-003"])
    assert batch_select.resolve_range("TASK-002..TASK-002", board_text, sync_mod) == ["TASK-002"]


def test_resolve_range_includes_a_blocked_marked_line_as_is():
    board_text = "# Board\n\n## TODO\n\n- TASK-001 — a\n- TASK-002 — b ⛔ blocked_by TASK-999\n- TASK-003 — c\n"
    assert batch_select.resolve_range("TASK-001..TASK-003", board_text, sync_mod) == [
        "TASK-001", "TASK-002", "TASK-003",
    ]


def test_resolve_range_backwards_relative_to_board_order_raises():
    # TASK-002 is listed *before* TASK-001 on the board -- calling it 001..002 is backwards.
    board_text = todo_board_text(["TASK-002", "TASK-001"])
    with pytest.raises(BatchSelectionError, match="backwards on the board"):
        batch_select.resolve_range("TASK-001..TASK-002", board_text, sync_mod)


@pytest.mark.parametrize(
    "range_str,missing", [("TASK-999..TASK-002", "TASK-999"), ("TASK-001..TASK-999", "TASK-999")],
    ids=["start-missing", "end-missing"],
)
def test_resolve_range_endpoint_not_on_todo_list_raises(range_str, missing):
    board_text = todo_board_text(["TASK-001", "TASK-002"])
    with pytest.raises(BatchSelectionError, match=f"{missing} is not on the TODO list"):
        batch_select.resolve_range(range_str, board_text, sync_mod)


@pytest.mark.parametrize(
    "range_str", ["garbage", "TASK-abc..TASK-005", "TASK-005"],
    ids=["not-a-range", "non-numeric", "single-id"],
)
def test_resolve_range_malformed_raises(range_str):
    with pytest.raises(BatchSelectionError):
        batch_select.resolve_range(range_str, todo_board_text(["TASK-005"]), sync_mod)


# ---------------------------------------------------------------------------
# resolve_list
# ---------------------------------------------------------------------------


def test_resolve_list_is_a_verbatim_passthrough():
    assert batch_select.resolve_list(["TASK-005", "TASK-001", "TASK-003"]) == ["TASK-005", "TASK-001", "TASK-003"]


# ---------------------------------------------------------------------------
# resolve_stopping
# ---------------------------------------------------------------------------


def test_resolve_stopping_slices_through_the_named_task_inclusive():
    board_text = todo_board_text(["TASK-005", "TASK-002", "TASK-009"])
    result = batch_select.resolve_stopping("TASK-002", board_text, sync_mod)
    assert result == ["TASK-005", "TASK-002"]


def test_resolve_stopping_task_not_on_todo_list_raises():
    board_text = todo_board_text(["TASK-005", "TASK-009"])
    with pytest.raises(BatchSelectionError, match="not on the TODO list"):
        batch_select.resolve_stopping("TASK-002", board_text, sync_mod)


def test_resolve_stopping_missing_heading_raises():
    with pytest.raises(BatchSelectionError, match="TODO"):
        batch_select.resolve_stopping("TASK-002", "# Board\n\nnothing here\n", sync_mod)


# ---------------------------------------------------------------------------
# validate_and_order
# ---------------------------------------------------------------------------


def test_validate_and_order_no_blockers_returns_the_same_order():
    tasks = {"TASK-001": make_task("TASK-001", "todo"), "TASK-002": make_task("TASK-002", "todo")}
    assert batch_select.validate_and_order(["TASK-001", "TASK-002"], tasks, sync_mod) == ["TASK-001", "TASK-002"]


def test_validate_and_order_empty_selection_raises():
    with pytest.raises(BatchSelectionError, match="zero tasks"):
        batch_select.validate_and_order([], {}, sync_mod)


def test_validate_and_order_nonexistent_task_raises():
    with pytest.raises(BatchSelectionError, match="TASK-001 does not exist"):
        batch_select.validate_and_order(["TASK-001"], {}, sync_mod)


@pytest.mark.parametrize("status", ["blocked", "done", "wont-do"])
def test_validate_and_order_ineligible_status_raises(status):
    tasks = {"TASK-001": make_task("TASK-001", status)}
    with pytest.raises(BatchSelectionError, match="not eligible"):
        batch_select.validate_and_order(["TASK-001"], tasks, sync_mod)


@pytest.mark.parametrize("status", ["todo", "in-progress", "in-review"])
def test_validate_and_order_accepts_every_selectable_status(status):
    tasks = {"TASK-001": make_task("TASK-001", status)}
    assert batch_select.validate_and_order(["TASK-001"], tasks, sync_mod) == ["TASK-001"]


def test_validate_and_order_blocker_already_done_is_satisfied():
    tasks = {
        "TASK-001": make_task("TASK-001", "done"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    assert batch_select.validate_and_order(["TASK-002"], tasks, sync_mod) == ["TASK-002"]


def test_validate_and_order_blocker_inside_set_correctly_ordered_is_fine():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    assert batch_select.validate_and_order(["TASK-001", "TASK-002"], tasks, sync_mod) == ["TASK-001", "TASK-002"]


def test_validate_and_order_blocker_inside_set_but_ordered_after_raises():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    with pytest.raises(BatchSelectionError, match="TASK-002 is ordered before its blocker TASK-001"):
        batch_select.validate_and_order(["TASK-002", "TASK-001"], tasks, sync_mod)


def test_validate_and_order_blocker_outside_set_and_unresolved_raises():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    with pytest.raises(BatchSelectionError, match="TASK-002 is blocked by TASK-001.*outside the selection"):
        batch_select.validate_and_order(["TASK-002"], tasks, sync_mod)


def test_validate_and_order_missing_blocker_artifact_treated_as_outstanding_and_external():
    # `_outstanding_blockers` conservatively treats a `blocked_by` id with no matching task as
    # still outstanding -- confirms that flows through as an external-blocker refusal here too.
    tasks = {"TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-999"])}
    with pytest.raises(BatchSelectionError, match="TASK-002 is blocked by TASK-999"):
        batch_select.validate_and_order(["TASK-002"], tasks, sync_mod)


# ---------------------------------------------------------------------------
# select_batch -- mode dispatch, end to end over the pure functions
# ---------------------------------------------------------------------------


def test_select_batch_epic_mode():
    tasks = {
        "EPIC-001": make_epic(),
        "TASK-001": make_task("TASK-001", "todo", epic="EPIC-001"),
        "TASK-002": make_task("TASK-002", "todo", epic="EPIC-001", blocked_by=["TASK-001"]),
    }
    order = batch_select.select_batch({"mode": "epic", "epic": "EPIC-001"}, tasks, "", sync_mod)
    assert order == ["TASK-001", "TASK-002"]


def test_select_batch_range_mode():
    # Board order (TASK-003 listed before TASK-001) deliberately diverges from numeric id
    # order here -- proves select_batch's range dispatch follows the board, not the ids.
    tasks = {f"TASK-{n:03d}": make_task(f"TASK-{n:03d}", "todo") for n in (1, 2, 3)}
    board_text = todo_board_text(["TASK-003", "TASK-002", "TASK-001"])
    order = batch_select.select_batch({"mode": "range", "range": "TASK-003..TASK-001"}, tasks, board_text, sync_mod)
    assert order == ["TASK-003", "TASK-002", "TASK-001"]


def test_select_batch_list_mode():
    tasks = {"TASK-002": make_task("TASK-002", "todo"), "TASK-001": make_task("TASK-001", "todo")}
    order = batch_select.select_batch({"mode": "list", "tasks": ["TASK-002", "TASK-001"]}, tasks, "", sync_mod)
    assert order == ["TASK-002", "TASK-001"]  # given order preserved, not id-sorted


def test_select_batch_stopping_mode():
    tasks = {"TASK-001": make_task("TASK-001", "todo"), "TASK-002": make_task("TASK-002", "todo")}
    board_text = todo_board_text(["TASK-001", "TASK-002"])
    order = batch_select.select_batch({"mode": "stopping", "stopping_task": "TASK-002"}, tasks, board_text, sync_mod)
    assert order == ["TASK-001", "TASK-002"]


def test_select_batch_unknown_mode_raises():
    with pytest.raises(BatchSelectionError, match="unknown mode"):
        batch_select.select_batch({"mode": "bogus"}, {}, "", sync_mod)


def test_select_batch_missing_mode_param_raises_key_error():
    with pytest.raises(KeyError):
        batch_select.select_batch({"mode": "epic"}, {}, "", sync_mod)  # no "epic" key


# ---------------------------------------------------------------------------
# `select` CLI subcommand -- a real subprocess against a hand-authored `.tasks/` tree
# ---------------------------------------------------------------------------


def _init_fixture_repo(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
    (work / ".tasks" / "bin").mkdir(parents=True)
    shutil.copy(REPO_ROOT / ".tasks" / "bin" / "sync", work / ".tasks" / "bin" / "sync")
    return work


def _write_task(work: Path, task_id: str, status: str, blocked_by: list[str] | None = None) -> None:
    blocked = json.dumps(blocked_by or [])
    (work / ".tasks" / f"{task_id}-x.md").write_text(
        f"---\n"
        f"id: {task_id}\n"
        f"title: Title of {task_id}\n"
        f"type: feature\n"
        f"status: {status}\n"
        f"epic: null\n"
        f"created: 2026-01-01\n"
        f"branch: null\n"
        f"pr: null\n"
        f"merge_commit: null\n"
        f"blocked_by: {blocked}\n"
        f"blocks: []\n"
        f"---\n\nBody.\n"
    )


def _run_cli(work: Path, answers: dict) -> subprocess.CompletedProcess:
    answers_path = work / "answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "select", str(answers_path)],
        cwd=work, capture_output=True, text=True,
    )


def test_cli_select_list_mode_happy_path(tmp_path):
    work = _init_fixture_repo(tmp_path)
    _write_task(work, "TASK-001", "todo")
    _write_task(work, "TASK-002", "todo", blocked_by=["TASK-001"])
    (work / ".tasks" / "BOARD.md").write_text(todo_board_text(["TASK-001", "TASK-002"]))

    result = _run_cli(work, {"mode": "list", "tasks": ["TASK-001", "TASK-002"]})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"order": ["TASK-001", "TASK-002"]}


def test_cli_select_invalid_selection_exits_nonzero_with_a_clear_message(tmp_path):
    work = _init_fixture_repo(tmp_path)
    _write_task(work, "TASK-001", "todo")
    _write_task(work, "TASK-002", "todo", blocked_by=["TASK-001"])
    (work / ".tasks" / "BOARD.md").write_text(todo_board_text(["TASK-001", "TASK-002"]))

    # TASK-001 (the blocker) is left out of the selection entirely, and isn't done/wont-do.
    result = _run_cli(work, {"mode": "list", "tasks": ["TASK-002"]})

    assert result.returncode != 0
    assert "TASK-002" in result.stderr
    assert "TASK-001" in result.stderr
    assert "outside the selection" in result.stderr


def test_cli_select_epic_mode_end_to_end(tmp_path):
    work = _init_fixture_repo(tmp_path)
    (work / ".tasks" / "EPIC-001-x.md").write_text(
        "---\nid: EPIC-001\ntitle: Fixture epic\nspec: SPEC-001\nstatus: todo\n---\n\nBody.\n"
    )
    for task_id, status in (("TASK-001", "todo"), ("TASK-002", "done")):
        (work / ".tasks" / f"{task_id}-x.md").write_text(
            f"---\nid: {task_id}\ntitle: Title of {task_id}\ntype: feature\nstatus: {status}\n"
            f"epic: EPIC-001\ncreated: 2026-01-01\nbranch: null\npr: null\nmerge_commit: null\n"
            f"blocked_by: []\nblocks: []\n---\n\nBody.\n"
        )
    (work / ".tasks" / "BOARD.md").write_text(todo_board_text(["TASK-001"]))

    result = _run_cli(work, {"mode": "epic", "epic": "EPIC-001"})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"order": ["TASK-001"]}  # TASK-002 (done) excluded


def test_cli_select_range_mode_follows_board_order_not_numeric_id_order(tmp_path):
    work = _init_fixture_repo(tmp_path)
    for task_id in ("TASK-001", "TASK-002", "TASK-003"):
        _write_task(work, task_id, "todo")
    # TASK-003 outranks TASK-001 on the board -- the opposite of numeric id order.
    (work / ".tasks" / "BOARD.md").write_text(todo_board_text(["TASK-003", "TASK-002", "TASK-001"]))

    result = _run_cli(work, {"mode": "range", "range": "TASK-003..TASK-001"})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"order": ["TASK-003", "TASK-002", "TASK-001"]}
