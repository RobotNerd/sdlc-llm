"""setup.py provision: the Kaneo project and the Outline collection, created only where missing."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend_fakes import FakeKaneo, FakeOutline

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "skills/setup-project/scripts/setup.py"
WORKSPACE = "workspace1"
FAKE_KEYS = {"KANEO_API_KEY": "fake-kaneo-key", "OUTLINE_API_KEY": "fake-outline-key"}
COLUMNS = ["to-do", "in-progress", "needs-human", "done"]
LABELS = {"bug", "chore", "deferred", "docs", "epic", "feature", "follow-up", "refactor", "wont-do"}
STRUCTURE = {"docs", "docs/guidelines", "reports", "reports/batches", "reports/epics", "spec"}
GUIDELINES = {"Documentation style", "Review policy", "Task style guide", "Testing strategy"}


@pytest.fixture
def backends():
    kaneo, outline = FakeKaneo(), FakeOutline()
    yield kaneo, outline
    kaneo.close()
    outline.close()


def make_repo(tmp_path, plugin=False):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    if plugin:
        (repo / ".claude-plugin").mkdir()
        (repo / ".claude-plugin/plugin.json").write_text('{"name": "example"}')
    return repo


def run_provision(repo, kaneo, outline):
    values = repo.parent / "values.json"
    values.write_text(json.dumps({
        "kaneo": {"project_name": "Example", "project_slug": "EX", "url": kaneo.url, "workspace_id": WORKSPACE},
        "outline": {"collection_name": "example", "url": outline.url},
    }))
    environment = {name: value for name, value in os.environ.items() if name not in FAKE_KEYS}
    environment.update(FAKE_KEYS)
    return subprocess.run(
        [sys.executable, str(SETUP), "provision", str(values)],
        capture_output=True,
        cwd=repo,
        env=environment,
        text=True,
        timeout=60,
    )


def documents_by_path(outline, collection_id):
    paths = {}

    def walk(nodes, prefix):
        for node in nodes:
            path = f"{prefix}{node['title']}"
            paths[path] = next(document for document in outline.documents if document["id"] == node["id"])
            walk(node["children"], f"{path}/")

    walk(outline.tree(collection_id), "")
    return paths


def test_everything_is_created_and_ids_are_printed_when_backends_are_empty(tmp_path, backends):
    kaneo, outline = backends

    result = run_provision(make_repo(tmp_path), kaneo, outline)

    assert result.returncode == 0, result.stderr
    ids = json.loads(result.stdout)
    project = kaneo.projects[0]
    assert (project["slug"], project["name"]) == ("EX", "Example")
    assert ids["kaneo"]["project_id"] == project["id"]
    columns = sorted(kaneo.columns[project["id"]], key=lambda column: column["position"])
    assert [column["slug"] for column in columns][: len(COLUMNS)] == COLUMNS
    assert [column["slug"] for column in columns if column["isFinal"]] == ["done"]
    assert set(ids["kaneo"]["columns"]) == set(COLUMNS)
    assert {label["name"] for label in kaneo.labels} == LABELS
    assert set(ids["kaneo"]["labels"]) == LABELS
    assert ids["outline"]["collection_id"] == outline.collections[0]["id"]
    paths = documents_by_path(outline, outline.collections[0]["id"])
    assert set(paths) == STRUCTURE | {f"docs/guidelines/{title}" for title in GUIDELINES}
    assert set(ids["outline"]["guidelines"]) == GUIDELINES
    for request in kaneo.requests + outline.requests:
        assert request["headers"]["Authorization"].startswith("Bearer fake-")


def test_no_writes_are_made_when_provision_runs_again(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)
    first = run_provision(repo, kaneo, outline)
    kaneo.requests.clear()
    outline.requests.clear()

    second = run_provision(repo, kaneo, outline)

    assert second.returncode == 0, second.stderr
    assert kaneo.writes() == []
    assert outline.writes() == []
    assert json.loads(second.stdout)["kaneo"] == json.loads(first.stdout)["kaneo"]
    assert json.loads(second.stdout)["outline"] == json.loads(first.stdout)["outline"]


def test_only_missing_parts_are_created_and_a_custom_doc_is_kept_when_some_exist(tmp_path, backends):
    kaneo, outline = backends
    project = kaneo.add_project(WORKSPACE, "Example", "EX")
    collection = outline.add_collection("example")
    docs = outline.add_document(collection["id"], "docs", "")
    guidelines = outline.add_document(collection["id"], "guidelines", "", docs["id"])
    custom = outline.add_document(collection["id"], "Testing strategy", "Our own testing rules.", guidelines["id"])

    result = run_provision(make_repo(tmp_path), kaneo, outline)

    assert result.returncode == 0, result.stderr
    assert len(kaneo.projects) == 1
    assert len(outline.collections) == 1
    assert not any(request["path"] == "/api/project" and request["method"] == "POST" for request in kaneo.requests)
    assert {column["slug"] for column in kaneo.columns[project["id"]]} >= set(COLUMNS)
    assert {label["name"] for label in kaneo.labels} == LABELS
    assert custom["text"] == "Our own testing rules."
    paths = documents_by_path(outline, collection["id"])
    assert set(paths) == STRUCTURE | {f"docs/guidelines/{title}" for title in GUIDELINES}
    assert json.loads(result.stdout)["outline"]["guidelines"]["Testing strategy"] == custom["id"]


def test_existing_task_labels_do_not_count_as_workspace_labels(tmp_path, backends):
    kaneo, outline = backends
    kaneo.add_label(WORKSPACE, "feature", task_id="task1")

    run_provision(make_repo(tmp_path), kaneo, outline)

    assert {label["name"] for label in kaneo.labels if label["taskId"] is None} == LABELS


def test_failure_names_outline_and_the_step_when_outline_is_down(tmp_path, backends):
    kaneo, outline = backends
    outline.fail_with = 500

    result = run_provision(make_repo(tmp_path), kaneo, outline)

    assert result.returncode != 0
    assert "Outline" in result.stderr
    assert "list collections" in result.stderr
    assert "fake-outline-key" not in result.stderr


def test_skill_evals_section_is_dropped_when_the_project_is_not_a_plugin(tmp_path, backends):
    kaneo, outline = backends

    run_provision(make_repo(tmp_path), kaneo, outline)

    testing = documents_by_path(outline, outline.collections[0]["id"])["docs/guidelines/Testing strategy"]["text"]
    assert "Skill evals" not in testing
    assert "## Unit tests" in testing


def test_skill_evals_section_is_kept_when_the_project_is_a_plugin(tmp_path, backends):
    kaneo, outline = backends

    run_provision(make_repo(tmp_path, plugin=True), kaneo, outline)

    testing = documents_by_path(outline, outline.collections[0]["id"])["docs/guidelines/Testing strategy"]["text"]
    assert "## Skill evals" in testing
    assert "* Skill evals" in testing
