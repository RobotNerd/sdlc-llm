"""Unit/integration tests for `init-project/scaffold.py`'s `upgrade` subcommand and the
`managed_files`/`apply_managed_files`/`classify_managed_files`/manifest machinery it shares with
`run` (TASK-029).

Pure functions are tested directly against small fixture trees in `tmp_path`. The `upgrade`
subcommand itself is exercised as a real subprocess against a genuine local "toolkit source" git
repo (a committed copy of this repo's own `.claude/skills/` tree) and a genuine scaffolded target
repo -- `--source` points at the local path so the real `git clone` path is exercised offline, per
the task's own testing strategy.
"""

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

import sync as installed_sync

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "init-project"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"

_loader = SourceFileLoader("init_project_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("init_project_scaffold", _loader)
scaffold = importlib.util.module_from_spec(_spec)
sys.modules["init_project_scaffold"] = scaffold
_loader.exec_module(scaffold)


RUN_ANSWERS = {
    "test_command": "pytest",
    "lint_command": None,
    "format_command": None,
    "docs_paths": ["README.md"],
    "default_branch": "main",
    "branch_prefix": "task-",
    "remote": "origin",
    "rebase_before_pr": True,
    "merge_strategy": "squash",
    "delete_branch_after_merge": True,
    "ci_checks": [],
    "archive_done": True,
    "tdd_enforced": True,
}


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


# ---------------------------------------------------------------------------
# managed_files
# ---------------------------------------------------------------------------


def _build_fake_source(root: Path, skill_names: list[str]) -> None:
    skills_dir = root / ".claude" / "skills"
    for name in skill_names:
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        (skill_dir / "scaffold.py").write_text("# scaffold\n")
        if name == "init-project":
            templates = skill_dir / "templates"
            templates.mkdir()
            (templates / "guidelines.md").write_text("guidelines\n")
            (templates / "spec.md").write_text("spec template\n")
            (templates / "epic.md").write_text("epic template\n")
            (templates / "task.md").write_text("task template\n")
            (templates / "pull_request_template.md").write_text("pr template\n")
            (skill_dir / "vendored-sync").write_text("#!/usr/bin/env python3\n")


def test_managed_files_includes_every_skill_and_the_four_core_items(tmp_path):
    _build_fake_source(tmp_path, ["init-project", "add-task"])
    files = scaffold.managed_files(tmp_path)
    targets = set(files.values())

    assert Path(".claude/skills/add-task/SKILL.md") in targets
    assert Path(".claude/skills/init-project/SKILL.md") in targets
    assert Path(".tasks/guidelines.md") in targets
    assert Path(".tasks/templates/spec.md") in targets
    assert Path(".tasks/templates/epic.md") in targets
    assert Path(".tasks/templates/task.md") in targets
    assert Path(".tasks/bin/sync") in targets
    assert Path(".github/pull_request_template.md") in targets


def test_managed_files_excludes_repo_only_skills(tmp_path):
    _build_fake_source(tmp_path, ["init-project", "strip-project-references"])
    files = scaffold.managed_files(tmp_path)
    targets = set(files.values())
    assert not any(str(t).startswith(".claude/skills/strip-project-references") for t in targets)


def test_managed_files_never_includes_config_or_board(tmp_path):
    _build_fake_source(tmp_path, ["init-project"])
    files = scaffold.managed_files(tmp_path)
    targets = set(files.values())
    assert Path(".tasks/config.md") not in targets
    assert Path(".tasks/BOARD.md") not in targets


def test_managed_files_excludes_pycache(tmp_path):
    _build_fake_source(tmp_path, ["init-project", "add-task"])
    pycache = tmp_path / ".claude" / "skills" / "add-task" / "__pycache__"
    pycache.mkdir()
    (pycache / "scaffold.cpython-313.pyc").write_bytes(b"\x00")
    files = scaffold.managed_files(tmp_path)
    assert not any("__pycache__" in str(t) for t in files.values())


# ---------------------------------------------------------------------------
# apply_managed_files
# ---------------------------------------------------------------------------


def test_apply_managed_files_writes_and_chmods_sync(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("hello\n")
    root = tmp_path / "target"
    root.mkdir()
    written = scaffold.apply_managed_files({source: Path(".tasks/bin/sync")}, root)
    target = root / ".tasks" / "bin" / "sync"
    assert written == [Path(".tasks/bin/sync")]
    assert target.read_text() == "hello\n"
    assert target.stat().st_mode & 0o777 == 0o755


def test_apply_managed_files_skips_self_copy(tmp_path):
    root = tmp_path / "target"
    (root / ".claude" / "skills" / "add-task").mkdir(parents=True)
    same_file = root / ".claude" / "skills" / "add-task" / "SKILL.md"
    same_file.write_text("unchanged\n")

    written = scaffold.apply_managed_files({same_file: Path(".claude/skills/add-task/SKILL.md")}, root)

    assert written == []
    assert same_file.read_text() == "unchanged\n"


# ---------------------------------------------------------------------------
# classify_managed_files / manifest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_content,target_content,manifest_hash_content,expected_bucket",
    [
        (None, None, None, "new"),
        ("content\n", "content\n", None, "up_to_date"),
        ("new content\n", "old content\n", "old content\n", "clean_update"),
        ("new content\n", "someone's edit\n", "old content\n", "locally_modified"),
        # a pre-manifest project: no `manifest_hashes` entry for this file at all, and it
        # doesn't match the incoming source either -- must not be silently treated as safe
        # to overwrite.
        ("new content\n", "pre-existing local content\n", None, "locally_modified"),
    ],
    ids=["new", "up-to-date", "clean-update", "locally-modified-hash-mismatch", "locally-modified-no-manifest-entry"],
)
def test_classify(tmp_path, source_content, target_content, manifest_hash_content, expected_bucket):
    source = tmp_path / "source.md"
    source.write_text(source_content or "content\n")
    root = tmp_path / "target"
    root.mkdir()
    if target_content is not None:
        (root / "file.md").write_text(target_content)
    manifest_hashes = {}
    if manifest_hash_content is not None:
        manifest_hashes["file.md"] = hashlib.sha256(manifest_hash_content.encode()).hexdigest()

    result = scaffold.classify_managed_files({source: Path("file.md")}, root, manifest_hashes)
    assert result[expected_bucket] == [Path("file.md")]


def test_manifest_round_trips(tmp_path):
    root = tmp_path / "target"
    (root / ".tasks").mkdir(parents=True)
    (root / "file.md").write_text("content\n")
    scaffold.write_manifest(root, source="https://example/repo", ref="main", commit="abc123",
                             files={tmp_path / "x": Path("file.md")})
    manifest = scaffold.load_manifest(root)
    assert manifest["source"] == "https://example/repo"
    assert manifest["ref"] == "main"
    assert manifest["commit"] == "abc123"
    assert manifest["files"]["file.md"] == hashlib.sha256(b"content\n").hexdigest()


def test_load_manifest_empty_when_absent(tmp_path):
    root = tmp_path / "target"
    (root / ".tasks").mkdir(parents=True)
    assert scaffold.load_manifest(root) == {}


# ---------------------------------------------------------------------------
# `upgrade` subcommand -- real subprocesses against a real local "toolkit source" repo
# ---------------------------------------------------------------------------


@pytest.fixture
def toolkit_source(tmp_path_factory):
    """A real git repo holding a committed copy of this repo's own `.claude/skills/` tree --
    `--source` points at this local path so `upgrade`'s real `git clone` is exercised offline.
    Function-scoped: several tests commit further changes on top (staleness, conflicts), so each
    test gets its own independent copy rather than fighting over shared mutable state.
    """
    src = tmp_path_factory.mktemp("toolkit-source")
    shutil.copytree(
        REPO_ROOT / ".claude", src / ".claude", ignore=shutil.ignore_patterns("__pycache__")
    )
    _git(["init", "-q"], cwd=src)
    _git(["config", "user.email", "t@example.com"], cwd=src)
    _git(["config", "user.name", "Test"], cwd=src)
    _git(["add", "-A"], cwd=src)
    _git(["commit", "-q", "-m", "toolkit snapshot"], cwd=src)
    _git(["branch", "-M", "main"], cwd=src)
    return src


def _upgrade_script(toolkit_source):
    return toolkit_source / ".claude" / "skills" / "init-project" / "scaffold.py"


def _run_upgrade(toolkit_source, cwd, *extra_args):
    return subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "upgrade",
         "--source", str(toolkit_source), "--ref", "main", *extra_args],
        cwd=cwd, capture_output=True, text=True,
    )


