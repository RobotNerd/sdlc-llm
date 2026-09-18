"""Unit and hook-script tests for `.dev/hooks/check-portable-references.py` (TASK-036):
repo-only, denies `gh pr create` when a concrete `TASK-`/`EPIC-`/`SPEC-NNN` id exists anywhere
under `.claude/skills/**`.

Acceptance criteria this covers:
- denies `gh pr create` when a concrete id exists under `.claude/skills/`
- passes on the current (post-TASK-027) tree
- the hook file and its `.claude/settings.json` registration are absent from every file
  `init-project`/`upgrade` writes to another repo
"""

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / ".dev" / "hooks" / "check-portable-references.py"

_loader = SourceFileLoader("check_portable_references", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("check_portable_references", _loader)
check_portable_references = importlib.util.module_from_spec(_spec)
sys.modules["check_portable_references"] = check_portable_references
_loader.exec_module(check_portable_references)


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# find_id_offenders -- pure
# ---------------------------------------------------------------------------


def test_find_id_offenders_empty_on_a_clean_tree(tmp_path):
    _write(tmp_path, "a/SKILL.md", "Nothing project-specific here.\n")
    assert check_portable_references.find_id_offenders(tmp_path) == []


def test_find_id_offenders_flags_a_bare_task_id(tmp_path):
    _write(tmp_path, "a/SKILL.md", "See TASK-016 for context.\n")
    offenders = check_portable_references.find_id_offenders(tmp_path)
    assert len(offenders) == 1
    assert offenders[0]["text"] == "TASK-016"


def test_find_id_offenders_flags_epic_and_spec_ids_too(tmp_path):
    _write(tmp_path, "a/SKILL.md", "EPIC-002 and SPEC-001 both apply here.\n")
    offenders = check_portable_references.find_id_offenders(tmp_path)
    ids = {e["text"] for e in offenders}
    assert ids == {"EPIC-002", "SPEC-001"}


def test_find_id_offenders_excludes_banned_phrase_only_entries(tmp_path):
    _write(tmp_path, "a/SKILL.md", "Update CLAUDE.md when this changes.\n")
    assert check_portable_references.find_id_offenders(tmp_path) == []


def test_find_id_offenders_excludes_the_strip_project_references_skill_itself(tmp_path):
    _write(tmp_path, "strip-project-references/scaffold.py", "TASK-016 example id\n")
    assert check_portable_references.find_id_offenders(tmp_path) == []


# ---------------------------------------------------------------------------
# main() -- PreToolUse payload handling
# ---------------------------------------------------------------------------


def _payload(command: str, cwd: str) -> dict:
    return {
        "session_id": "test-session", "cwd": cwd, "hook_event_name": "PreToolUse",
        "tool_name": "Bash", "tool_input": {"command": command},
    }


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)], input=json.dumps(payload), capture_output=True, text=True
    )


def test_hook_ignores_unrelated_bash_commands(tmp_path):
    _write(tmp_path, ".claude/skills/a/SKILL.md", "See TASK-016 for context.\n")
    result = _run_hook(_payload("git status", str(tmp_path)))
    assert result.returncode == 0
    assert result.stderr == ""


def test_hook_ignores_a_non_bash_tool_call(tmp_path):
    payload = _payload("gh pr create", str(tmp_path))
    payload["tool_name"] = "Edit"
    result = _run_hook(payload)
    assert result.returncode == 0


def test_hook_denies_gh_pr_create_when_an_id_leaked_into_the_skills_surface(tmp_path):
    _write(tmp_path, ".claude/skills/a/SKILL.md", "See TASK-016 for context.\n")
    result = _run_hook(_payload("gh pr create --title x --body y", str(tmp_path)))
    assert result.returncode == 2
    assert "TASK-016" in result.stderr
    assert "a/SKILL.md" in result.stderr


def test_hook_allows_gh_pr_create_on_a_clean_skills_surface(tmp_path):
    _write(tmp_path, ".claude/skills/a/SKILL.md", "Nothing project-specific here.\n")
    result = _run_hook(_payload("gh pr create --title x --body y", str(tmp_path)))
    assert result.returncode == 0
    assert result.stderr == ""


def test_hook_allows_gh_pr_create_when_there_is_no_skills_dir_at_all(tmp_path):
    result = _run_hook(_payload("gh pr create --title x --body y", str(tmp_path)))
    assert result.returncode == 0


def test_hook_survives_malformed_json_on_stdin():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)], input="not json", capture_output=True, text=True
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Real repo tree (testing strategy step: "passes on the current tree")
# ---------------------------------------------------------------------------


def test_find_id_offenders_against_this_repos_real_skills_tree_is_clean():
    skills_dir = REPO_ROOT / ".claude" / "skills"
    assert check_portable_references.find_id_offenders(skills_dir) == []


def test_hook_allows_gh_pr_create_against_this_repos_real_tree():
    result = _run_hook(_payload("gh pr create --title x --body y", str(REPO_ROOT)))
    assert result.returncode == 0
    assert result.stderr == ""


# ---------------------------------------------------------------------------
# Never vendored -- extends TASK-029's managed_files/settings.json exclusion coverage
# ---------------------------------------------------------------------------


def test_hook_script_lives_outside_every_directory_init_project_vendors():
    """`.dev/hooks/**` isn't `.claude/hooks/**` (copied verbatim by `managed_files()`) or
    anywhere under `.claude/skills/**` (also copied, minus repo-only skills) -- so this script
    is excluded from every project `init-project`/`upgrade` write to, by construction, with no
    exclusion list to keep in sync.
    """
    rel = SCRIPT_PATH.relative_to(REPO_ROOT)
    assert rel.parts[0] not in (".claude",)


def test_portable_settings_template_does_not_register_the_repo_only_hook():
    template = REPO_ROOT / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    assert "check-portable-references" not in template.read_text()


def test_this_repos_own_settings_registers_the_repo_only_hook():
    real = REPO_ROOT / ".claude" / "settings.json"
    assert "check-portable-references" in real.read_text()
