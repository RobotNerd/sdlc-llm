"""The draft validator: a JSON draft of tasks checked against the Task style guide's mechanical rules."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/validate_draft.py"
STYLE_GUIDE = ROOT / "lib/references/guidelines/task-style-guide.md"

GOOD_DESCRIPTION = """\
## Description
Add a `--json` flag to the export command, so scripts can read its output.

## Acceptance criteria
- [ ] `export --json` prints one JSON object per task.
- [ ] `export` without the flag prints the table as before.

## Testing strategy
### Automated
#### JSON flag → one object per task   (criterion: first)
* **Given:** two tasks
* **When:** `export --json` runs
* **Then:** two JSON lines

#### No flag → table   (criterion: second)
* **Given:** two tasks
* **When:** `export` runs
* **Then:** the table, unchanged

### Manual
None

## Notes
None
"""

GOOD_DEFERRED = """\
## Deferred
Export to CSV.
## Why
Nobody has asked for it yet.
## Brings it back
A request for a spreadsheet export.
## Source
none
"""


def task(task_id, **fields):
    return {
        "id": task_id,
        "title": "Add JSON output to the export command",
        "type": "feature",
        "description": GOOD_DESCRIPTION,
        "blocked_by": [],
        **fields,
    }


def deferred(item_id, **fields):
    return {"id": item_id, "title": "Export tasks to CSV", "description": GOOD_DEFERRED, **fields}


def run_validator(tmp_path, tasks=(), deferred_items=()):
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps({"tasks": list(tasks), "deferred": list(deferred_items)}))
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(draft)],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


def error_lines(result):
    return result.stdout.strip().splitlines()


def test_ok_is_printed_when_the_style_guide_good_example_is_validated(tmp_path):
    guide = STYLE_GUIDE.read_text()
    example = guide.split("**Good**", 1)[1].split("```markdown\n", 1)[1].split("\n```", 1)[0]
    title_line, description = example.split("\n", 1)
    good = task("good", title=title_line.removeprefix("Title: "), description=description.strip() + "\n")

    result = run_validator(tmp_path, [good], [deferred("later")])

    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout) == {"ok": True}


def test_every_task_in_the_cycle_is_named_when_blockers_form_a_cycle(tmp_path):
    tasks = [
        task("a", blocked_by=["b"]),
        task("b", blocked_by=["c"]),
        task("c", blocked_by=["a"]),
        task("d", blocked_by=["a"]),
    ]

    result = run_validator(tmp_path, tasks)

    assert result.returncode == 1
    cycle_errors = [line for line in error_lines(result) if ": cycle: " in line]
    assert len(cycle_errors) == 1
    named = set(re.findall(r"\b[a-d]\b", cycle_errors[0].split(": cycle: ", 1)[1]))
    assert named == {"a", "b", "c"}


def test_unknown_blocker_is_named_when_blocked_by_cites_a_missing_id(tmp_path):
    result = run_validator(tmp_path, [task("a", blocked_by=["missing-id"])])

    assert result.returncode == 1
    assert error_lines(result) == ["a: unknown-blocker: missing-id"]


@pytest.mark.parametrize("section", ["Description", "Acceptance criteria", "Testing strategy", "Notes"])
def test_missing_section_is_named_when_a_task_lacks_it(tmp_path, section):
    description = GOOD_DESCRIPTION.replace(f"## {section}\n", "")

    result = run_validator(tmp_path, [task("a", description=description)])

    assert result.returncode == 1
    assert f"a: missing-section: {section}" in error_lines(result)


@pytest.mark.parametrize(
    ("title", "rule"),
    [
        ("Add " + "a very long title " * 4 + "that runs on", "title-length"),
        ("Add JSON output to the export command.", "title-period"),
        ("Finish the export work from EX-12", "title-task-key"),
    ],
)
def test_title_rule_is_named_when_the_title_breaks_it(tmp_path, title, rule):
    result = run_validator(tmp_path, [task("a", title=title)])

    assert result.returncode == 1
    assert [line for line in error_lines(result) if line.startswith(f"a: {rule}: ")]


@pytest.mark.parametrize(
    "criteria",
    ["None\n", "* `export --json` prints one JSON object per task.\n", "\n"],
    ids=["none", "bullets", "empty"],
)
def test_criteria_rule_is_named_when_criteria_are_not_a_checklist(tmp_path, criteria):
    description = re.sub(
        r"(## Acceptance criteria\n).*?(\n## Testing strategy)", rf"\g<1>{criteria}\g<2>", GOOD_DESCRIPTION, flags=re.S
    )

    result = run_validator(tmp_path, [task("a", description=description)])

    assert result.returncode == 1
    assert [line for line in error_lines(result) if line.startswith("a: criteria-checklist: ")]


def test_untested_criterion_is_named_when_no_test_cites_it(tmp_path):
    description = GOOD_DESCRIPTION.replace(
        "- [ ] `export` without the flag prints the table as before.\n",
        "- [ ] `export` without the flag prints the table as before.\n- [ ] `export --csv` prints CSV.\n",
    )

    result = run_validator(tmp_path, [task("a", description=description)])

    assert result.returncode == 1
    errors = [line for line in error_lines(result) if line.startswith("a: untested-criterion: ")]
    assert len(errors) == 1
    assert "export --csv" in errors[0]


@pytest.mark.parametrize("reference", ["(criteria: first, second)", "(criteria: first to second)", "(criteria: all)"])
def test_ok_is_printed_when_one_test_cites_every_criterion(tmp_path, reference):
    description = GOOD_DESCRIPTION.replace("(criterion: first)", reference).replace("(criterion: second)", "")

    result = run_validator(tmp_path, [task("a", description=description)])

    assert result.returncode == 0, result.stdout


def test_type_rule_is_named_when_the_type_is_not_one_of_the_five(tmp_path):
    result = run_validator(tmp_path, [task("a", type="enhancement")])

    assert result.returncode == 1
    assert [line for line in error_lines(result) if line.startswith("a: type: ") and "enhancement" in line]


@pytest.mark.parametrize("section", ["Deferred", "Why", "Brings it back", "Source"])
def test_missing_section_is_named_when_a_deferred_item_lacks_it(tmp_path, section):
    description = GOOD_DEFERRED.replace(f"## {section}\n", "")

    result = run_validator(tmp_path, [], [deferred("later", description=description)])

    assert result.returncode == 1
    assert f"later: missing-section: {section}" in error_lines(result)


def test_every_error_is_listed_when_a_draft_breaks_several_rules(tmp_path):
    tasks = [task("a", type="enhancement", blocked_by=["missing-id"]), task("b", title="Fix it.")]

    result = run_validator(tmp_path, tasks)

    assert result.returncode == 1
    rules = {line.split(": ")[1] for line in error_lines(result)}
    assert rules == {"type", "unknown-blocker", "title-period"}


def test_draft_error_is_printed_when_the_file_is_not_valid_json(tmp_path):
    draft = tmp_path / "draft.json"
    draft.write_text("{not json")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(draft)], capture_output=True, check=False, text=True, timeout=30
    )

    assert result.returncode == 1
    assert result.stdout.startswith("draft: invalid-json: ")