@pytest.fixture
def target(tmp_path, toolkit_source):
    """A scaffolded (via `run`, against `toolkit_source`) target project -- `.claude/skills/` is
    deliberately absent here until `upgrade` pulls it in, matching real behavior (`run` never
    copies sibling skill directories; `upgrade` is the only thing that does).
    """
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q"], cwd=work)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)
    (work / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "init"], cwd=work)

    answers_path = work / "answers.json"
    answers_path.write_text(json.dumps(RUN_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "run", str(answers_path)],
        cwd=work, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "scaffold .tasks"], cwd=work)
    assert not (work / ".claude").exists()  # confirms the premise: `run` doesn't copy skills
    return work


def test_upgrade_refuses_without_tasks_dir(tmp_path, toolkit_source):
    work = tmp_path / "no-tasks"
    work.mkdir()
    _git(["init", "-q"], cwd=work)

    result = _run_upgrade(toolkit_source, work)

    assert result.returncode != 0
    assert "run" in result.stderr
    assert not (work / ".claude").exists()


def test_upgrade_pulls_in_every_portable_skill_not_the_repo_only_one(target, toolkit_source):
    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    for name in ("add-task", "implement-task", "init-project", "plan-feature", "refine-backlog", "review-docs"):
        assert (target / ".claude" / "skills" / name / "SKILL.md").exists(), name
    assert not (target / ".claude" / "skills" / "strip-project-references").exists()


