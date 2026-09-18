#!/usr/bin/env python3
"""Deterministic scaffolding for the `init-project` skill.

Everything here is mechanical -- no judgement, no interviewing. `SKILL.md` owns the interview
(asking for `.tasks/config.md`'s values, warning about a missing `gh`) and the human confirmation
STOPs; once the human has approved, the skill writes the confirmed answers to a JSON file and
invokes this script's `run` (fresh project), `upgrade` (refresh an existing one), or
`migrate-config` (additively bring `config.md` up to the current schema) subcommand. Nothing
here prompts interactively.

`run` and `upgrade` share `managed_files()` -- the one table of everything the toolkit manages in
a target project (every portable skill under `.claude/skills/`, plus `guidelines.md`,
`.tasks/templates/*`, the vendored `sync`, and the PR template) -- so the two commands' copy lists
can't drift apart. `run`'s own source is always wherever this script's own repo lives (no clone
needed, skills are assumed already present there); with no `--target`, it keeps its original
behavior of applying only the four non-skill entries (the skill tree it's itself running from is
assumed to already be the target project's own -- installing skills is `upgrade`'s job). Passing
`--target <path>` points `run` at a separate project instead, and applies the full table -- skills
included -- since that's the only way to actually bring them into a project you haven't started a
session inside. `upgrade` clones a real source (also `--target`-aware) and always applies the full
table, hash-classified against `.tasks/.toolkit-manifest.json` so a local edit is never silently
overwritten -- `run --target` reuses that same classification against an empty manifest so a
pre-existing file in a fresh target is never silently overwritten either, `--force` required.

Standard library only -- no third-party dependencies, consistent with `.tasks/bin/sync` itself.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Skills that exist only to maintain this toolkit's own repo -- never copied into another
# project. See `.claude/skills/strip-project-references/SKILL.md` step 0.
_REPO_ONLY_SKILLS = {"strip-project-references"}

DEFAULT_SOURCE = "https://github.com/RobotNerd/sdlc-llm"
DEFAULT_REF = "main"
MANIFEST_NAME = ".toolkit-manifest.json"

# Every key `.tasks/config.md`'s template expects. Keep in sync with
# `templates/config.md`'s `{{placeholder}}`s -- `workflow_version`,
# `allow_auto_merge`, `docs_review_paths`, `docs_ignore_paths`, and
# `ignored_paths` are deliberately absent: SKILL.md never asks about any
# of them, they're fixed by the template itself.
REQUIRED_KEYS = (
    "test_command",
    "lint_command",
    "format_command",
    "docs_paths",
    "default_branch",
    "branch_prefix",
    "remote",
    "rebase_before_pr",
    "merge_strategy",
    "delete_branch_after_merge",
    "ci_checks",
    "archive_done",
)


def _strip_leading_comment(text: str) -> str:
    """Drop a template's leading `<!-- ... -->` instructional comment, if present."""
    return re.sub(r"^<!--.*?-->\n", "", text, count=1, flags=re.DOTALL)


