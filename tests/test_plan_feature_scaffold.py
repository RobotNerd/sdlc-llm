"""Unit/integration tests for `.claude/skills/plan-feature/scaffold.py` (TASK-026).

`find_cycle`/`render_spec_file`/`render_epic_file` are pure functions, tested directly with small
fixtures. `write-spec`/`write-epics`/`finish` are exercised as real subprocesses against a scratch
repo built by `init-project`'s own (already-tested) `scaffold.py`.
"""

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "plan-feature"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"
INIT_PROJECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "init-project" / "scaffold.py"
ADD_TASK_SCRIPT = REPO_ROOT / ".claude" / "skills" / "add-task" / "scaffold.py"
SPEC_TEMPLATE_TEXT = (REPO_ROOT / ".tasks" / "templates" / "spec.md").read_text()
EPIC_TEMPLATE_TEXT = (REPO_ROOT / ".tasks" / "templates" / "epic.md").read_text()

_loader = SourceFileLoader("plan_feature_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("plan_feature_scaffold", _loader)
plan_feature_scaffold = importlib.util.module_from_spec(_spec)
sys.modules["plan_feature_scaffold"] = plan_feature_scaffold
_loader.exec_module(plan_feature_scaffold)


# ---------------------------------------------------------------------------
# find_cycle
# ---------------------------------------------------------------------------


def test_find_cycle_returns_none_for_acyclic_graph():
    slices = [
        {"name": "A", "blocked_by": []},
        {"name": "B", "blocked_by": ["A"]},
        {"name": "C", "blocked_by": ["A", "B"]},
    ]
    assert plan_feature_scaffold.find_cycle(slices) is None


def test_find_cycle_flags_a_genuine_cycle():
    slices = [
        {"name": "A", "blocked_by": ["B"]},
        {"name": "B", "blocked_by": ["C"]},
        {"name": "C", "blocked_by": ["A"]},
    ]
    cycle = plan_feature_scaffold.find_cycle(slices)
    assert cycle is not None
    # the cycle closes back on its own starting node
    assert cycle[0] == cycle[-1]
    assert set(cycle) == {"A", "B", "C"}


def test_find_cycle_ignores_unrelated_acyclic_branch():
    slices = [
        {"name": "A", "blocked_by": []},
        {"name": "B", "blocked_by": ["A"]},
        {"name": "X", "blocked_by": ["Y"]},
        {"name": "Y", "blocked_by": ["X"]},
    ]
    cycle = plan_feature_scaffold.find_cycle(slices)
    assert cycle is not None
    assert set(cycle) == {"X", "Y"}


def test_find_cycle_handles_self_referential_slice():
    slices = [{"name": "A", "blocked_by": ["A"]}]
    cycle = plan_feature_scaffold.find_cycle(slices)
    assert cycle == ["A", "A"]


def test_find_cycle_no_slices():
    assert plan_feature_scaffold.find_cycle([]) is None


# ---------------------------------------------------------------------------
# render_spec_file
# ---------------------------------------------------------------------------


def test_render_spec_file_fills_every_placeholder_and_drops_comment():
    text = plan_feature_scaffold.render_spec_file(
        SPEC_TEMPLATE_TEXT,
        spec_id="SPEC-099",
        title="Sample feature",
        created="2026-09-15",
        problem="Users can't do X.",
        goals=["Let users do X", "Do it fast"],
        non_goals=["Support Y"],
        alternatives=["Do nothing", "Buy a third-party tool"],
    )

    assert not text.startswith("<!--")
    assert "{{" not in text
    assert "id: SPEC-099" in text
    assert "title: Sample feature" in text
    assert "created: 2026-09-15" in text
    assert "# SPEC-099: Sample feature" in text
    assert "Users can't do X." in text
    assert "- Let users do X" in text
    assert "- Do it fast" in text
    assert "- Support Y" in text
    assert "- Do nothing" in text
    assert "- Buy a third-party tool" in text
    assert "_(none)_" in text  # the generated `epics` region stays untouched


def test_render_spec_file_raises_on_missing_placeholder():
    broken_template = SPEC_TEMPLATE_TEXT.replace("{{problem}}", "already filled")
    with pytest.raises(ValueError, match="problem"):
        plan_feature_scaffold.render_spec_file(
            broken_template, spec_id="SPEC-099", title="X", created="2026-09-15",
            problem="Y", goals=["a"], non_goals=["b"], alternatives=["c"],
        )


# ---------------------------------------------------------------------------
# render_epic_file
# ---------------------------------------------------------------------------


def test_render_epic_file_fills_every_placeholder_including_shared_item_name():
    text = plan_feature_scaffold.render_epic_file(
        EPIC_TEMPLATE_TEXT,
        epic_id="EPIC-099",
        title="Sample epic",
        spec_id="SPEC-001",
        created="2026-09-15",
        goal="Ship the sample feature.",
        in_scope=["The API endpoint", "The stub UI"],
        out_of_scope=["Mobile support"],
        success_criteria=["Users can do X end to end"],
    )

    assert not text.startswith("<!--")
    assert "{{" not in text
    assert "id: EPIC-099" in text
    assert "spec: SPEC-001" in text
    assert "# EPIC-099: Sample epic" in text
    assert "Ship the sample feature." in text
    assert "- [ ] Users can do X end to end" in text

    # in_scope/out_of_scope share the `{{item}}` placeholder name in the template --
    # confirm they landed in the right section, not swapped or merged.
    in_scope_idx = text.index("## In scope")
    out_of_scope_idx = text.index("## Out of scope")
    success_idx = text.index("## Success criteria")
    assert in_scope_idx < text.index("The API endpoint") < out_of_scope_idx
    assert in_scope_idx < text.index("The stub UI") < out_of_scope_idx
    assert out_of_scope_idx < text.index("Mobile support") < success_idx


def test_render_epic_file_renders_null_spec():
    text = plan_feature_scaffold.render_epic_file(
        EPIC_TEMPLATE_TEXT, epic_id="EPIC-099", title="X", spec_id=None, created="2026-09-15",
        goal="g", in_scope=["a"], out_of_scope=["b"], success_criteria=["c"],
    )
    assert "spec: null" in text


def test_render_epic_file_raises_on_missing_placeholder():
    broken_template = EPIC_TEMPLATE_TEXT.replace("{{goal}}", "already filled")
    with pytest.raises(ValueError, match="goal"):
        plan_feature_scaffold.render_epic_file(
            broken_template, epic_id="EPIC-099", title="X", spec_id=None, created="2026-09-15",
            goal="g", in_scope=["a"], out_of_scope=["b"], success_criteria=["c"],
        )


# ---------------------------------------------------------------------------
# Integration: write-spec / write-epics / finish against a real scratch repo
# ---------------------------------------------------------------------------


INIT_PROJECT_ANSWERS = {
    "test_command": "pytest",
    "lint_command": None,
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


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
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


def _run(cwd, command, answers):
    answers_path = cwd.parent / f"{command}-answers.json"
    answers_path.write_text(json.dumps(answers))
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), command, str(answers_path)],
        cwd=cwd, capture_output=True, text=True,
    )