def test_upgrade_writes_manifest(target, toolkit_source):
    result = _run_upgrade(toolkit_source, target)
    assert result.returncode == 0, result.stderr
    manifest = scaffold.load_manifest(target)
    assert manifest["source"] == str(toolkit_source)
    assert manifest["ref"] == "main"
    assert manifest["commit"]
    assert ".claude/skills/add-task/SKILL.md" in manifest["files"]


def test_upgrade_second_run_is_a_true_noop(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    second = _run_upgrade(toolkit_source, target)
    assert second.returncode == 0, second.stderr
    output = json.loads(second.stdout)
    assert output["new"] == []
    assert output["updated"] == []
    assert output["forced"] == []
    status = _git(["status", "--short"], cwd=target)
    assert status.stdout.strip() == ""


def test_upgrade_dry_run_writes_nothing(target, toolkit_source):
    # `run` already wrote a manifest of its own four core items -- dry-run must leave it
    # byte-for-byte alone, not just "not create a new one".
    manifest_before = (target / ".tasks" / scaffold.MANIFEST_NAME).read_bytes()

    result = _run_upgrade(toolkit_source, target, "--dry-run")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert any("add-task/SKILL.md" in p for p in output["new"])
    assert not (target / ".claude").exists()
    assert (target / ".tasks" / scaffold.MANIFEST_NAME).read_bytes() == manifest_before


def test_upgrade_picks_up_a_staled_file(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    staled_source = toolkit_source / ".claude" / "skills" / "add-task" / "SKILL.md"
    staled_source.write_text(staled_source.read_text() + "\n# staled upstream change\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "stale add-task"], cwd=toolkit_source)

    result = _run_upgrade(toolkit_source, target)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert ".claude/skills/add-task/SKILL.md" in output["updated"]
    target_path = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    assert target_path.read_text().endswith("# staled upstream change\n")


def test_upgrade_refuses_locally_modified_and_writes_nothing(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    upstream_source = toolkit_source / ".claude" / "skills" / "add-task" / "SKILL.md"
    upstream_source.write_text(upstream_source.read_text() + "\n# upstream change\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "upstream change"], cwd=toolkit_source)

    local_path = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    local_path.write_text(local_path.read_text() + "\n# local edit\n")
    manifest_before = (target / ".tasks" / scaffold.MANIFEST_NAME).read_bytes()

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode != 0
    assert "add-task/SKILL.md" in result.stderr
    assert "local edit" in result.stderr or "upstream change" in result.stderr
    status = _git(["status", "--short"], cwd=target)
    assert status.stdout.strip() == "M .claude/skills/add-task/SKILL.md"
    assert (target / ".tasks" / scaffold.MANIFEST_NAME).read_bytes() == manifest_before


def test_upgrade_force_overwrites_locally_modified(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    upstream_source = toolkit_source / ".claude" / "skills" / "add-task" / "SKILL.md"
    upstream_source.write_text(upstream_source.read_text() + "\n# upstream change 2\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "upstream change 2"], cwd=toolkit_source)

    local_path = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    local_path.write_text(local_path.read_text() + "\n# local edit 2\n")

    result = _run_upgrade(toolkit_source, target, "--force")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert ".claude/skills/add-task/SKILL.md" in output["forced"]
    assert local_path.read_text().endswith("# upstream change 2\n")


# ---------------------------------------------------------------------------
# Hook scripts (TASK-038 acceptance criterion 1) -- `.claude/hooks/*` classifies and
# refreshes exactly like a skill file, via the same generic managed_files() table
# ---------------------------------------------------------------------------


def test_upgrade_picks_up_a_staled_hook_script(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    staled_source = toolkit_source / ".claude" / "skills" / "init-project" / "vendored-hooks" / "pretooluse_bash.py"
    staled_source.write_text(staled_source.read_text() + "\n# staled upstream change\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "stale hook script"], cwd=toolkit_source)

    result = _run_upgrade(toolkit_source, target)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert ".claude/hooks/pretooluse_bash.py" in output["updated"]
    target_path = target / ".claude" / "hooks" / "pretooluse_bash.py"
    assert target_path.read_text().endswith("# staled upstream change\n")


def test_upgrade_refuses_a_locally_modified_hook_script_and_writes_nothing(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    upstream_source = toolkit_source / ".claude" / "skills" / "init-project" / "vendored-hooks" / "pretooluse_bash.py"
    upstream_source.write_text(upstream_source.read_text() + "\n# upstream change\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "upstream hook change"], cwd=toolkit_source)

    local_path = target / ".claude" / "hooks" / "pretooluse_bash.py"
    local_path.write_text(local_path.read_text() + "\n# local edit\n")

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode != 0
    assert "pretooluse_bash.py" in result.stderr
    status = _git(["status", "--short"], cwd=target)
    assert status.stdout.strip() == "M .claude/hooks/pretooluse_bash.py"


# ---------------------------------------------------------------------------
# `.claude/settings.json`'s hook registrations (TASK-038 acceptance criterion 2) --
# additively merged, never hash-classified/overwritten like the rest of the table
# ---------------------------------------------------------------------------


def _settings_json(project) -> dict:
    return json.loads((project / ".claude" / "settings.json").read_text())


def test_upgrade_adds_a_settings_hook_registration_the_target_is_missing(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    # Simulate the toolkit gaining a brand-new hook (a synthetic event name, so this doesn't
    # interact with the real `SessionStart` entry the template already carries) after `target`
    # was last upgraded.
    template_path = (
        toolkit_source / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    )
    template = json.loads(template_path.read_text())
    template["hooks"]["Notification"] = [
        {"hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/new_hook.py"}]}
    ]
    template_path.write_text(json.dumps(template, indent=2) + "\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "add a new hook"], cwd=toolkit_source)

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert any("new_hook.py" in entry for entry in output["settings_hooks_added"])
    assert _settings_json(target)["hooks"]["Notification"] == template["hooks"]["Notification"]


def test_upgrade_preserves_a_targets_own_extra_settings_hook_registration(target, toolkit_source):
    """The interesting case isn't a no-op re-upgrade -- it's a merge that genuinely writes
    something new (a real template addition) landing *alongside* a project's own custom
    registration without disturbing it.
    """
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr

    settings_path = target / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["hooks"].setdefault("PreToolUse", []).append({
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.dev/hooks/project_only_check.py"}],
    })
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "add a project-only hook registration"], cwd=target)

    template_path = (
        toolkit_source / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    )
    template = json.loads(template_path.read_text())
    template["hooks"]["Notification"] = [
        {"hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/new_hook.py"}]}
    ]
    template_path.write_text(json.dumps(template, indent=2) + "\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "add a new hook"], cwd=toolkit_source)

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert any("new_hook.py" in entry for entry in output["settings_hooks_added"])
    merged = _settings_json(target)
    assert merged["hooks"]["Notification"] == template["hooks"]["Notification"]
    bash_groups = merged["hooks"]["PreToolUse"]
    assert any(
        g.get("matcher") == "Bash" and any("project_only_check.py" in h["command"] for h in g["hooks"])
        for g in bash_groups
    )


def test_upgrade_settings_json_already_current_reports_nothing_added(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    before = (target / ".claude" / "settings.json").read_bytes()

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["settings_hooks_added"] == []
    assert (target / ".claude" / "settings.json").read_bytes() == before


def test_upgrade_dry_run_reports_settings_hooks_would_add_and_writes_nothing(target, toolkit_source):
    template_path = (
        toolkit_source / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    )
    template = json.loads(template_path.read_text())
    template["hooks"]["Notification"] = [
        {"hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/new_hook.py"}]}
    ]
    template_path.write_text(json.dumps(template, indent=2) + "\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "add a new hook"], cwd=toolkit_source)

    before = (target / ".claude" / "settings.json").exists()
    assert before is False  # `target` hasn't been upgraded yet in this test

    result = _run_upgrade(toolkit_source, target, "--dry-run")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert any("new_hook.py" in entry for entry in output["settings_hooks_would_add"])
    assert not (target / ".claude").exists()


def test_upgrade_writes_no_settings_hooks_when_another_conflict_blocks_the_whole_upgrade(target, toolkit_source):
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    # A new template hook (something for settings.json to add) *and* an unrelated locally
    # modified skill file (something that blocks the whole upgrade) at the same time.
    template_path = (
        toolkit_source / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    )
    template = json.loads(template_path.read_text())
    template["hooks"]["Notification"] = [
        {"hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/new_hook.py"}]}
    ]
    template_path.write_text(json.dumps(template, indent=2) + "\n")
    upstream_source = toolkit_source / ".claude" / "skills" / "add-task" / "SKILL.md"
    upstream_source.write_text(upstream_source.read_text() + "\n# upstream change\n")
    _git(["add", "-A"], cwd=toolkit_source)
    _git(["commit", "-q", "-m", "new hook + upstream skill change"], cwd=toolkit_source)

    local_path = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    local_path.write_text(local_path.read_text() + "\n# local edit\n")
    settings_before = (target / ".claude" / "settings.json").read_bytes()

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode != 0
    assert (target / ".claude" / "settings.json").read_bytes() == settings_before


# ---------------------------------------------------------------------------
# `.gitignore` merge (TASK-066) -- `target`'s own `.gitignore` already covers everything, since
# `run` (used to scaffold the `target` fixture) writes it too; these tests reset it first to
# exercise `upgrade`'s own additive merge.
# ---------------------------------------------------------------------------


def test_upgrade_gitignore_already_current_reports_nothing_added(target, toolkit_source):
    before = (target / ".gitignore").read_bytes()

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["gitignore_added"] == []
    assert (target / ".gitignore").read_bytes() == before


def test_upgrade_adds_missing_gitignore_entries_preserving_existing_content(target, toolkit_source):
    (target / ".gitignore").write_text("node_modules/\n*.log\n")

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert set(output["gitignore_added"]) == {"__pycache__/", "*.py[cod]", ".pytest_cache/"}
    gitignore = (target / ".gitignore").read_text()
    assert gitignore.startswith("node_modules/\n*.log\n")
    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert ".pytest_cache/" in gitignore


def test_upgrade_dry_run_reports_gitignore_would_add_and_writes_nothing(target, toolkit_source):
    (target / ".gitignore").write_text("node_modules/\n")
    before = (target / ".gitignore").read_bytes()

    result = _run_upgrade(toolkit_source, target, "--dry-run")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert set(output["gitignore_would_add"]) == {"__pycache__/", "*.py[cod]", ".pytest_cache/"}
    assert (target / ".gitignore").read_bytes() == before


def test_upgrade_writes_no_gitignore_changes_when_another_conflict_blocks_the_whole_upgrade(target, toolkit_source):
    """Same posture as the settings.json case above: a `locally_modified` conflict elsewhere
    refuses the whole `upgrade` and writes nothing at all, `.gitignore` included -- it's not a
    partial apply."""
    first = _run_upgrade(toolkit_source, target)
    assert first.returncode == 0, first.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "upgrade"], cwd=target)

    (target / ".gitignore").write_text("node_modules/\n")
    local_path = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    local_path.write_text(local_path.read_text() + "\n# local edit\n")

    result = _run_upgrade(toolkit_source, target)

    assert result.returncode != 0
    assert (target / ".gitignore").read_text() == "node_modules/\n"


# ---------------------------------------------------------------------------
# Data-loss guard (testing strategy step 4) -- the criterion that matters most
# ---------------------------------------------------------------------------


def _hash_tree(root, *rel_dirs):
    hashes = {}
    for rel_dir in rel_dirs:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def test_upgrade_never_touches_non_managed_tasks_or_github_files(target, toolkit_source):
    ADD_TASK_SCRIPT = toolkit_source / ".claude" / "skills" / "add-task" / "scaffold.py"
    add_task_answers = target.parent / "add-task-answers.json"
    add_task_answers.write_text(json.dumps({
        "title": "A real task",
        "type": "feature",
        "epic": None,
        "blocked_by": [],
        "priority_mode": "end",
    }))
    add_result = subprocess.run(
        [sys.executable, str(ADD_TASK_SCRIPT), "run", str(add_task_answers)],
        cwd=target, capture_output=True, text=True,
    )
    assert add_result.returncode == 0, add_result.stderr
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "add a real task"], cwd=target)

    # The manifest itself is legitimately rewritten every successful upgrade (fresh hashes) --
    # it's `upgrade`'s own bookkeeping, not a "non-managed" project-owned file, even though it
    # isn't part of `managed_files()`'s table.
    managed_targets = {str(t) for t in scaffold.managed_files(toolkit_source).values()}
    managed_targets.add(f".tasks/{scaffold.MANIFEST_NAME}")
    before = _hash_tree(target, ".tasks", ".github")

    result = _run_upgrade(toolkit_source, target)
    assert result.returncode == 0, result.stderr

    after = _hash_tree(target, ".tasks", ".github")
    for rel, digest in before.items():
        if rel in managed_targets:
            continue
        assert after.get(rel) == digest, f"non-managed file changed: {rel}"


def test_upgrade_never_touches_a_dev_only_hook_path(target, toolkit_source):
    """Extends the data-loss guard above explicitly to a repo-only hook path (this toolkit's own
    `.dev/hooks/*`, never in `managed_files()` at all): a regression that started copying under
    `.dev/` should fail this loudly, not just pass silently because no test looked there.
    """
    dev_hook = target / ".dev" / "hooks" / "check-portable-references.py"
    dev_hook.parent.mkdir(parents=True)
    dev_hook.write_text("# repo-only, never vendored into another project\n")
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "simulate a repo-only dev hook"], cwd=target)

    before = _hash_tree(target, ".dev")
    assert before  # sanity: the fixture file above is actually there to protect

    result = _run_upgrade(toolkit_source, target)
    assert result.returncode == 0, result.stderr

    after = _hash_tree(target, ".dev")
    assert after == before


