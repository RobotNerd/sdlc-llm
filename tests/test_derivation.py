"""Unit tests for `.tasks/bin/sync`'s epic-status derivation and
blocked_by/blocks reconciliation (TASK-006).

Acceptance criteria this covers:
- derive_epic_status implements rules 1-7 in order, first match wins;
  hand-set wont-do is preserved
- the function is total: every row of SPEC-001's worked-cases table
  produces the documented result and (implicitly, via these cases) rule
- reconcile_blocks rewrites every blocks list from blocked_by, overwriting
  disagreements
- neither function writes files
- a blocked_by pointing at a missing task id raises, rather than being
  silently dropped
"""

from pathlib import Path

import pytest

from sync import Artifact, GraphError, derive_epic_status, reconcile_blocks


def make_epic(status: str = "todo") -> Artifact:
    fields = {"id": "EPIC-001", "title": "MVP", "status": status}
    return Artifact(id="EPIC-001", kind="epic", path=Path("EPIC-001.md"), fields=fields, order=list(fields), body="")


def make_task(task_id: str, status: str, blocked_by: list[str] | None = None) -> Artifact:
    fields = {"id": task_id, "status": status, "blocked_by": blocked_by or [], "blocks": []}
    return Artifact(id=task_id, kind="task", path=Path(f"{task_id}.md"), fields=fields, order=list(fields), body="")


# ---------------------------------------------------------------------------
# derive_epic_status — SPEC-001's worked-cases table, verbatim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "child_statuses,expected",
    [
        ([], "todo"),  # rule 2: no children
        (["todo"], "todo"),  # rule 2: all todo
        (["todo", "todo"], "todo"),  # rule 2
        (["todo", "in-progress"], "in-progress"),  # rule 3
        (["todo", "in-review"], "in-progress"),  # rule 3: in-review also counts as active
        (["blocked", "blocked"], "blocked"),  # rule 4
        (["wont-do", "wont-do"], "wont-do"),  # rule 5
        (["done", "wont-do"], "done"),  # rule 6
        (["done", "done"], "done"),  # rule 6
        (["todo", "done"], "in-progress"),  # rule 7: catch-all
        (["blocked", "done"], "in-progress"),  # rule 7: catch-all
        (["blocked", "wont-do"], "in-progress"),  # rule 7: catch-all
    ],
)
def test_derive_epic_status_worked_cases(child_statuses, expected):
    epic = make_epic(status="todo")
    children = [make_task(f"TASK-{i:03d}", status) for i, status in enumerate(child_statuses)]
    result = derive_epic_status(epic, children)
    assert result.fields["status"] == expected


def test_derive_epic_status_hand_set_wont_do_with_all_children_done():
    # the exact SPEC-001 worked-cases table row: "epic hand-set to wont-do,
    # children all done" -> wont-do (rule 1), not the rule-6 "done" that
    # the children alone would otherwise produce.
    epic = make_epic(status="wont-do")
    children = [make_task("TASK-001", "done"), make_task("TASK-002", "done")]
    assert derive_epic_status(epic, children).fields["status"] == "wont-do"


def test_derive_epic_status_hand_set_wont_do_is_preserved_even_with_active_children():
    epic = make_epic(status="wont-do")
    children = [make_task("TASK-001", "done"), make_task("TASK-002", "in-progress")]
    result = derive_epic_status(epic, children)
    assert result.fields["status"] == "wont-do"  # rule 1: human decision is sticky


def test_derive_epic_status_is_a_pure_function():
    epic = make_epic(status="todo")
    children = [make_task("TASK-001", "in-progress")]
    result = derive_epic_status(epic, children)
    assert epic.fields["status"] == "todo"  # original untouched
    assert result is not epic
    assert result.fields["status"] == "in-progress"  # rule 3


def test_derive_epic_status_single_done_child_is_rule_6_done():
    epic = make_epic(status="todo")
    result = derive_epic_status(epic, [make_task("TASK-001", "done")])
    assert result.fields["status"] == "done"


def test_derive_epic_status_preserves_other_epic_fields():
    epic = make_epic(status="todo")
    result = derive_epic_status(epic, [make_task("TASK-001", "done")])
    assert result.fields["id"] == "EPIC-001"
    assert result.fields["title"] == "MVP"
    assert result.id == "EPIC-001"
    assert result.path == epic.path


# ---------------------------------------------------------------------------
# reconcile_blocks
# ---------------------------------------------------------------------------


def test_reconcile_blocks_computes_the_exact_reverse_of_blocked_by():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
        "TASK-003": make_task("TASK-003", "todo", blocked_by=["TASK-001"]),
    }
    result = reconcile_blocks(tasks)
    assert result["TASK-001"].fields["blocks"] == ["TASK-002", "TASK-003"]
    assert result["TASK-002"].fields["blocks"] == []
    assert result["TASK-003"].fields["blocks"] == []


def test_reconcile_blocks_overwrites_a_disagreeing_pre_existing_blocks_list():
    tasks = {
        "TASK-001": Artifact(
            id="TASK-001", kind="task", path=Path("TASK-001.md"),
            fields={"id": "TASK-001", "status": "todo", "blocked_by": [], "blocks": ["TASK-999"]},
            order=["id", "status", "blocked_by", "blocks"], body="",
        ),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    result = reconcile_blocks(tasks)
    assert result["TASK-001"].fields["blocks"] == ["TASK-002"]  # TASK-999 discarded


def test_reconcile_blocks_output_is_sorted():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-010": make_task("TASK-010", "todo", blocked_by=["TASK-001"]),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    result = reconcile_blocks(tasks)
    assert result["TASK-001"].fields["blocks"] == ["TASK-002", "TASK-010"]


def test_reconcile_blocks_raises_on_dangling_blocked_by():
    tasks = {"TASK-001": make_task("TASK-001", "todo", blocked_by=["TASK-999"])}
    with pytest.raises(GraphError, match="TASK-999"):
        reconcile_blocks(tasks)


def test_reconcile_blocks_is_a_pure_function():
    tasks = {
        "TASK-001": make_task("TASK-001", "todo"),
        "TASK-002": make_task("TASK-002", "todo", blocked_by=["TASK-001"]),
    }
    reconcile_blocks(tasks)
    assert tasks["TASK-001"].fields["blocks"] == []  # originals untouched


def test_reconcile_blocks_handles_no_tasks():
    assert reconcile_blocks({}) == {}