def _sync_check(cwd):
    return subprocess.run(
        [sys.executable, str(cwd / ".tasks" / "bin" / "sync"), "check"], cwd=cwd, capture_output=True, text=True
    )


def test_write_spec_creates_file_with_next_id(repo):
    result = _run(repo, "write-spec", {
        "title": "Sample feature", "created": "2026-09-15", "problem": "Users can't do X.",
        "goals": ["Let users do X"], "non_goals": ["Support Y"], "alternatives": ["Do nothing"],
    })
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["spec_id"] == "SPEC-001"
    spec_path = repo / output["path"]
    assert spec_path.exists()
    assert "{{" not in spec_path.read_text()


def test_write_epics_creates_multiple_epics_with_sequential_ids(repo):
    result = _run(repo, "write-epics", {
        "spec_id": "SPEC-001",
        "epics": [
            {
                "title": "First epic", "created": "2026-09-15", "goal": "g1",
                "in_scope": ["a"], "out_of_scope": ["b"], "success_criteria": ["c"],
            },
            {
                "title": "Second epic", "created": "2026-09-15", "goal": "g2",
                "in_scope": ["a"], "out_of_scope": ["b"], "success_criteria": ["c"],
            },
        ],
    })
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert [e["epic_id"] for e in output["epics"]] == ["EPIC-001", "EPIC-002"]
    for entry in output["epics"]:
        assert (repo / entry["path"]).exists()