# ---------------------------------------------------------------------------
# `--target` on both `run` and `upgrade` (TASK-049) -- scaffolding/refreshing a project by path
# from an unrelated cwd, exercised against the same local `toolkit_source` fixture as above so
# hashes are stable and independent of this actual working tree's uncommitted state.
# ---------------------------------------------------------------------------


def test_run_target_installs_skills_from_an_unrelated_cwd(tmp_path, toolkit_source):
    cwd = tmp_path / "unrelated-cwd"
    cwd.mkdir()
    target = tmp_path / "target-repo"
    target.mkdir()
    _git(["init", "-q"], cwd=target)
    _git(["config", "user.email", "t@example.com"], cwd=target)
    _git(["config", "user.name", "Test"], cwd=target)
    (target / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "init"], cwd=target)

    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(RUN_ANSWERS))
    result = subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "run", str(answers_path),
         "--target", str(target)],
        cwd=cwd, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (target / ".claude" / "skills" / "add-task" / "SKILL.md").exists()
    assert not (target / ".claude" / "skills" / "strip-project-references").exists()
    assert not (cwd / ".tasks").exists()


def test_run_target_then_upgrade_target_dry_run_sees_skills_up_to_date(tmp_path, toolkit_source):
    target = tmp_path / "target-repo"
    target.mkdir()
    _git(["init", "-q"], cwd=target)
    _git(["config", "user.email", "t@example.com"], cwd=target)
    _git(["config", "user.name", "Test"], cwd=target)
    (target / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=target)
    _git(["commit", "-q", "-m", "init"], cwd=target)

    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(RUN_ANSWERS))
    run_result = subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "run", str(answers_path),
         "--target", str(target)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert run_result.returncode == 0, run_result.stderr

    dry = subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "upgrade",
         "--target", str(target), "--source", str(toolkit_source), "--ref", "main", "--dry-run"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert dry.returncode == 0, dry.stderr
    classification = json.loads(dry.stdout)
    assert classification["locally_modified"] == []
    assert any("add-task/SKILL.md" in p for p in classification["up_to_date"])


