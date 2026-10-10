"""Check a JSON draft of tasks against the Task style guide's mechanical rules.

Prints {"ok": true} and exits 0 when the draft passes. Otherwise prints every error, one per
line, as `<id>: <rule>: <detail>`, and exits 1.

The draft is one JSON object:

    {
      "tasks": [
        {
          "id": "export-json",            # any string, unique in the draft
          "title": "Add JSON output to the export command",
          "type": "feature",              # feature, bug, chore, refactor, or docs
          "description": "## Description\\n...",   # the task template, in markdown
          "blocked_by": ["other-id"]      # ids of tasks in this draft
        }
      ],
      "deferred": [
        {
          "id": "csv-export",
          "title": "Export tasks to CSV",
          "description": "## Deferred\\n...\\n## Why\\n...\\n## Brings it back\\n...\\n## Source\\n..."
        }
      ]
    }

Judgment checks, such as whether a criterion is objective, are left to the skills.
"""

import argparse
import json
import re
import sys
from pathlib import Path

TASK_SECTIONS = ("Description", "Acceptance criteria", "Testing strategy", "Notes")
DEFERRED_SECTIONS = ("Deferred", "Why", "Brings it back", "Source")
TYPES = ("feature", "bug", "chore", "refactor", "docs")
TITLE_MAX = 70
# A tracker key such as ABC-12. Placeholders such as KEY-NNN have no digits, so they pass.
TASK_KEY = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
CHECKLIST_ITEM = re.compile(r"^- \[ \] \S")
# A test names its criteria as "(criterion: first)", "(criteria: first, third)",
# "(criteria: second to fourth)", or "(criteria: all)".
CRITERIA_REFERENCE = re.compile(r"\(criteri(?:on|a):\s*([^)]*)\)")
ORDINALS = (
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
    "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth"
).split()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("draft", type=Path, help="the draft's JSON file")
    arguments = parser.parse_args(argv)

    errors = validate_file(arguments.draft)
    if errors:
        print("\n".join(errors))
        return 1
    print(json.dumps({"ok": True}))
    return 0


def validate_file(path):
    try:
        draft = json.loads(path.read_text())
    except OSError as error:
        return [f"draft: unreadable: {error.strerror}"]
    except json.JSONDecodeError as error:
        return [f"draft: invalid-json: {error}"]
    if not isinstance(draft, dict):
        return ["draft: invalid-json: the draft must be an object with `tasks` and `deferred`"]
    return validate(draft.get("tasks") or [], draft.get("deferred") or [])


def validate(tasks, deferred_items):
    errors = []
    task_ids = [item.get("id", "") for item in tasks]
    for item_id in sorted({item_id for item_id in task_ids if task_ids.count(item_id) > 1}):
        errors.append(f"{item_id}: duplicate-id: used by {task_ids.count(item_id)} tasks")

    for item in tasks:
        item_id = item.get("id") or "<no id>"
        errors += [f"{item_id}: {error}" for error in task_errors(item, set(task_ids))]
    errors += cycle_errors(tasks)
    for item in deferred_items:
        item_id = item.get("id") or "<no id>"
        errors += [f"{item_id}: {error}" for error in title_errors(item.get("title", ""))]
        errors += [f"{item_id}: {error}" for error in section_errors(item.get("description", ""), DEFERRED_SECTIONS)]
    return errors


def task_errors(item, known_ids):
    errors = title_errors(item.get("title", ""))
    if item.get("type") not in TYPES:
        errors.append(f"type: {item.get('type')!r} isn't one of {', '.join(TYPES)}")
    errors += [f"unknown-blocker: {blocker}" for blocker in item.get("blocked_by") or [] if blocker not in known_ids]

    description = item.get("description", "")
    errors += section_errors(description, TASK_SECTIONS)
    sections = split_sections(description)
    if "Acceptance criteria" in sections:
        criteria, checklist_errors = parse_criteria(sections["Acceptance criteria"])
        errors += checklist_errors
        tested = tested_criteria(sections.get("Testing strategy", ""), len(criteria))
        for number, criterion in enumerate(criteria, start=1):
            if number not in tested:
                errors.append(f"untested-criterion: the {ordinal(number)} criterion, {criterion!r}, has no test")
    return errors


def title_errors(title):
    errors = []
    if not title.strip():
        errors.append("title-missing: the title is empty")
    if len(title) > TITLE_MAX:
        errors.append(f"title-length: {len(title)} characters, over {TITLE_MAX}")
    if title.rstrip().endswith("."):
        errors.append("title-period: the title ends in a period")
    errors += [f"title-task-key: {key}" for key in TASK_KEY.findall(title)]
    return errors


def section_errors(description, required):
    present = split_sections(description)
    return [f"missing-section: {name}" for name in required if name not in present]


def split_sections(markdown):
    """Map each top-level `## ` heading to its text, skipping headings inside code blocks."""
    sections, current, in_fence = {}, None, False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines) for name, lines in sections.items()}


def parse_criteria(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], ["criteria-checklist: the acceptance criteria are empty"]
    criteria, errors = [], []
    for line in lines:
        if CHECKLIST_ITEM.match(line):
            criteria.append(line[len("- [ ] ") :].strip())
        else:
            errors.append(f"criteria-checklist: {line.strip()!r} isn't a `- [ ]` item")
    return criteria, errors


def tested_criteria(testing_text, count):
    tested = set()
    for reference in CRITERIA_REFERENCE.findall(testing_text):
        for part in reference.split(","):
            words = part.strip().lower().split()
            if words == ["all"]:
                tested.update(range(1, count + 1))
            elif len(words) == 3 and words[1] == "to" and ordinal_number(words[0]) and ordinal_number(words[2]):
                tested.update(range(ordinal_number(words[0]), ordinal_number(words[2]) + 1))
            elif len(words) == 1 and ordinal_number(words[0]):
                tested.add(ordinal_number(words[0]))
    return tested


def ordinal_number(word):
    if word.isdigit():
        return int(word)
    return ORDINALS.index(word) + 1 if word in ORDINALS else None


def ordinal(number):
    return ORDINALS[number - 1] if number <= len(ORDINALS) else str(number)


def cycle_errors(tasks):
    """One error per cycle, naming every task in it, found as strongly connected components."""
    graph = {item.get("id"): list(item.get("blocked_by") or []) for item in tasks}
    index, lowlink, on_stack, stack, components = {}, {}, set(), [], []

    def visit(node):
        index[node] = lowlink[node] = len(index)
        stack.append(node)
        on_stack.add(node)
        for blocker in graph[node]:
            if blocker not in graph:
                continue
            if blocker not in index:
                visit(blocker)
                lowlink[node] = min(lowlink[node], lowlink[blocker])
            elif blocker in on_stack:
                lowlink[node] = min(lowlink[node], index[blocker])
        if lowlink[node] == index[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1 or node in graph[node]:
                components.append(component)

    for node in graph:
        if node not in index:
            visit(node)
    errors = []
    for component in components:
        members = [item.get("id") for item in tasks if item.get("id") in component]
        errors.append(f"{members[0]}: cycle: {', '.join(members)} block each other")
    return errors


if __name__ == "__main__":
    sys.exit(main())