def test_finish_reports_epic_appears_in_panel_and_children_populated(repo):
    write_epic = _run(repo, "write-epics", {
        "spec_id": None,
        "epics": [{
            "title": "Sample epic", "created": "2026-09-15", "goal": "g",
            "in_scope": ["a"], "out_of_scope": ["b"], "success_criteria": ["c"],
        }],
    })
    assert write_epic.returncode == 0, write_epic.stderr
    epic_id = json.loads(write_epic.stdout)["epics"][0]["epic_id"]

    # add-task's own scaffold isn't involved here -- hand-write a task linked to this
    # epic directly, since this test is about `finish`'s reporting, not task creation.
    task_text = (
        "---\nid: TASK-001\ntitle: Sample task\ntype: feature\nstatus: todo\n"
        f"epic: {epic_id}\ncreated: 2026-09-15\nbranch: task-001-sample-task\npr: null\n"
        "merge_commit: null\nblocked_by: []\nblocks: []\n---\n\n# TASK-001: Sample task\n"
    )
    (repo / ".tasks" / "TASK-001-sample-task.md").write_text(task_text)

    result = _run(repo, "finish", {"epic_ids": [epic_id]})

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["epics"] == [{"epic_id": epic_id, "in_epics_panel": True, "children_populated": True}]
    assert _sync_check(repo).returncode == 0


def test_finish_reports_epic_with_no_children_yet(repo):
    write_epic = _run(repo, "write-epics", {
        "spec_id": None,
        "epics": [{
            "title": "Empty epic", "created": "2026-09-15", "goal": "g",
            "in_scope": ["a"], "out_of_scope": ["b"], "success_criteria": ["c"],
        }],
    })
    epic_id = json.loads(write_epic.stdout)["epics"][0]["epic_id"]

    result = _run(repo, "finish", {"epic_ids": [epic_id]})

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["epics"] == [{"epic_id": epic_id, "in_epics_panel": True, "children_populated": False}]


def test_full_chain_spec_to_epic_to_fanned_out_tasks_to_finish(repo):
    """Same shape as TASK-018's own dry run: draft a spec, group into one epic, fan out
    to the real `add-task` skill for two dependent slices, then confirm `finish` sees a
    fully-populated epic and `sync check` stays clean throughout.
    """
    write_spec = _run(repo, "write-spec", {
        "title": "Sample feature", "created": "2026-09-15", "problem": "Users can't do X.",
        "goals": ["Let users do X"], "non_goals": ["Support Y"], "alternatives": ["Do nothing"],
    })
    assert write_spec.returncode == 0, write_spec.stderr
    spec_id = json.loads(write_spec.stdout)["spec_id"]

    cycles = _run(repo, "check-cycles", {"slices": [
        {"name": "slice-a", "blocked_by": []},
        {"name": "slice-b", "blocked_by": ["slice-a"]},
    ]})
    assert json.loads(cycles.stdout)["cycle"] is None

    write_epic = _run(repo, "write-epics", {
        "spec_id": spec_id,
        "epics": [{
            "title": "Sample epic", "created": "2026-09-15", "goal": "Ship the sample feature.",
            "in_scope": ["Slice A", "Slice B"], "out_of_scope": ["Mobile"],
            "success_criteria": ["Both slices ship"],
        }],
    })
    assert write_epic.returncode == 0, write_epic.stderr
    epic_id = json.loads(write_epic.stdout)["epics"][0]["epic_id"]

    def _add_task(title, blocked_by=None):
        answers = {
            "title": title, "type": "feature", "epic": epic_id,
            "blocked_by": blocked_by or [], "priority_mode": "end",
        }
        answers_path = repo.parent / "add-task-answers.json"
        answers_path.write_text(json.dumps(answers))
        result = subprocess.run(
            [sys.executable, str(ADD_TASK_SCRIPT), "run", str(answers_path)],
            cwd=repo, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

    _add_task("Slice A")
    _add_task("Slice B", blocked_by=["TASK-001"])

    finish = _run(repo, "finish", {"epic_ids": [epic_id]})
    assert finish.returncode == 0, finish.stderr
    output = json.loads(finish.stdout)
    assert output["epics"] == [{"epic_id": epic_id, "in_epics_panel": True, "children_populated": True}]

    # sync reconciles blocks from blocked_by automatically -- confirms the dependency
    # graph came out acyclic by construction, matching TASK-018's own precedent.
    task_a = (repo / ".tasks" / "TASK-001-slice-a.md").read_text()
    assert "blocks: [TASK-002]" in task_a
    assert _sync_check(repo).returncode == 0


def test_check_cycles_subcommand_wiring(repo):
    result = _run(repo, "check-cycles", {"slices": [
        {"name": "A", "blocked_by": ["B"]},
        {"name": "B", "blocked_by": ["A"]},
    ]})
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["cycle"] is not None