def test_upgrade_target_refreshes_a_separate_project(target, toolkit_source, tmp_path):
    cwd = tmp_path / "unrelated-cwd"
    cwd.mkdir()

    result = subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "upgrade",
         "--target", str(target), "--source", str(toolkit_source), "--ref", "main"],
        cwd=cwd, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (target / ".claude" / "skills" / "add-task" / "SKILL.md").exists()
    assert not (cwd / ".tasks").exists()


# ---------------------------------------------------------------------------
# `merge_config_schema` (TASK-030) -- pure function, hand-built fixtures
# ---------------------------------------------------------------------------


_CURRENT_CONFIG = """---
workflow_version: 1
test_command: pytest
lint_command: null
docs_paths: [README.md]
docs_review_paths: [README.md]
docs_ignore_paths: []
default_branch: main
branch_prefix: task-
remote: origin
rebase_before_pr: true
merge_strategy: squash
delete_branch_after_merge: true
allow_auto_merge: false
ci_checks: []
archive_done: true
context_usage_halt_pct: 85
token_budget_per_batch: null
ignored_paths: []
---

# Workflow config
"""


def _drop_keys(text: str, *keys: str) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if not any(line.startswith(f"{k}:") for k in keys))


def test_merge_config_schema_is_noop_on_an_already_current_file():
    merged, added, bumped = scaffold.merge_config_schema(_CURRENT_CONFIG, installed_sync)
    assert merged == _CURRENT_CONFIG
    assert added == []
    assert bumped is None


