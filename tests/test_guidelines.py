"""The repo's guideline docs: all present under the fixed names, and easy to navigate."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDELINES = ROOT / "docs/guidelines"
NAMES = (
    "architecture.md",
    "code-style.md",
    "commit-conventions.md",
    "documentation-style.md",
    "review-policy.md",
    "skill-authoring.md",
    "task-style.md",
    "testing.md",
)
# A doc longer than this starts with a contents list.
CONTENTS_THRESHOLD_LINES = 100


def test_exactly_the_named_docs_are_present():
    assert sorted(path.name for path in GUIDELINES.glob("*.md")) == list(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_long_doc_starts_with_contents_that_match_its_sections(name):
    text = (GUIDELINES / name).read_text()
    if len(text.splitlines()) <= CONTENTS_THRESHOLD_LINES:
        pytest.skip("short enough to need no contents list")

    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert headings[0] == "Contents"
    contents = text.split("## Contents", 1)[1].split("\n## ", 1)[0]
    entries = re.findall(r"^\* (.+)$", contents, re.MULTILINE)
    assert entries
    assert [entry for entry in entries if entry not in headings] == []