def _yaml_scalar(value) -> str:
    """Render a Python value the way it should appear in config.md's YAML frontmatter --
    bare (unquoted) strings and flow-style lists.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_scalar(v) for v in value) + "]"
    return str(value)


def render_config(answers: dict) -> str:
    """Render `.tasks/config.md`'s content from `templates/config.md` and `answers`.

    Raises `KeyError` if `answers` is missing a required key -- callers should validate
    with `missing_keys` first for a friendlier message.
    """
    text = _strip_leading_comment((TEMPLATES_DIR / "config.md").read_text())
    for key in REQUIRED_KEYS:
        text = text.replace("{{" + key + "}}", _yaml_scalar(answers[key]))
    return text


def missing_keys(answers: dict) -> list[str]:
    return [key for key in REQUIRED_KEYS if key not in answers]


def load_sync_module(sync_path: Path) -> ModuleType:
    """Import a `sync` script by file path -- it has no `.py` suffix so a normal `import`
    can't find it. Same technique `add-task`/`plan-feature`/`implement-task`/`refine-backlog`/
    `review-docs`'s own `scaffold.py` already use. Raises `SystemExit` if `sync_path` doesn't
    exist.
    """
    if not sync_path.is_file():
        raise SystemExit(f"init-project: {sync_path} not found")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def _template_frontmatter_pairs() -> list[tuple[str, str]]:
    """Ordered (key, raw_value) pairs from `templates/config.md`'s frontmatter block, as
    literal text -- not run through `parse_frontmatter`, since a `{{placeholder}}` token
    (an interview-answered `REQUIRED_KEYS` entry) isn't valid YAML on its own.
    """
    text = _strip_leading_comment((TEMPLATES_DIR / "config.md").read_text())
    end = text.index("\n---\n", 4)
    block = text[4:end]
    pairs = []
    for line in block.split("\n"):
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        pairs.append((key.strip(), value.strip()))
    return pairs


def merge_config_schema(project_text: str, sync_module: ModuleType) -> tuple[str, list[str], object]:
    """Additively migrate an existing project's `config.md` to the current template's schema.

    Only ever *adds* keys the project's file lacks -- among the template's fixed keys (every
    template key outside `REQUIRED_KEYS`, since those are interview answers `upgrade` has no
    value for and never invents one for) -- at the template's relative position, with the
    template's own literal default, parsed via `sync_module.parse_frontmatter` itself (a tiny
    synthetic `"---\\nkey: value\\n---\\n"` snippet) rather than a second hand-rolled scalar
    parser -- one parser, used both ways. `workflow_version` is bumped to the template's value
    when the template's is higher. Existing keys, their values, their order, project-added
    extra keys, and the body are left byte-for-byte alone.

    Returns `(merged_text, added_keys, bumped_to)` -- `bumped_to` is `None` unless
    `workflow_version` was bumped. When there is nothing to add or bump, `merged_text` is
    `project_text` itself, untouched -- guarantees true idempotency regardless of any cosmetic
    formatting a full parse/render round-trip might otherwise normalize away.

    Raises `sync_module.FrontmatterError` if `project_text` doesn't parse.
    """
    fields, body, order = sync_module.parse_frontmatter(project_text)
    template_pairs = _template_frontmatter_pairs()
    template_index = {key: i for i, (key, _) in enumerate(template_pairs)}

    new_fields = dict(fields)
    new_order = list(order)
    added: list[str] = []

    for key, raw_value in template_pairs:
        if key in REQUIRED_KEYS or key in new_fields:
            continue
        default_fields, _, _ = sync_module.parse_frontmatter(f"---\n{key}: {raw_value}\n---\n")
        insert_at = 0
        for prev_key, _ in reversed(template_pairs[: template_index[key]]):
            if prev_key in new_order:
                insert_at = new_order.index(prev_key) + 1
                break
        new_order.insert(insert_at, key)
        new_fields[key] = default_fields[key]
        added.append(key)

    bumped_to = None
    template_version_raw = dict(template_pairs)["workflow_version"]
    template_version = sync_module.parse_frontmatter(
        f"---\nworkflow_version: {template_version_raw}\n---\n"
    )[0]["workflow_version"]
    if "workflow_version" in new_fields and template_version > new_fields["workflow_version"]:
        new_fields["workflow_version"] = template_version
        bumped_to = template_version

    if not added and bumped_to is None:
        return project_text, [], None

    merged = sync_module.render_frontmatter(new_fields, new_order) + body
    return merged, added, bumped_to


# Python artifacts the toolkit's own vendored files (`.tasks/bin/sync`, every skill's
# `scaffold.py`, the pytest suite) produce in a target repo -- irrelevant to whether the target
# project itself uses Python, so `init-project` merges these into the target's `.gitignore`
# unconditionally (see `merge_gitignore`).
_GITIGNORE_HEADER = "# Python (added by init-project)"
_GITIGNORE_ENTRIES = ("__pycache__/", "*.py[cod]", ".pytest_cache/")


def _gitignore_entry_key(line: str) -> str | None:
    """Canonicalize a single `.gitignore` line to one of `_GITIGNORE_ENTRIES`, tolerant of the
    common equivalent spellings a hand-written (or another tool's) `.gitignore` might already use
    -- a bare directory name, `**/`-prefixed, `*.pyc` instead of the wildcard-brace form, a
    trailing slash or not. Returns `None` for a blank line, a comment, or anything unrelated to
    those three entries -- the caller only uses this to detect what's already present, never to
    touch other lines.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    bare = stripped[3:] if stripped.startswith("**/") else stripped
    bare = bare.rstrip("/")
    if bare == "__pycache__":
        return "__pycache__/"
    if bare == ".pytest_cache":
        return ".pytest_cache/"
    if stripped in ("*.pyc", "*.py[cod]"):
        return "*.py[cod]"
    return None


def merge_gitignore(project_text: str) -> tuple[str, list[str]]:
    """Additively merge this toolkit's Python-artifact `_GITIGNORE_ENTRIES` into a target
    project's `.gitignore` text (`""` if the project doesn't have one yet).

    Every existing line is scanned (via `_gitignore_entry_key`) for an entry already covering one
    of the three; only the ones genuinely missing are appended, under a single new
    `_GITIGNORE_HEADER` comment line, as their own block after whatever the project already has.
    Nothing already present is reordered, rewritten, or removed -- this is append-only, exactly
    like `merge_settings_hooks` below. Returns `(merged_text, added)` -- `added` is `[]` (and
    `merged_text == project_text`) when every entry is already covered.
    """
    existing = {key for line in project_text.splitlines() if (key := _gitignore_entry_key(line))}
    missing = [entry for entry in _GITIGNORE_ENTRIES if entry not in existing]
    if not missing:
        return project_text, []

    prefix = project_text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix:
        prefix += "\n"  # blank line separating the new block from whatever's already there
    block = "\n".join([_GITIGNORE_HEADER, *missing]) + "\n"
    return prefix + block, missing


def merge_settings_hooks(project: dict, template: dict) -> tuple[dict, list[str]]:
    """Additively merge `template`'s (the toolkit's current `settings.json`) hook registrations
    into `project`'s (a target project's existing `.claude/settings.json`, or `{}` if it has
    none yet).

    For every event (`"PreToolUse"`, `"SessionStart"`, ...) and every matcher-group under it in
    `template`, matched to `project`'s corresponding group by its `matcher` value (including no
    `matcher` key at all, e.g. `SessionStart`'s): a group `project` altogether lacks is appended
    whole; an existing group only gains the individual hook commands it's missing, appended after
    whatever's already there. A hook is identified by its `command` string alone -- if the
    project already has *any* hook with that exact command in that group, it's left untouched, so
    a project's own edit to a shipped hook (a different flag, say) is never duplicated or
    clobbered. Nothing `project` already has -- its own extra events, groups, or hooks -- is ever
    removed or reordered, which is exactly what lets a project keep a guardrail hook of its own
    that no template will ever ship (this toolkit's own repo has one such repo-only hook).

    Returns `(merged, added)` -- `added` is `[]` (and `merged == project`, structurally) when
    `project` already has every hook `template` does.
    """
    merged = copy.deepcopy(project)
    added: list[str] = []
    hooks = merged.setdefault("hooks", {})

    for event, template_groups in template.get("hooks", {}).items():
        project_groups = hooks.setdefault(event, [])
        for template_group in template_groups:
            matcher = template_group.get("matcher")
            project_group = next((g for g in project_groups if g.get("matcher") == matcher), None)
            if project_group is None:
                project_groups.append(copy.deepcopy(template_group))
                added.extend(f"{event}/{matcher!r}: {h['command']}" for h in template_group["hooks"])
                continue
            existing_commands = {h.get("command") for h in project_group.setdefault("hooks", [])}
            for hook in template_group["hooks"]:
                if hook["command"] not in existing_commands:
                    project_group["hooks"].append(copy.deepcopy(hook))
                    added.append(f"{event}/{matcher!r}: {hook['command']}")

    return merged, added


def repo_root() -> Path:
    """The repo root, via `git rev-parse --show-toplevel`. Raises `SystemExit` if the
    current directory isn't inside a git repository at all.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("init-project: not inside a git repository")
    return Path(result.stdout.strip())


# ---------------------------------------------------------------------------
# git plumbing for `source_dir` -- a repo that isn't necessarily the current directory
# (`run`'s own repo, or `upgrade`'s freshly-cloned one)
# ---------------------------------------------------------------------------


def _repo_root_of(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def _resolve_target(target: str | None) -> Path:
    """The project root to scaffold/upgrade: `repo_root()` (the current working directory's git
    root) when `target` is `None`, or the git root containing `target` otherwise -- letting `run`
    and `upgrade` be invoked from this toolkit's own repo against a separate project by path.
    Raises `SystemExit` naming `target` if it doesn't exist or isn't inside a git repository.
    """
    if target is None:
        return repo_root()
    path = Path(target).expanduser()
    if not path.exists():
        raise SystemExit(f"init-project: --target {target} does not exist")
    resolved = _repo_root_of(path)
    if resolved is None:
        raise SystemExit(f"init-project: --target {target} is not inside a git repository")
    return resolved


def _git_remote_url(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "remote", "get-url", "origin"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _git_current_branch(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    branch = result.stdout.strip() if result.returncode == 0 else None
    return branch if branch and branch != "HEAD" else None


def _git_head_commit(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


# ---------------------------------------------------------------------------
# managed_files: the one table `run` and `upgrade` both apply
# ---------------------------------------------------------------------------


def managed_files(source_dir: Path) -> dict[Path, Path]:
    """Every file the toolkit manages in a target project: absolute source path (under
    `source_dir`) -> target path relative to the target repo's root.

    Every file under `source_dir/.claude/skills/<name>/**` for every skill not in
    `_REPO_ONLY_SKILLS` (`__pycache__` excluded), plus the single-file items `run` has always
    copied: `guidelines.md`, the three task/epic/spec templates, `vendored-sync` (->
    `.tasks/bin/sync`), `vendored-guardrails` (-> `.tasks/bin/guardrails.py`), every file under
    `vendored-hooks/` (-> `.claude/hooks/<name>`), `settings.json` (-> `.claude/settings.json`),
    and `pull_request_template.md`. `config.md` and `BOARD.md` are deliberately absent --
    project-owned, never touched by either command.
    """
    files: dict[Path, Path] = {}

    skills_src = source_dir / ".claude" / "skills"
    if skills_src.is_dir():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name in _REPO_ONLY_SKILLS:
                continue
            for path in sorted(skill_dir.rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                files[path] = path.relative_to(source_dir)

    init_project = skills_src / "init-project"
    init_templates = init_project / "templates"
    files[init_templates / "guidelines.md"] = Path(".tasks/guidelines.md")
    for name in ("spec.md", "epic.md", "task.md"):
        files[init_templates / name] = Path(f".tasks/templates/{name}")
    files[init_project / "vendored-sync"] = Path(".tasks/bin/sync")
    files[init_project / "vendored-guardrails"] = Path(".tasks/bin/guardrails.py")
    vendored_hooks = init_project / "vendored-hooks"
    if vendored_hooks.is_dir():
        for path in sorted(vendored_hooks.iterdir()):
            if path.is_file():
                files[path] = Path(".claude/hooks") / path.name
    files[init_templates / "settings.json"] = Path(".claude/settings.json")
    files[init_templates / "pull_request_template.md"] = Path(".github/pull_request_template.md")

    return files


def apply_managed_files(files: dict[Path, Path], root: Path) -> list[Path]:
    """Write every `source -> repo-relative target` pair from `files` under `root`. A self-copy
    (source and target resolve to the same file -- `run`'s own case, where the skill directories
    are already sitting exactly where they'd be copied to) is silently skipped. Returns the
    repo-relative targets actually written.
    """
    written: list[Path] = []
    for source, rel_target in files.items():
        target = root / rel_target
        if source.resolve() == target.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
        if rel_target == Path(".tasks/bin/sync") or rel_target == Path(".tasks/bin/guardrails.py") or rel_target.parts[:2] == (".claude", "hooks"):
            target.chmod(0o755)
        written.append(rel_target)
    return written


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_managed_files(
    files: dict[Path, Path], root: Path, manifest_hashes: dict[str, str]
) -> dict[str, list[Path]]:
    """Classify every managed target under `root` against `manifest_hashes` (the previous
    manifest's `"files"` dict -- `{}` for a pre-manifest project) and the freshly-computed
    source hash:

    - `new`: target doesn't exist yet.
    - `up_to_date`: target already matches the incoming source -- nothing to do.
    - `clean_update`: target matches the last-recorded manifest hash (untouched since the last
      `run`/`upgrade`) -- safe to overwrite with the new source.
    - `locally_modified`: target exists, disagrees with the source, and disagrees with (or has
      no entry in) the manifest -- a real local edit that overwriting would silently destroy.
    """
    result: dict[str, list[Path]] = {"new": [], "up_to_date": [], "clean_update": [], "locally_modified": []}
    for source, rel_target in files.items():
        target = root / rel_target
        if not target.exists():
            result["new"].append(rel_target)
            continue
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if target_hash == source_hash:
            result["up_to_date"].append(rel_target)
            continue
        if manifest_hashes.get(str(rel_target)) == target_hash:
            result["clean_update"].append(rel_target)
        else:
            result["locally_modified"].append(rel_target)
    return result


def _report_conflicts(files: dict[Path, Path], root: Path, locally_modified: list[Path]) -> None:
    """Print a diff for each conflicting managed file to stderr -- shared by `run` and `upgrade`
    so their refusal behavior (and its wording) can't drift apart.
    """
    print(
        "init-project: pre-existing managed files in the target conflict with the incoming "
        "source -- refusing to overwrite:\n",
        file=sys.stderr,
    )
    by_target = {t: s for s, t in files.items()}
    for rel_target in locally_modified:
        target = root / rel_target
        diff = difflib.unified_diff(
            target.read_text(errors="replace").splitlines(keepends=True),
            by_target[rel_target].read_text(errors="replace").splitlines(keepends=True),
            fromfile=str(rel_target),
            tofile=f"{rel_target} (incoming)",
        )
        print("".join(diff), file=sys.stderr)
    print(
        "init-project: re-run with --force to overwrite these, or resolve by hand",
        file=sys.stderr,
    )


def load_manifest(root: Path) -> dict:
    path = root / ".tasks" / MANIFEST_NAME
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def write_manifest(
    root: Path, *, source: str, ref: str, commit: str | None, files: dict[Path, Path]
) -> None:
    manifest = {
        "source": source,
        "ref": ref,
        "commit": commit,
        "updated": date.today().isoformat(),
        "files": {str(rel_target): _sha256(root / rel_target) for rel_target in files.values()},
    }
    (root / ".tasks" / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def cmd_run(args: argparse.Namespace) -> int:
    root = _resolve_target(args.target)
    tasks_dir = root / ".tasks"
    if tasks_dir.is_dir():
        print(
            f"init-project: {tasks_dir} already exists -- refusing to re-initialize "
            "(run `scaffold.py upgrade` instead to refresh an existing setup)",
            file=sys.stderr,
        )
        return 2

    answers = json.loads(Path(args.answers).read_text())
    missing = missing_keys(answers)
    if missing:
        print(
            f"init-project: missing required answer(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2

    # No clone: `run`'s source is always wherever this script's own repo lives. With no
    # `--target`, `run` keeps its original behavior -- only the four non-skill entries, on the
    # assumption the skill tree it's itself running from is already the target project's own
    # (installing skills is `upgrade`'s job, not a fresh `run`'s). `--target` is the one thing
    # that changes that: pointing `run` at a separate project only makes sense if it actually
    # brings the skills along, so the full table (skills included) applies in that case.
    own_repo_root = _repo_root_of(SKILL_DIR) or SKILL_DIR.parent.parent.parent
    if args.target is None:
        files = {s: t for s, t in managed_files(own_repo_root).items() if t.parts[0] != ".claude"}
    else:
        files = managed_files(own_repo_root)

    # `.tasks/` doesn't exist yet (checked above), so there's never a prior manifest to consult --
    # any pre-existing managed file in the target that disagrees with the incoming source is a
    # conflict, exactly like `upgrade`'s own `locally_modified` classification.
    classification = classify_managed_files(files, root, {})
    if classification["locally_modified"] and not args.force:
        _report_conflicts(files, root, classification["locally_modified"])
        return 2

    to_write = set(classification["new"]) | set(classification["up_to_date"]) | set(classification["clean_update"])
    if args.force:
        to_write |= set(classification["locally_modified"])

    (tasks_dir / "bin").mkdir(parents=True, exist_ok=True)
    (tasks_dir / "templates").mkdir(parents=True, exist_ok=True)
    (root / ".github").mkdir(parents=True, exist_ok=True)

    (tasks_dir / "config.md").write_text(render_config(answers))
    (tasks_dir / "BOARD.md").write_text((TEMPLATES_DIR / "board.md").read_text())

    apply_managed_files({s: t for s, t in files.items() if t in to_write}, root)

    # `.gitignore` is project-owned, same as `config.md`/`BOARD.md` -- never in `managed_files()`,
    # never hash-classified. Merged additively regardless of `--target`: the toolkit vendors
    # Python either way, so the target's `.gitignore` needs these entries whether or not the
    # project itself uses Python.
    gitignore_path = root / ".gitignore"
    gitignore_before = gitignore_path.read_text() if gitignore_path.is_file() else ""
    gitignore_text, gitignore_added = merge_gitignore(gitignore_before)
    if gitignore_added:
        gitignore_path.write_text(gitignore_text)

    sync_dst = tasks_dir / "bin" / "sync"
    sync_result = subprocess.run([sys.executable, str(sync_dst)], cwd=root)
    if sync_result.returncode != 0:
        print("init-project: `sync` failed after scaffolding", file=sys.stderr)
        return sync_result.returncode

    check_result = subprocess.run([sys.executable, str(sync_dst), "check"], cwd=root)
    if check_result.returncode != 0:
        print(
            "init-project: `sync check` is not clean immediately after scaffolding -- "
            "this is a bug in this script or in the vendored sync, not something to paper over",
            file=sys.stderr,
        )
        return check_result.returncode

    write_manifest(
        root,
        source=_git_remote_url(own_repo_root) or "local",
        ref=_git_current_branch(own_repo_root) or "local",
        commit=_git_head_commit(own_repo_root),
        files=files,
    )

    gitignore_note = (
        f".gitignore: added {', '.join(gitignore_added)}" if gitignore_added
        else ".gitignore: nothing needed"
    )
    print(f"init-project: scaffolded {tasks_dir} -- sync check is clean -- {gitignore_note}")
    return 0


def cmd_upgrade(args: argparse.Namespace) -> int:
    root = _resolve_target(args.target)
    tasks_dir = root / ".tasks"
    if not tasks_dir.is_dir():
        print(
            f"init-project: {tasks_dir} not found -- run `scaffold.py run` first to bootstrap "
            "a new project; `upgrade` only refreshes an already-initialized one",
            file=sys.stderr,
        )
        return 2

    source = args.source or DEFAULT_SOURCE
    ref = args.ref or DEFAULT_REF

    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "toolkit-source"
        clone_result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, source, str(clone_dir)],
            capture_output=True, text=True,
        )
        if clone_result.returncode != 0:
            print(f"init-project: git clone failed:\n{clone_result.stderr}", file=sys.stderr)
            return clone_result.returncode

        commit = _git_head_commit(clone_dir)
        files = managed_files(clone_dir)

        # `.claude/settings.json` is excluded from the hash-classified table below -- unlike
        # every other managed file, a project can genuinely extend it (its own extra hook
        # registration), and a whole-file hash comparison can't tell "the project edited the
        # shipped content" apart from "the project only ever added to it". It still gets
        # `managed_files()`'s ordinary whole-file copy for a *fresh* `run` (nothing to merge
        # with yet there); `upgrade` alone additively merges it via `merge_settings_hooks`,
        # further down, once the exact same clone has been fetched anyway.
        settings_target = Path(".claude/settings.json")
        settings_source = next((s for s, t in files.items() if t == settings_target), None)
        if settings_source is not None:
            del files[settings_source]

        manifest_hashes = load_manifest(root).get("files", {})
        classification = classify_managed_files(files, root, manifest_hashes)

        settings_hooks_would_add: list[str] = []
        if settings_source is not None:
            template_settings = json.loads(settings_source.read_text())
            settings_path = root / settings_target
            try:
                project_settings = json.loads(settings_path.read_text()) if settings_path.is_file() else {}
            except json.JSONDecodeError as exc:
                print(f"init-project: {settings_path} does not parse as JSON: {exc}", file=sys.stderr)
                return 2
            _, settings_hooks_would_add = merge_settings_hooks(project_settings, template_settings)

        # `.gitignore`, like `.claude/settings.json`, is project-owned and never hash-classified
        # -- additively merged on every `upgrade` too, so a project scaffolded before this merge
        # existed (or one that later deleted the entries by hand) still ends up covered.
        gitignore_path = root / ".gitignore"
        gitignore_before = gitignore_path.read_text() if gitignore_path.is_file() else ""
        _, gitignore_would_add = merge_gitignore(gitignore_before)

        if args.dry_run:
            print(json.dumps({
                **{k: [str(p) for p in v] for k, v in classification.items()},
                "settings_hooks_would_add": settings_hooks_would_add,
                "gitignore_would_add": gitignore_would_add,
            }))
            return 0

        if classification["locally_modified"] and not args.force:
            _report_conflicts(files, root, classification["locally_modified"])
            return 2

        to_write = set(classification["new"]) | set(classification["clean_update"])
        if args.force:
            to_write |= set(classification["locally_modified"])
        apply_managed_files({s: t for s, t in files.items() if t in to_write}, root)
        write_manifest(root, source=source, ref=ref, commit=commit, files=files)

        settings_hooks_added: list[str] = []
        if settings_source is not None and settings_hooks_would_add:
            settings_path = root / settings_target
            project_settings = json.loads(settings_path.read_text()) if settings_path.is_file() else {}
            merged_settings, settings_hooks_added = merge_settings_hooks(project_settings, template_settings)
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(merged_settings, indent=2) + "\n")

        gitignore_added: list[str] = []
        if gitignore_would_add:
            gitignore_text, gitignore_added = merge_gitignore(gitignore_before)
            gitignore_path.write_text(gitignore_text)

        # Captured (unlike `run`'s equivalent calls): `upgrade`'s own stdout is JSON a caller
        # parses, so `sync`'s own chatter must not leak into it.
        sync_dst = tasks_dir / "bin" / "sync"
        sync_result = subprocess.run([sys.executable, str(sync_dst)], cwd=root, capture_output=True, text=True)
        if sync_result.returncode != 0:
            print("init-project: `sync` failed after upgrade", file=sys.stderr)
            print(sync_result.stdout, file=sys.stderr)
            print(sync_result.stderr, file=sys.stderr)
            return sync_result.returncode

        check_result = subprocess.run(
            [sys.executable, str(sync_dst), "check"], cwd=root, capture_output=True, text=True
        )
        if check_result.returncode != 0:
            print(
                "init-project: `sync check` is not clean immediately after upgrade -- "
                "this is a bug in this script or in the vendored sync, not something to paper over",
                file=sys.stderr,
            )
            print(check_result.stdout, file=sys.stderr)
            print(check_result.stderr, file=sys.stderr)
            return check_result.returncode

    print(json.dumps({
        "new": [str(p) for p in classification["new"]],
        "updated": [str(p) for p in classification["clean_update"]],
        "forced": [str(p) for p in classification["locally_modified"]] if args.force else [],
        "up_to_date": len(classification["up_to_date"]),
        "settings_hooks_added": settings_hooks_added,
        "gitignore_added": gitignore_added,
    }))
    return 0


def cmd_migrate_config(args: argparse.Namespace) -> int:
    """Additively migrate `.tasks/config.md` to the current template's schema.

    Deliberately separate from `upgrade` itself: `config.md` is project-owned and never
    hash-classified against the toolkit manifest the way skills/templates/sync are, so it gets
    its own preview-then-`--apply` gate instead -- a bare call only reports what it *would* add
    and writes nothing, so `SKILL.md` can show the human the diff and STOP before anything is
    written for real. Parses/renders via the project's own already-installed
    `.tasks/bin/sync` -- run this after `upgrade` has refreshed it, so the merge is guaranteed
    to write something that same parser accepts.
    """
    root = _resolve_target(args.target)
    tasks_dir = root / ".tasks"
    if not tasks_dir.is_dir():
        print(f"init-project: {tasks_dir} not found -- run `scaffold.py run` first", file=sys.stderr)
        return 2

    sync_module = load_sync_module(tasks_dir / "bin" / "sync")
    config_path = tasks_dir / "config.md"
    project_text = config_path.read_text()

    try:
        merged, added, bumped_to = merge_config_schema(project_text, sync_module)
    except sync_module.FrontmatterError as exc:
        print(f"init-project: {config_path} does not parse: {exc}", file=sys.stderr)
        return 2

    if not added and bumped_to is None:
        print(json.dumps({"added": [], "workflow_version_bumped_to": None, "applied": False}))
        return 0

    if not args.apply:
        diff = "".join(difflib.unified_diff(
            project_text.splitlines(keepends=True),
            merged.splitlines(keepends=True),
            fromfile=str(config_path),
            tofile=f"{config_path} (proposed)",
        ))
        print(json.dumps({
            "added": added,
            "workflow_version_bumped_to": bumped_to,
            "applied": False,
            "diff": diff,
        }))
        return 0

    config_path.write_text(merged)

    sync_dst = tasks_dir / "bin" / "sync"
    sync_result = subprocess.run([sys.executable, str(sync_dst)], cwd=root, capture_output=True, text=True)
    if sync_result.returncode != 0:
        print("init-project: `sync` failed after config migration", file=sys.stderr)
        print(sync_result.stdout, file=sys.stderr)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    check_result = subprocess.run(
        [sys.executable, str(sync_dst), "check"], cwd=root, capture_output=True, text=True
    )
    if check_result.returncode != 0:
        print(
            "init-project: `sync check` is not clean immediately after config migration -- "
            "this is a bug in this script or in the vendored sync, not something to paper over",
            file=sys.stderr,
        )
        print(check_result.stdout, file=sys.stderr)
        print(check_result.stderr, file=sys.stderr)
        return check_result.returncode

    print(json.dumps({"added": added, "workflow_version_bumped_to": bumped_to, "applied": True}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="scaffold .tasks/ into the current repo (or --target) from a confirmed answers file"
    )
    run_parser.add_argument("answers", help="path to a JSON file with the interview answers")
    run_parser.add_argument(
        "--target", help="path to the project to scaffold (default: the current repo)"
    )
    run_parser.add_argument(
        "--force", action="store_true", help="overwrite pre-existing managed files that conflict"
    )

    upgrade_parser = subparsers.add_parser(
        "upgrade", help="refresh an already-initialized project's toolkit files from a source clone"
    )
    upgrade_parser.add_argument(
        "--target", help="path to the project to refresh (default: the current repo)"
    )
    upgrade_parser.add_argument("--source", help=f"git URL or local path (default: {DEFAULT_SOURCE})")
    upgrade_parser.add_argument("--ref", help=f"branch or tag to clone (default: {DEFAULT_REF})")
    upgrade_parser.add_argument(
        "--dry-run", action="store_true", help="report the classification, write nothing"
    )
    upgrade_parser.add_argument(
        "--force", action="store_true", help="overwrite locally-modified managed files too"
    )

    migrate_config_parser = subparsers.add_parser(
        "migrate-config",
        help="additively migrate .tasks/config.md to the current template's schema",
    )
    migrate_config_parser.add_argument(
        "--target", help="path to the project whose config.md to migrate (default: the current repo)"
    )
    migrate_config_parser.add_argument(
        "--apply", action="store_true", help="write the migration (default: preview only)"
    )

    args = parser.parse_args(argv)
    dispatch = {"run": cmd_run, "upgrade": cmd_upgrade, "migrate-config": cmd_migrate_config}
    if args.command in dispatch:
        return dispatch[args.command](args)
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover -- parser.error already exits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