def test_merge_config_schema_adds_a_single_missing_key_at_template_position():
    old = _drop_keys(_CURRENT_CONFIG, "ignored_paths")
    merged, added, bumped = scaffold.merge_config_schema(old, installed_sync)
    assert added == ["ignored_paths"]
    assert bumped is None
    lines = merged.splitlines()
    assert lines[lines.index("token_budget_per_batch: null") + 1] == "ignored_paths: []"


def test_merge_config_schema_adds_multiple_missing_keys_at_their_own_positions():
    old = _drop_keys(_CURRENT_CONFIG, "docs_review_paths", "docs_ignore_paths", "ignored_paths")
    merged, added, bumped = scaffold.merge_config_schema(old, installed_sync)
    assert added == ["docs_review_paths", "docs_ignore_paths", "ignored_paths"]
    lines = merged.splitlines()
    assert lines[lines.index("docs_paths: [README.md]") + 1] == "docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md]"
    assert lines[lines.index("docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md]") + 1] == "docs_ignore_paths: []"
    assert lines[lines.index("token_budget_per_batch: null") + 1] == "ignored_paths: []"


def test_merge_config_schema_adds_usage_safety_valve_keys_at_template_position():
    old = _drop_keys(_CURRENT_CONFIG, "context_usage_halt_pct", "token_budget_per_batch")
    merged, added, bumped = scaffold.merge_config_schema(old, installed_sync)
    assert added == ["context_usage_halt_pct", "token_budget_per_batch"]
    assert bumped is None
    lines = merged.splitlines()
    assert lines[lines.index("archive_done: true") + 1] == "context_usage_halt_pct: 85"
    assert lines[lines.index("context_usage_halt_pct: 85") + 1] == "token_budget_per_batch: null"


