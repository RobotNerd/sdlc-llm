"""The pure logic behind `implement-task`'s opt-in, critic-gated, capped auto-merge (TASK-045):
the critic's prompt and its strictly fail-closed verdict parsing, the deterministic gate order, the
per-batch merge cap, and the reporting helpers. No git/gh -- the CLI wiring and the marker/hook
side live in `test_implement_task_scaffold.py` and `test_auto_merge_guardrail.py`.
"""

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / ".claude" / "skills" / "implement-task" / "scaffold.py"

_loader = SourceFileLoader("implement_task_scaffold_am", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("implement_task_scaffold_am", _loader)
scaffold = importlib.util.module_from_spec(_spec)
sys.modules["implement_task_scaffold_am"] = scaffold
_loader.exec_module(scaffold)

ALL_TRUE = {"criteria_met": True, "scope_ok": True, "gates_passed": True, "nothing_alarming": True}


def _verdict(approve=True, findings=None, **overrides):
    return json.dumps({"approve": approve, **{**ALL_TRUE, **overrides}, "findings": findings or []})


# ---------------------------------------------------------------------------
# the critic's prompt -- narrow and checklist-style, not an open-ended review
# ---------------------------------------------------------------------------


def _prompt(**overrides):
    kwargs = dict(
        task_id="TASK-045", title="Auto-merge", head_sha="abc1234",
        acceptance_criteria="- [x] first criterion\n- [x] second criterion",
        changed_files=["src/a.py", "tests/test_a.py"], scope_paths=["src/a.py", "tests/test_a.py"],
        gates="pytest: pass (10 passed)\nsync check: exit 0", diff="diff --git a/src/a.py b/src/a.py\n+x = 1\n",
    )
    kwargs.update(overrides)
    return scaffold.build_critic_prompt(**kwargs)


def test_critic_prompt_carries_everything_the_checklist_needs():
    text = _prompt()

    for needle in ("TASK-045", "abc1234", "first criterion", "second criterion", "src/a.py",
                   "tests/test_a.py", "pytest: pass", "+x = 1"):
        assert needle in text, needle


def test_critic_prompt_asks_for_exactly_the_four_checklist_items_as_json():
    text = _prompt()

    for key in ("criteria_met", "scope_ok", "gates_passed", "nothing_alarming", "approve", "findings"):
        assert key in text, key
    assert "JSON" in text


def test_critic_prompt_is_scoped_not_an_open_ended_review():
    text = _prompt().lower()

    assert "not" in text and "code-quality" in text or "not a general code review" in text
    assert "reject" in text  # tells the critic to reject when it can't verify


def test_critic_prompt_truncates_a_huge_diff_and_says_so():
    text = _prompt(diff="x" * (scaffold.CRITIC_MAX_DIFF_CHARS + 5000))

    assert "truncated" in text.lower()
    assert len(text) < scaffold.CRITIC_MAX_DIFF_CHARS + 6000


# ---------------------------------------------------------------------------
# the verdict -- fails closed
# ---------------------------------------------------------------------------


def test_verdict_approves_only_when_approve_and_every_item_is_true():
    result = scaffold.evaluate_critic_verdict(_verdict(findings=["looks fine"]))

    assert result["approve"] is True
    assert result["findings"] == ["looks fine"]
    assert result["checklist"] == ALL_TRUE
    assert result["reason"] is None


def test_verdict_accepts_a_fenced_json_block_or_json_amid_prose():
    fenced = f"Here is my verdict:\n```json\n{_verdict()}\n```\n"
    prose = f"Sure. {_verdict()} Hope that helps."

    assert scaffold.evaluate_critic_verdict(fenced)["approve"] is True
    assert scaffold.evaluate_critic_verdict(prose)["approve"] is True


def test_verdict_rejects_an_explicit_no_and_keeps_the_findings():
    result = scaffold.evaluate_critic_verdict(_verdict(approve=False, criteria_met=False, findings=["AC 2 unmet"]))

    assert result["approve"] is False
    assert result["findings"] == ["AC 2 unmet"]
    assert "criteria_met" in result["reason"]


@pytest.mark.parametrize("item", ["criteria_met", "scope_ok", "gates_passed", "nothing_alarming"])
def test_verdict_rejects_when_any_single_checklist_item_fails_even_if_approve_is_true(item):
    result = scaffold.evaluate_critic_verdict(_verdict(approve=True, **{item: False}))

    assert result["approve"] is False
    assert item in result["reason"]


@pytest.mark.parametrize("text", [
    "", "looks good to me!", "{not json", "[]", "null", "42",
    json.dumps({"approve": True}),                                   # checklist missing
    json.dumps({"approve": "true", **ALL_TRUE, "findings": []}),     # not a real boolean
    json.dumps({"approve": True, **{**ALL_TRUE, "scope_ok": "yes"}, "findings": []}),
    json.dumps({"approve": True, **ALL_TRUE, "findings": "fine"}),   # findings not a list
    json.dumps({"approve": True, **ALL_TRUE}),                       # findings missing
])
def test_verdict_rejects_anything_unparseable_or_malformed(text):
    result = scaffold.evaluate_critic_verdict(text)

    assert result["approve"] is False
    assert result["reason"]


def test_verdict_accepts_a_pre_parsed_object():
    assert scaffold.evaluate_critic_verdict(json.loads(_verdict()))["approve"] is True


# ---------------------------------------------------------------------------
# deterministic helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("returncode,state", [(0, "green"), (8, "pending"), (1, "not_green"), (2, "not_green")])
def test_pr_checks_state(returncode, state):
    assert scaffold.pr_checks_state(returncode) == state


def test_scope_violations_allows_declared_paths_and_tasks_bookkeeping_only():
    changed = ["src/a.py", ".tasks/BOARD.md", ".tasks/archive/TASK-001-x.md", "docs/extra.md", "src/other.py"]

    assert scaffold.scope_violations(changed, scope_paths=["src/a.py"]) == ["docs/extra.md", "src/other.py"]


def test_scope_violations_none_when_everything_is_in_scope():
    assert scaffold.scope_violations(["src/a.py", ".tasks/TASK-045-x.md"], scope_paths=["src/a.py"]) == []


@pytest.mark.parametrize("merged,cap,allowed", [
    (0, 5, True), (4, 5, True), (5, 5, False), (9, 5, False), (0, 0, False), (0, None, True), (999, None, True),
])
def test_check_merge_cap(merged, cap, allowed):
    result = scaffold.check_merge_cap(merged=merged, cap=cap)

    assert result["allowed"] is allowed
    assert (result["message"] is None) is allowed


@pytest.mark.parametrize("bad", ["5", -1, 1.5, True])
def test_check_merge_cap_rejects_a_bad_cap_loudly(bad):
    with pytest.raises(ValueError, match="autonomous_merge_cap"):
        scaffold.check_merge_cap(merged=0, cap=bad)


def _gates(**overrides):
    kwargs = dict(allow_auto_merge=True, cap_allowed=True, checks_state="green", scope_violations=[], verdict_approve=True)
    kwargs.update(overrides)
    return scaffold.evaluate_auto_merge_gates(**kwargs)


def test_all_gates_green_proceeds():
    assert _gates() == {"proceed": True, "reason": None, "halt": False}


@pytest.mark.parametrize("overrides,reason,halt", [
    ({"allow_auto_merge": False}, "disabled", False),
    ({"allow_auto_merge": None}, "disabled", False),
    ({"cap_allowed": False}, "cap_reached", True),
    ({"checks_state": "pending"}, "checks_pending", False),
    ({"checks_state": "not_green"}, "checks_not_green", False),
    ({"scope_violations": ["x.py"]}, "scope_violation", False),
    ({"verdict_approve": False}, "critic_rejected", False),
])
def test_each_gate_blocks_with_its_own_reason(overrides, reason, halt):
    assert _gates(**overrides) == {"proceed": False, "reason": reason, "halt": halt}


def test_gate_priority_disabled_first_then_cap_regardless_of_the_critic():
    assert _gates(allow_auto_merge=False, cap_allowed=False, verdict_approve=False)["reason"] == "disabled"
    # at the cap, a human checkpoint is forced even though the critic approved and CI is green
    assert _gates(cap_allowed=False, verdict_approve=True, checks_state="green")["reason"] == "cap_reached"
    assert _gates(cap_allowed=False, checks_state="pending")["reason"] == "cap_reached"


def test_gate_priority_checks_before_scope_before_critic():
    assert _gates(checks_state="pending", scope_violations=["x"], verdict_approve=False)["reason"] == "checks_pending"
    assert _gates(scope_violations=["x"], verdict_approve=False)["reason"] == "scope_violation"


# ---------------------------------------------------------------------------
# interrupt routing -- two new kinds
# ---------------------------------------------------------------------------


def test_critic_rejection_bails_out_the_task_and_ends_the_batch():
    assert scaffold.interrupt_routing("critic_rejection") == {"routing": "bail_out_halt", "continue_batch": False}


def test_auto_merge_cap_reached_is_a_systemic_halt():
    assert scaffold.interrupt_routing("auto_merge_cap_reached") == {"routing": "systemic", "continue_batch": False}


def test_existing_interrupt_routing_is_unchanged():
    assert scaffold.interrupt_routing("needs_clarification") == {"routing": "isolated", "continue_batch": True}
    assert scaffold.interrupt_routing("infra_failure") == {"routing": "systemic", "continue_batch": False}


# ---------------------------------------------------------------------------
# the ledger and the reporting
# ---------------------------------------------------------------------------


def _review(task_id, outcome, approve=True, findings=None):
    return {"task_id": task_id, "pr": 1, "head_sha": "abc1234", "approve": approve,
            "findings": findings or [], "checklist": ALL_TRUE, "outcome": outcome}


def test_record_critic_review_appends_without_mutating_and_counts_only_auto_merged():
    state = scaffold.new_batch_state({"mode": "list"}, ["TASK-001", "TASK-002"])

    state2 = scaffold.record_critic_review(state, _review("TASK-001", "auto_merged"))
    state3 = scaffold.record_critic_review(state2, _review("TASK-002", "critic_rejected", approve=False))

    assert state["critic_reviews"] == []
    assert scaffold.count_auto_merged(state3) == 1
    assert scaffold.batch_progress(state3)["critic_reviews"] == state3["critic_reviews"]


def test_read_batch_state_tolerates_a_file_without_critic_reviews(tmp_path):
    path = scaffold.batch_state_path(tmp_path)
    path.parent.mkdir()
    path.write_text(json.dumps({"selection": {}, "order": ["TASK-001"], "accounted": [], "outcomes": []}))

    assert scaffold.read_batch_state(path)["critic_reviews"] == []


def test_render_critic_summary_lists_every_reviewed_task_with_findings():
    text = scaffold.render_critic_summary([
        _review("TASK-001", "auto_merged", findings=["clean"]),
        _review("TASK-002", "critic_rejected", approve=False, findings=["AC 2 unmet"]),
        _review("TASK-003", "skipped:scope_violation", approve=True),
    ])

    assert "| TASK-001 | auto_merged |" in text and "clean" in text
    assert "| TASK-002 | critic_rejected |" in text and "AC 2 unmet" in text
    assert "TASK-003" in text and "scope_violation" in text


def test_render_critic_summary_when_none():
    assert "none" in scaffold.render_critic_summary([]).lower()


def _outcomes(*pairs):
    return [{"task_id": t, "title": f"Title {t}", "status": s, "link": None} for t, s in pairs]


def test_render_batch_result_when_every_task_completed():
    text = scaffold.render_batch_result(
        order=["TASK-001", "TASK-002"], outcomes=_outcomes(("TASK-001", "done"), ("TASK-002", "done")), halt=None,
    )

    assert "2 tasks" in text and "2 completed" in text
    assert "ended early" not in text.lower()


def test_render_batch_result_names_the_task_that_ended_the_batch_and_what_never_started():
    text = scaffold.render_batch_result(
        order=["TASK-001", "TASK-002", "TASK-003", "TASK-004"],
        outcomes=_outcomes(("TASK-001", "done"), ("TASK-002", "todo (critic rejected)")),
        halt={"task_id": "TASK-002", "kind": "critic_rejection", "reason": "criteria_met failed: AC 2 unmet"},
    )

    assert "4 tasks" in text
    assert "1 completed" in text
    assert "ended early" in text.lower()
    assert "TASK-002" in text and "critic_rejection" in text and "AC 2 unmet" in text
    assert "TASK-003" in text and "TASK-004" in text  # never started


def test_scaffold_and_guardrails_agree_on_the_marker_path():
    import guardrails

    assert scaffold.AUTO_MERGE_MARKER_RELPATH == guardrails.AUTO_MERGE_MARKER_RELPATH
