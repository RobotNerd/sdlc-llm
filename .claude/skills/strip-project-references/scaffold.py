#!/usr/bin/env python3
"""Deterministic scripting for the `strip-project-references` skill.

Repo-only: this skill (and this script) exist to keep this repo's own shipped
`.claude/skills/**` surface free of references (`TASK-`/`EPIC-`/`SPEC-NNN` ids, `CLAUDE.md`,
`.tmp/workflow-plan.md`, "this repo's own …") that would confuse an agent working in a different
project once this toolkit is vendored there. `init-project`'s future `upgrade` excludes this
skill's own directory from what it copies -- see TASK-029's Notes.

`scan_surface` is the single canonical detector -- also imported by
`tests/test_portable_surface.py`, so the CI regression gate and this interactive tool can't drift
apart. It classifies every `TASK-NNN`/`EPIC-NNN`/`SPEC-NNN` occurrence and banned-phrase hit into
two buckets:

- mechanical: safe to fix by pattern substitution alone -- an id-only provenance parenthetical
  (`(TASK-024)`, `(TASK-021/022/024)`), or a bare example id (`TASK-016`, `[TASK-004, TASK-006]`)
  with nothing else needing judgment nearby.
- judgment: a `§`-citation, a banned-phrase occurrence, or any id sharing a paragraph with either
  -- these need a human/LLM-authored sentence rewrite, never a mechanical substitution.

"Paragraph" here means a blank-line-delimited block of the raw file text -- the granularity every
real reference-stripping edit works at (one docstring/comment block at a time), and wide enough to
catch a citation whose `§` mark lands on the line after its id (e.g. `(SPEC-001\n    §'...')`,
which a same-line-only check would miss). An id is only auto-fixed when its whole paragraph is
otherwise clean.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("strip-project-references: not inside a git repository")
    return Path(result.stdout.strip())


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"\b(?:TASK|EPIC|SPEC)-\d{3}\b")
_ID_ONLY_PAREN_RE = re.compile(r"\((?:TASK|EPIC|SPEC)-\d{3}(?:/\d{3})*\)")
_BANNED_PHRASES = ("CLAUDE.md", ".tmp/workflow-plan.md", "this repo's own")

# `CLAUDE.md` is also a generic Claude Code convention filename (like `README.md`), not
# necessarily a pointer to *this* repo's own doc -- these two spots use it as a legitimate default
# filename for any project, so they're exempt from the `CLAUDE.md` ban specifically. Matched by an
# anchor string on the same line so a *new* stray `CLAUDE.md` reference elsewhere still trips the
# check. (Same exemptions TASK-027 carved out.)
_CLAUDE_MD_EXEMPTIONS = {
    "init-project/templates/config.md": "docs_review_paths",
    "review-docs/scaffold.py": "_ROOT_DOC_NAMES",
}


# Repo-only skill directories, excluded from the scan itself: portability is the whole reason
# this check exists, and a repo-only skill (by definition never vendored elsewhere -- see this
# skill's own SKILL.md) has nothing to be portable *for*. Without this, this script's own
# docstring -- which necessarily names real ids and the banned phrases themselves to document what
# it detects -- would trip its own scanner. Grow this set if another repo-only skill is added.
_EXCLUDED_SKILL_DIRS = {"strip-project-references"}


def iter_skill_surface_files(skills_dir: Path):
    """Every file under `.claude/skills/` that's part of the *portable* surface --
    `__pycache__` and `_EXCLUDED_SKILL_DIRS` excluded.
    """
    for path in sorted(skills_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.relative_to(skills_dir).parts[0] in _EXCLUDED_SKILL_DIRS:
            continue
        yield path


def _is_claude_md_exempt(rel_path: str, line: str) -> bool:
    anchor = _CLAUDE_MD_EXEMPTIONS.get(rel_path)
    return anchor is not None and anchor in line


def _banned_phrase_hits(rel_path: str, line: str) -> list[str]:
    """Banned phrases present on `line`, minus the `CLAUDE.md` exemption for this path."""
    hits = []
    for phrase in _BANNED_PHRASES:
        if phrase not in line:
            continue
        if phrase == "CLAUDE.md" and _is_claude_md_exempt(rel_path, line):
            continue
        hits.append(phrase)
    return hits


def _split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """(start, end, text) for each blank-line-delimited paragraph of `text`, in order."""
    paragraphs = []
    start = 0
    for m in re.finditer(r"\n[ \t]*\n", text):
        end = m.start() + 1
        if end > start:
            paragraphs.append((start, end, text[start:end]))
        start = m.end()
    if start < len(text):
        paragraphs.append((start, len(text), text[start:]))
    return paragraphs


def _paragraph_is_dirty(rel_path: str, paragraph_text: str) -> bool:
    """True if `paragraph_text` contains a `§` citation mark or a (non-exempt) banned phrase --
    meaning every id in it needs a human/LLM sentence rewrite, not a mechanical substitution.
    """
    if "§" in paragraph_text:
        return True
    for line in paragraph_text.splitlines():
        if _banned_phrase_hits(rel_path, line):
            return True
    return False


def scan_surface(skills_dir: Path) -> dict:
    """Scan every file under `skills_dir` and classify offenders into `mechanical`/`judgment`
    buckets (see module docstring). Each entry is `{"path", "line", "kind", ...}`, `path` relative
    to `skills_dir`.
    """
    mechanical: list[dict] = []
    judgment: list[dict] = []

    for path in iter_skill_surface_files(skills_dir):
        rel = str(path.relative_to(skills_dir))
        text = path.read_text()

        for line_no, line in enumerate(text.splitlines(), start=1):
            for phrase in _banned_phrase_hits(rel, line):
                judgment.append({"path": rel, "line": line_no, "kind": "banned_phrase", "phrase": phrase})

        for para_start, _para_end, para_text in _split_paragraphs(text):
            dirty = _paragraph_is_dirty(rel, para_text)
            paren_spans = [
                (m.start(), m.end(), m.group(0)) for m in _ID_ONLY_PAREN_RE.finditer(para_text)
            ]
            reported_parens: set[tuple[int, int]] = set()

            for m in _ID_RE.finditer(para_text):
                abs_start = para_start + m.start()
                line_no = text.count("\n", 0, abs_start) + 1
                full_id = m.group(0)
                enclosing = next(
                    (s for s in paren_spans if s[0] <= m.start() < s[1]), None
                )

                if dirty:
                    judgment.append(
                        {"path": rel, "line": line_no, "kind": "id_needs_rewrite", "text": full_id}
                    )
                    continue

                if enclosing:
                    key = (enclosing[0], enclosing[1])
                    if key not in reported_parens:
                        reported_parens.add(key)
                        mechanical.append(
                            {"path": rel, "line": line_no, "kind": "id_parenthetical", "text": enclosing[2]}
                        )
                    continue

                mechanical.append({"path": rel, "line": line_no, "kind": "id_example", "text": full_id})

    return {"mechanical": mechanical, "judgment": judgment}


# ---------------------------------------------------------------------------
# Mechanical fix
# ---------------------------------------------------------------------------


def _nnn_ify(id_text: str) -> str:
    prefix = id_text.split("-", 1)[0]
    return f"{prefix}-NNN"


def apply_mechanical_fixes(skills_dir: Path, dry_run: bool = False) -> list[dict]:
    """Apply only the mechanical bucket's two transforms (strip an id-only parenthetical; NNN-ify
    a bare example id), recomputed fresh per file against the current text so edits stay accurate
    even if `scan_surface` was run earlier against a since-changed tree. Never touches a paragraph
    `_paragraph_is_dirty` flags. Returns `[{"path", "count"}, ...]` for files actually changed (or
    that would change, if `dry_run`); writes nothing when `dry_run` is true.
    """
    changes: list[dict] = []

    for path in iter_skill_surface_files(skills_dir):
        rel = str(path.relative_to(skills_dir))
        text = path.read_text()
        edits: list[tuple[int, int, str]] = []

        for para_start, _para_end, para_text in _split_paragraphs(text):
            if _paragraph_is_dirty(rel, para_text):
                continue

            paren_spans = [
                (para_start + m.start(), para_start + m.end())
                for m in _ID_ONLY_PAREN_RE.finditer(para_text)
            ]
            for s, e in paren_spans:
                lead = s - 1
                if lead >= 0 and text[lead] == " ":
                    edits.append((lead, e, ""))
                else:
                    edits.append((s, e, ""))

            for m in _ID_RE.finditer(para_text):
                abs_start = para_start + m.start()
                abs_end = para_start + m.end()
                if any(s <= abs_start < e for s, e in paren_spans):
                    continue
                edits.append((abs_start, abs_end, _nnn_ify(m.group(0))))

        if not edits:
            continue

        edits.sort(key=lambda edit: edit[0], reverse=True)
        new_text = text
        for s, e, replacement in edits:
            new_text = new_text[:s] + replacement + new_text[e:]

        if new_text != text:
            changes.append({"path": rel, "count": len(edits)})
            if not dry_run:
                path.write_text(new_text)

    return changes


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_scan(_args: argparse.Namespace) -> int:
    skills_dir = repo_root() / ".claude" / "skills"
    print(json.dumps(scan_surface(skills_dir)))
    return 0


def cmd_apply_mechanical(args: argparse.Namespace) -> int:
    skills_dir = repo_root() / ".claude" / "skills"
    changes = apply_mechanical_fixes(skills_dir, dry_run=args.dry_run)
    print(json.dumps({"changed": changes}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="report mechanical/judgment offenders under .claude/skills/")

    apply_parser = subparsers.add_parser(
        "apply-mechanical", help="fix the mechanically-safe offenders in place"
    )
    apply_parser.add_argument(
        "--dry-run", action="store_true", help="report what would change without writing"
    )

    args = parser.parse_args(argv)
    dispatch = {"scan": cmd_scan, "apply-mechanical": cmd_apply_mechanical}
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