def test_merge_config_schema_preserves_existing_values_and_project_added_key():
    # `project_extra_key` sits between two template keys neither of which is missing here, so
    # it's untouched by the one insertion (`ignored_paths`, at the very end) -- a clean check
    # that an existing project-added key's position and value survive the merge unmoved.
    old = _CURRENT_CONFIG.replace(
        "docs_paths: [README.md]\n", "docs_paths: [README.md]\nproject_extra_key: keep-me\n"
    )
    old = _drop_keys(old, "ignored_paths")
    merged, added, bumped = scaffold.merge_config_schema(old, installed_sync)
    assert added == ["ignored_paths"]
    assert "project_extra_key: keep-me" in merged
    fields, _, order = installed_sync.parse_frontmatter(merged)
    assert order.index("docs_paths") < order.index("project_extra_key") < order.index("docs_review_paths")
    assert fields["test_command"] == "pytest"
    assert fields["archive_done"] is True


def test_merge_config_schema_preserves_body_byte_identical_including_dashes_lookalike():
    body = "\n# Workflow config\n\nSome prose with a --- lookalike line.\n---\nmore prose\n"
    old = _drop_keys(_CURRENT_CONFIG, "ignored_paths").split("---\n\n", 1)[0] + "---\n" + body
    merged, added, _ = scaffold.merge_config_schema(old, installed_sync)
    assert added == ["ignored_paths"]
    _, merged_body, _ = installed_sync.parse_frontmatter(merged)
    assert merged_body == body


def test_merge_config_schema_round_trips_through_installed_parser():
    old = _drop_keys(_CURRENT_CONFIG, "docs_review_paths", "docs_ignore_paths", "ignored_paths")
    merged, added, _ = scaffold.merge_config_schema(old, installed_sync)
    fields, _, order = installed_sync.parse_frontmatter(merged)
    assert set(order) == set(fields.keys())
    for key in added:
        assert key in fields


def test_merge_config_schema_is_idempotent():
    old = _drop_keys(_CURRENT_CONFIG, "docs_review_paths", "docs_ignore_paths", "ignored_paths")
    once, _, _ = scaffold.merge_config_schema(old, installed_sync)
    twice, added_again, bumped_again = scaffold.merge_config_schema(once, installed_sync)
    assert twice == once
    assert added_again == []
    assert bumped_again is None


def test_merge_config_schema_bumps_workflow_version_when_template_is_higher(monkeypatch):
    real_pairs = scaffold._template_frontmatter_pairs()

    def bumped_pairs():
        return [(k, "2") if k == "workflow_version" else (k, v) for k, v in real_pairs]

    monkeypatch.setattr(scaffold, "_template_frontmatter_pairs", bumped_pairs)
    merged, added, bumped = scaffold.merge_config_schema(_CURRENT_CONFIG, installed_sync)
    assert bumped == 2
    assert "workflow_version: 2" in merged


def test_merge_config_schema_never_touches_a_required_interview_key():
    old = _drop_keys(_CURRENT_CONFIG, "test_command")
    merged, added, _ = scaffold.merge_config_schema(old, installed_sync)
    assert "test_command" not in added
    assert "test_command:" not in merged


# ---------------------------------------------------------------------------
# `merge_settings_hooks` (TASK-038) -- pure function, hand-built fixtures
# ---------------------------------------------------------------------------


_ONE_HOOK_TEMPLATE = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 hooks/a.py"}]},
        ],
    },
}


def test_merge_settings_hooks_adds_everything_to_an_empty_project():
    merged, added = scaffold.merge_settings_hooks({}, _ONE_HOOK_TEMPLATE)
    assert merged == _ONE_HOOK_TEMPLATE
    assert added == ["PreToolUse/'Bash': python3 hooks/a.py"]


def test_merge_settings_hooks_noop_when_project_already_has_everything():
    merged, added = scaffold.merge_settings_hooks(_ONE_HOOK_TEMPLATE, _ONE_HOOK_TEMPLATE)
    assert added == []
    assert merged == _ONE_HOOK_TEMPLATE


def test_merge_settings_hooks_adds_a_missing_group_under_an_existing_event():
    project = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 hooks/b.py"}]},
            ],
        },
    }
    merged, added = scaffold.merge_settings_hooks(project, _ONE_HOOK_TEMPLATE)
    matchers = {g["matcher"] for g in merged["hooks"]["PreToolUse"]}
    assert matchers == {"Bash", "Edit|Write"}
    assert added == ["PreToolUse/'Bash': python3 hooks/a.py"]


def test_merge_settings_hooks_adds_a_missing_hook_to_an_existing_matcher_group():
    project = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 hooks/other.py"}]},
            ],
        },
    }
    merged, added = scaffold.merge_settings_hooks(project, _ONE_HOOK_TEMPLATE)
    bash_group = next(g for g in merged["hooks"]["PreToolUse"] if g["matcher"] == "Bash")
    commands = [h["command"] for h in bash_group["hooks"]]
    assert commands == ["python3 hooks/other.py", "python3 hooks/a.py"]
    assert added == ["PreToolUse/'Bash': python3 hooks/a.py"]


