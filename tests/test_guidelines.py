"""The default guideline docs the plugin ships: portable to any project, and easy to navigate."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDELINES = ROOT / "lib/references/guidelines"
SHIPPED = ("documentation-style.md", "review-policy.md", "task-style-guide.md", "testing-strategy.md")
# A tracker key such as ABC-12. KEY-NNN style placeholders don't match, since they have no digits.
TRACKER_KEY = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
# Paths and names that only make sense inside this repo.
REPO_SPECIFIC = ("/Users/", ".claude-plugin", "hooks/", "lib/", "mcp.json", "sdlc-llm", "§")
# A doc longer than this starts with a contents list.
CONTENTS_THRESHOLD_LINES = 100


def test_exactly_the_default_docs_are_shipped():
    assert sorted(path.name for path in GUIDELINES.glob("*.md")) == list(SHIPPED)


@pytest.mark.parametrize("name", SHIPPED)
def test_doc_has_no_tracker_keys_or_repo_specific_paths(name):
    text = (GUIDELINES / name).read_text()

    assert TRACKER_KEY.findall(text) == []
    assert [term for term in REPO_SPECIFIC if term in text] == []


@pytest.mark.parametrize("name", SHIPPED)
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