def test_merge_settings_hooks_handles_a_group_with_no_matcher_key():
    template = {
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 hooks/s.py"}]}]},
    }
    merged, added = scaffold.merge_settings_hooks({}, template)
    assert merged == template
    assert added == ["SessionStart/None: python3 hooks/s.py"]

    # A second merge against the same (now-populated) project adds nothing further.
    merged_again, added_again = scaffold.merge_settings_hooks(merged, template)
    assert added_again == []
    assert merged_again == merged


def test_merge_settings_hooks_preserves_a_projects_own_extra_event_group_and_hook():
    project = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 hooks/a.py"},
                        {"type": "command", "command": "python3 .dev/hooks/project_only.py"},
                    ],
                },
            ],
            "PostToolUse": [
                {"hooks": [{"type": "command", "command": "python3 hooks/project_only_post.py"}]},
            ],
        },
    }
    merged, added = scaffold.merge_settings_hooks(project, _ONE_HOOK_TEMPLATE)
    assert added == []
    assert merged == project


def test_merge_settings_hooks_is_idempotent():
    project = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 hooks/other.py"}]},
            ],
        },
    }
    once, _ = scaffold.merge_settings_hooks(project, _ONE_HOOK_TEMPLATE)
    twice, added_second_time = scaffold.merge_settings_hooks(once, _ONE_HOOK_TEMPLATE)
    assert added_second_time == []
    assert twice == once


def test_merge_settings_hooks_does_not_mutate_its_inputs():
    project = {"hooks": {}}
    project_copy = copy.deepcopy(project)
    template_copy = copy.deepcopy(_ONE_HOOK_TEMPLATE)
    scaffold.merge_settings_hooks(project, _ONE_HOOK_TEMPLATE)
    assert project == project_copy
    assert _ONE_HOOK_TEMPLATE == template_copy


# ---------------------------------------------------------------------------
# `migrate-config` subcommand -- real subprocess against a scaffolded target
# ---------------------------------------------------------------------------


def _run_migrate_config(toolkit_source, cwd, *extra_args):
    return subprocess.run(
        [sys.executable, str(_upgrade_script(toolkit_source)), "migrate-config", *extra_args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_migrate_config_preview_reports_added_keys_and_writes_nothing(target, toolkit_source):
    config_path = target / ".tasks" / "config.md"
    config_path.write_text(_drop_keys(config_path.read_text(), "ignored_paths"))
    before = config_path.read_text()

    result = _run_migrate_config(toolkit_source, target)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["added"] == ["ignored_paths"]
    assert output["applied"] is False
    assert "ignored_paths" in output["diff"]
    assert config_path.read_text() == before


def test_migrate_config_apply_writes_and_reruns_sync_check(target, toolkit_source):
    config_path = target / ".tasks" / "config.md"
    config_path.write_text(_drop_keys(config_path.read_text(), "ignored_paths"))

    result = _run_migrate_config(toolkit_source, target, "--apply")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["added"] == ["ignored_paths"]
    assert output["applied"] is True
    assert "ignored_paths: []" in config_path.read_text()

    check = subprocess.run(
        [sys.executable, str(target / ".tasks" / "bin" / "sync"), "check"],
        cwd=target, capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stderr


def test_migrate_config_noop_when_schema_already_current(target, toolkit_source):
    result = _run_migrate_config(toolkit_source, target)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output == {"added": [], "workflow_version_bumped_to": None, "applied": False}


def test_migrate_config_integration_end_to_end_via_upgrade(target, toolkit_source):
    """Full flow (TASK-030's testing strategy step 4): a project scaffolded at an older schema
    (missing template-fixed keys `run` itself never wrote), `upgrade` refreshes the toolkit
    files/sync, then `migrate-config --apply` brings `config.md` up to date -- exactly the
    missing keys appear and nothing else in `config.md` changes.
    """
    config_path = target / ".tasks" / "config.md"
    original = _drop_keys(config_path.read_text(), "docs_review_paths", "docs_ignore_paths", "ignored_paths")
    config_path.write_text(original)

    upgrade_result = _run_upgrade(toolkit_source, target)
    assert upgrade_result.returncode == 0, upgrade_result.stderr
    assert config_path.read_text() == original  # `upgrade` itself never touches config.md

    migrate_result = _run_migrate_config(toolkit_source, target, "--apply")
    assert migrate_result.returncode == 0, migrate_result.stderr
    output = json.loads(migrate_result.stdout)
    assert set(output["added"]) == {"docs_review_paths", "docs_ignore_paths", "ignored_paths"}

    fields, _, _ = installed_sync.parse_frontmatter(config_path.read_text())
    original_fields, _, _ = installed_sync.parse_frontmatter(original)
    for key, value in original_fields.items():
        assert fields[key] == value
    assert fields["docs_review_paths"] == ["CLAUDE.md", "README.md", ".tasks/guidelines.md"]
    assert fields["docs_ignore_paths"] == []
    assert fields["ignored_paths"] == []
