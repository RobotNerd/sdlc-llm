#!/usr/bin/env python3
"""Deterministic scripting for the `implement-task` skill.

Same shape as `init-project`/`add-task`'s `scaffold.py`: `SKILL.md` owns everything
genuinely judgment-driven -- restating the plan, writing code/tests, deciding what's automatable,
composing commit/PR content, the bail-out call -- and every STOP. Each such step is paired with
exactly one call into this script for the mechanical git/gh/frontmatter/`sync` action that follows
it. Nothing here prompts interactively, and nothing here authors content (commit messages, PR
bodies) -- those arrive as already-composed strings.

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses) rather than re-implementing frontmatter parsing/writing or "what does a
TODO line look like".
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shlex
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

_DONE_STATUSES = ("done", "wont-do")
_IN_FLIGHT_STATUSES = ("in-progress", "in-review")


# ---------------------------------------------------------------------------
# repo / sync module plumbing (same technique as add-task's scaffold.py)
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("implement-task: not inside a git repository")
    return Path(result.stdout.strip())


def discover_or_exit(sync_mod: ModuleType, tasks_root: Path) -> dict:
    """`sync_mod.discover(tasks_root)`, but a malformed task/epic/spec file (`FrontmatterError`,
    whose message already names the file and the problem) becomes a one-line error and a non-zero
    exit instead of a traceback. Never skips the bad file -- it still fails the command.
    """
    try:
        return sync_mod.discover(tasks_root)
    except sync_mod.FrontmatterError as exc:
        raise SystemExit(f"implement-task: {exc}") from None


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"implement-task: {sync_path} not found -- run `init-project` first")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def _run_sync(sync_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(sync_path), *extra_args], capture_output=True, text=True
    )


def load_guardrails_module() -> ModuleType:
    """`.tasks/bin/guardrails.py`, reusing an already-loaded copy (e.g. `tests/conftest.py`'s)
    if present so the hook path and this skill never run two independent instances of the same
    module. Resolved from this script's own location, not any `cwd` argument -- `init-project`
    vendors `scaffold.py` and `guardrails.py` at the same fixed relative offset in every target
    repo, so this holds both here and once vendored.
    """
    if "guardrails" in sys.modules:
        return sys.modules["guardrails"]
    guardrails_path = Path(__file__).resolve().parents[3] / ".tasks" / "bin" / "guardrails.py"
    loader = SourceFileLoader("guardrails", str(guardrails_path))
    spec = importlib.util.spec_from_loader("guardrails", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["guardrails"] = module
    loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# git/gh wrappers -- thin, side-effecting; kept separate from the pure
# decision functions below so those can be unit-tested without real git/gh
# ---------------------------------------------------------------------------


def dirty_files(cwd: Path, ignore: tuple[str, ...] = ()) -> list[str]:
    """Paths `git status` reports as dirty in `cwd`, excluding `ignore` -- the project's own
    `ignored_paths` (`.tasks/config.md`), a carve-out for paths like a personal prompt scratchpad
    that aren't part of any task's actual work. Thin delegate to
    `guardrails.dirty_tree_violation`, which owns the actual `git status`/porcelain-parsing logic
    (and its fail-open-on-broken-git behavior) so it's defined once for both the hook path and
    this skill.
    """
    return load_guardrails_module().dirty_tree_violation(cwd, tuple(ignore))


def current_branch(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def local_branch_exists(cwd: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=cwd
    )
    return result.returncode == 0


def remote_branch_exists(cwd: Path, remote: str, branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", remote, branch],
        cwd=cwd, capture_output=True, text=True,
    )
    return result.returncode == 0


def stage_bookkeeping(cwd: Path) -> subprocess.CompletedProcess:
    """Stage exactly what a bookkeeping commit (`wrap-up`'s `pr:`/`status:` update,
    `finish-merge`'s merge record) owns, and nothing else under `.tasks/`. `git add -u -- .tasks`
    stages modifications and deletions of already-tracked files only -- `BOARD.md`, `EPIC-*.md`,
    the task's own frontmatter, and the deletion side of an archive move -- never a new untracked
    file, so unrelated leftovers in `.tasks/` (say, an in-flight `add-task` run's output) can't
    ride along into a commit that `finish-merge` pushes straight to the default branch.
    `.tasks/archive/` is then added whole: `sync` moves *every* `done` task there, and staging
    only one of them would commit a deletion without its archived copy.
    """
    result = subprocess.run(["git", "add", "-u", "--", ".tasks"], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 or not (cwd / ".tasks" / "archive").is_dir():
        return result
    return subprocess.run(["git", "add", "--", ".tasks/archive"], cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Pure functions -- the four AC7 asks unit tests for, plus their small
# supporting helpers. No git/gh/filesystem I/O in here.
# ---------------------------------------------------------------------------


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a slug from title {title!r}")
    return slug


def compute_branch_name(branch_prefix: str, task_id: str, slug: str) -> str:
    """`<branch_prefix><id-number>-<slug>` (the workflow's branch-naming convention).

    `slug` is not re-derived from the task's full title here -- real task slugs are
    short, hand-chosen summaries (e.g. a title like "implement-task skill: four
    phases, STOP markers, resumable, bail-out" might get the branch
    `task-NNN-skill-implement-task`), not a mechanical `slugify(title)`. This
    function only does the formatting; callers supply the slug -- from an existing
    task's `branch:` field when one's already set (the normal case, since `add-task`
    always sets it at creation), or `slugify(title)` as a last-resort fallback.
    """
    number = task_id.split("-", 1)[1]
    return f"{branch_prefix}{number}-{slug}"


def pick_top_unblocked(board_text: str, sync_mod: ModuleType) -> dict:
    """The TODO-picking rule: read `BOARD.md`'s TODO list top to bottom,
    skip any line carrying `⛔ blocked_by ...`, take the first one that doesn't.
    Returns `{"task_id": id-or-None, "skipped": [{"id", "reason"}, ...]}` -- `None`
    if every TODO task is blocked (or the list is empty).
    """
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise ValueError("no '## TODO' heading found in BOARD.md")
    start = board_text.index(heading) + len(heading)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    lines = [line for line in board_text[start:end].splitlines() if sync_mod._TODO_LINE_RE.match(line)]

    skipped = []
    for line in lines:
        task_id = sync_mod._TODO_LINE_RE.match(line).group(1)
        if "⛔" in line:
            skipped.append({"id": task_id, "reason": line.split("⛔", 1)[1].strip()})
            continue
        return {"task_id": task_id, "skipped": skipped}
    return {"task_id": None, "skipped": skipped}


def stop_required_for_phase1(*, batch_mode: bool) -> bool:
    """Phase 1's announce-vs-block decision, for the autonomous batch mode: outside a batch, the
    plan restatement always ends in a hard STOP (unchanged). Inside an approved batch, the batch
    selection itself was the approval, so the plan is printed for the record but nothing blocks on
    it -- the caller proceeds straight into phase 2.
    """
    return not batch_mode


def record_outcome(outcomes: list[dict], entry: dict) -> list[dict]:
    """Append one task's outcome record to a batch run's accumulator, in encounter order. Returns
    a new list -- `outcomes` itself is never mutated, so a caller can keep holding the prior list.

    `entry` must carry `task_id`/`title`/`status` (a `link` of `None` is fine -- not every status,
    e.g. a task still `in-progress`, has a PR/merge-commit link yet); missing any of the first
    three raises `ValueError` naming it, since a silently incomplete row would make the
    end-of-batch summary misleading.
    """
    for key in ("task_id", "title", "status"):
        if key not in entry:
            raise ValueError(f"outcome entry missing required key: {key!r}")
    return [*outcomes, dict(entry)]


def render_outcome_table(outcomes: list[dict]) -> str:
    """The end-of-batch summary table: `Task | Title | Status | PR/Merge`, one row per outcome in
    accumulation order. An empty batch still renders a header-only table rather than raising --
    the caller always has something to print. A missing/`None` `link` renders as `—` (halted
    before a PR ever opened, or a task the batch skipped).
    """
    lines = ["| Task | Title | Status | PR/Merge |", "|---|---|---|---|"]
    for entry in outcomes:
        link = entry.get("link") or "—"
        lines.append(f"| {entry['task_id']} | {entry['title']} | {entry['status']} | {link} |")
    return "\n".join(lines)


BATCH_STATE_RELPATH = ".tmp/batch-state.json"
AUTO_MERGE_MARKER_RELPATH = ".tmp/auto-merge-marker.json"  # must equal guardrails.AUTO_MERGE_MARKER_RELPATH
_BATCH_STATE_KEYS = ("selection", "order", "accounted", "outcomes")


def batch_state_path(root: Path) -> Path:
    """Where a batch's local, untracked state lives: `.tmp/batch-state.json` under the repo root.
    Pure runtime state (never committed or reviewed), so `.tmp/` -- not `.tasks/`.
    """
    return root / BATCH_STATE_RELPATH


def new_batch_state(selection: dict, order: list[str]) -> dict:
    """A fresh batch's state: the original selection, its resolved `order`, and no progress yet.
    `accounted` lists task ids whose batch turn is over (merged, or bailed out by an isolated
    interrupt); `outcomes` is the same accumulator `record-outcome` builds; `follow_ups` is the
    ledger of follow-up tasks the batch created (or flagged past the limit) -- see
    `record_follow_up`; `critic_reviews` is the auto-merge critic ledger -- see
    `record_critic_review`.
    """
    return {"selection": selection, "order": list(order), "accounted": [], "outcomes": [], "follow_ups": [], "critic_reviews": []}


def write_batch_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def read_batch_state(path: Path) -> dict | None:
    """The batch state at `path`, or `None` if it's absent, unparseable, or missing required keys
    -- a corrupt file is treated as "no batch" rather than crashing every later invocation.
    """
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict) or any(key not in state for key in _BATCH_STATE_KEYS):
        return None
    state.setdefault("follow_ups", [])  # absent in a file written before follow-ups existed
    state.setdefault("critic_reviews", [])  # likewise for the auto-merge critic ledger
    return state


def clear_batch_state(path: Path) -> bool:
    """Delete the state file; returns whether there was one to delete."""
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def advance_batch_state(state: dict, entry: dict, *, accounted: bool) -> dict:
    """Record one task's outcome in `state` (returns a new dict; `state` is never mutated). An
    entry for a task that already has one replaces it in place -- a task's provisional `in-review`
    row becomes its final `done` row rather than a duplicate. `accounted=True` marks the task's
    turn in the batch as over. Raises `ValueError` if `entry`'s task isn't in `order`, or on an
    incomplete entry (same rule as `record_outcome`).
    """
    task_id = entry.get("task_id")
    if task_id not in state["order"]:
        raise ValueError(f"{task_id!r} is not part of this batch's order")
    if any(o["task_id"] == task_id for o in state["outcomes"]):
        outcomes = [dict(entry) if o["task_id"] == task_id else o for o in state["outcomes"]]
    else:
        outcomes = record_outcome(state["outcomes"], entry)
    marked = list(state["accounted"])
    if accounted and task_id not in marked:
        marked.append(task_id)
    return {**state, "accounted": marked, "outcomes": outcomes}


def batch_is_complete(state: dict) -> bool:
    return all(task_id in state["accounted"] for task_id in state["order"])


def batch_progress(state: dict) -> dict:
    """What a resuming session needs: the batch as recorded plus `remaining` (tasks in `order`
    not yet accounted for) and `next_task_id` (the first of them, or `None` if none are left).
    """
    remaining = [t for t in state["order"] if t not in state["accounted"]]
    return {
        "selection": state["selection"], "order": state["order"], "accounted": state["accounted"],
        "remaining": remaining, "next_task_id": remaining[0] if remaining else None,
        "outcomes": state["outcomes"], "follow_ups": state.get("follow_ups", []),
        "critic_reviews": state.get("critic_reviews", []),
    }


DEFAULT_FOLLOW_UP_LIMIT = 3


def _validate_limit(name: str, limit: object) -> None:
    """A per-batch cap read from config must be `None` (unlimited) or a non-negative integer --
    a mistyped value should fail loudly, not silently uncap or disable the batch.
    """
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError(f"{name} must be null or a non-negative integer, got {limit!r}")


def check_follow_up_limit(*, created: int, limit: int | None) -> dict:
    """Whether the batch may autonomously create one more follow-up task, given how many it has
    already created (`created`) and `autonomous_new_task_limit` from `.tasks/config.md` (`limit`).
    `None` means unlimited and never refuses; `0` disables autonomous creation outright. Returns
    `{"allowed": bool, "message": str | None}` -- `message` names the count and the limit, for
    the flagged entry and the summary. Raises `ValueError` on a limit that isn't `None` or a
    non-negative integer: a mistyped config value should fail loudly, not silently uncap or
    disable the batch.
    """
    _validate_limit("autonomous_new_task_limit", limit)
    if limit is None or created < limit:
        return {"allowed": True, "message": None}
    return {
        "allowed": False,
        "message": f"follow-up limit reached: {created} created, autonomous_new_task_limit is {limit}",
    }


def record_follow_up(state: dict, entry: dict) -> dict:
    """Append one follow-up record -- `{task_id, title, why, parent_task_id, created, ...}` -- to
    the batch state's ledger (returns a new dict). `created: False` marks a need that was flagged
    rather than created because the limit was reached.
    """
    return {**state, "follow_ups": [*state.get("follow_ups", []), dict(entry)]}


def count_created_follow_ups(state: dict) -> int:
    return sum(1 for f in state.get("follow_ups", []) if f.get("created"))


def render_follow_up_summary(follow_ups: list[dict]) -> str:
    """The follow-up section of the end-of-batch summary: a table of every task the batch created
    (with why and which task it came from), then a list of the needs it flagged instead because
    the limit was reached, for the human to handle. Both printed even when empty, so a reader
    never has to wonder whether follow-ups were considered.
    """
    created = [f for f in follow_ups if f.get("created")]
    flagged = [f for f in follow_ups if not f.get("created")]
    if not created and not flagged:
        return "Follow-up tasks: none"
    lines = []
    if created:
        lines += [
            f"Follow-up tasks created ({len(created)}):", "",
            "| Task | Title | Why | From |", "|---|---|---|---|",
        ]
        lines += [
            f"| {f['task_id']} | {f['title']} | {f['why']} | {f.get('parent_task_id') or '—'} |"
            for f in created
        ]
    else:
        lines.append("Follow-up tasks created: none")
    if flagged:
        lines += ["", f"Not created -- limit reached, needs a human ({len(flagged)}):", ""]
        lines += [
            f"- {f['title']} -- {f['why']} (from {f.get('parent_task_id') or '—'})" for f in flagged
        ]
    return "\n".join(lines)


def effective_ignored_paths(config: dict) -> tuple[str, ...]:
    """`ignored_paths` from config plus the batch-state file and the auto-merge marker, which
    never count as dirty whether or not the project's `.gitignore` covers them.
    """
    return (*(config.get("ignored_paths") or []), BATCH_STATE_RELPATH, AUTO_MERGE_MARKER_RELPATH)


_BAIL_OUT_HALT_INTERRUPT_KINDS = frozenset({"critic_rejection"})
_ISOLATED_INTERRUPT_KINDS = frozenset({
    "needs_clarification", "unexpected_blocker", "quality_gate_failure", "guardrail_denial",
})
_SYSTEMIC_INTERRUPT_KINDS = frozenset({
    "infra_failure", "context_usage_exceeded", "token_budget_exceeded", "auto_merge_cap_reached",
})


def interrupt_routing(kind: str) -> dict:
    """Route one of batch mode's interrupt conditions: `needs_clarification`/
    `unexpected_blocker`/`quality_gate_failure`/`guardrail_denial` are isolated -- bail out this
    one task and continue the batch at its next task. `infra_failure`/`context_usage_exceeded`/
    `token_budget_exceeded` are systemic -- halt the whole batch before starting anything else,
    since none of them are this task's fault and every remaining task would hit the same wall.
    `auto_merge_cap_reached` is also systemic: the batch's auto-merge cap forces a human
    checkpoint. `critic_rejection` is the one kind that is neither -- `bail_out_halt`: the
    rejected task is bailed out like an isolated one, but the batch ends there
    (`continue_batch: False`) and its artifacts are cleaned up. Raises `ValueError` on any other
    `kind`.
    """
    if kind in _BAIL_OUT_HALT_INTERRUPT_KINDS:
        return {"routing": "bail_out_halt", "continue_batch": False}
    if kind in _ISOLATED_INTERRUPT_KINDS:
        return {"routing": "isolated", "continue_batch": True}
    if kind in _SYSTEMIC_INTERRUPT_KINDS:
        return {"routing": "systemic", "continue_batch": False}
    raise ValueError(f"unknown interrupt kind: {kind!r}")


def check_usage_thresholds(
    *, context_pct: float, halt_pct: float, tokens_used: int, token_budget: int | None
) -> dict:
    """Batch mode's usage safety valve: this harness exposes no tool that reports exact context
    or token usage, so `context_pct`/`tokens_used` are the caller's own best-effort estimate at a
    checkpoint (between tasks, and where practical after phase 2/before phase 3) -- this stays a
    cheap, approximate stopgap on purpose, not a real measurement.

    Context is checked first: `context_pct >= halt_pct` reports `context_usage_exceeded`
    regardless of the token budget. Only when context is fine does a set (non-`None`)
    `token_budget` get checked against `tokens_used`, reporting `token_budget_exceeded`. Returns
    `{"halt": bool, "kind": str | None, "message": str | None}` -- `message` names the specific
    value and threshold crossed, for both `classify-interrupt` and a human reading the halt.
    """
    if context_pct >= halt_pct:
        return {
            "halt": True, "kind": "context_usage_exceeded",
            "message": f"context usage {context_pct:g}% >= halt threshold {halt_pct:g}%",
        }
    if token_budget is not None and tokens_used >= token_budget:
        return {
            "halt": True, "kind": "token_budget_exceeded",
            "message": f"token usage {tokens_used} >= batch budget {token_budget}",
        }
    return {"halt": False, "kind": None, "message": None}


# ---------------------------------------------------------------------------
# Opt-in, critic-gated, capped auto-merge -- the pure logic. The critic itself is a subagent on a
# cheap model launched by SKILL.md's instructions (this script can't call a model); everything
# here is deterministic: the prompt it gets, a strictly fail-closed reading of its answer, the
# fixed order the gates are checked in, and the per-batch cap.
# ---------------------------------------------------------------------------

CRITIC_MAX_DIFF_CHARS = 60000
CRITIC_CHECKLIST = (
    ("criteria_met", "The diff satisfies EVERY acceptance criterion listed below."),
    ("scope_ok", "Every changed file is within the task's declared scope (listed below)."),
    ("gates_passed", "Every quality gate listed below actually passed."),
    ("nothing_alarming", "Nothing alarming: no secrets, no destructive or unrelated changes, no disabled tests or guardrails."),
)


def build_critic_prompt(
    *, task_id: str, title: str, head_sha: str, acceptance_criteria: str, changed_files: list[str],
    scope_paths: list[str], gates: str, diff: str,
) -> str:
    """The prompt for the critic subagent: a narrow, four-item checklist -- deliberately not an
    open-ended code review (that would cost far more, and isn't this gate's job). It gets
    everything it needs inline and must answer with one JSON object; anything it can't verify
    from what's here it must reject.
    """
    truncated = len(diff) > CRITIC_MAX_DIFF_CHARS
    shown_diff = diff[:CRITIC_MAX_DIFF_CHARS] + ("\n[... diff truncated ...]" if truncated else "")
    checklist = "\n".join(f"{n}. `{key}` -- {text}" for n, (key, text) in enumerate(CRITIC_CHECKLIST, start=1))
    keys = ", ".join(f'"{key}": true|false' for key, _ in CRITIC_CHECKLIST)
    return f"""You are the merge gate's critic for {task_id}: {title} (PR head commit {head_sha}).

Answer ONLY the four checklist questions below. This is NOT a general code-quality review: do not
comment on style, naming or design preferences. If you cannot verify an item from what is given
here (for example the diff is truncated), answer false for it -- when in doubt, reject.

Checklist:
{checklist}

Reply with exactly one JSON object and nothing else:
{{"approve": true|false, {keys}, "findings": ["one short string per concern or observation"]}}
`approve` may be true only if all four items are true.

## Acceptance criteria
{acceptance_criteria}

## Declared scope (paths this task may change; `.tasks/` bookkeeping is always allowed)
{chr(10).join(f"- {p}" for p in scope_paths) or "(none declared)"}

## Files changed in the PR
{chr(10).join(f"- {p}" for p in changed_files) or "(none)"}

## Quality gates
{gates}

## Diff
{shown_diff}
"""


def evaluate_critic_verdict(verdict: object) -> dict:
    """Read the critic's answer -- raw text (bare JSON, a fenced block, or JSON inside prose) or an
    already-parsed dict -- and FAIL CLOSED: approval requires a well-formed object with `approve`
    exactly `True`, every checklist item exactly `True`, and `findings` a list of strings.
    Anything else -- unparseable text, a missing or non-boolean field, a false item alongside
    `approve: true` -- is a rejection with a `reason`. Returns
    `{"approve": bool, "checklist": {...}, "findings": [...], "reason": str | None}`.
    """
    def reject(reason: str, checklist: dict | None = None, findings: list | None = None) -> dict:
        return {"approve": False, "checklist": checklist or {}, "findings": findings or [], "reason": reason}

    obj = verdict
    if not isinstance(obj, dict):
        obj = None
        text = verdict if isinstance(verdict, str) else ""
        candidates = [text.strip()]
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            candidates.append(fenced.group(1))
        if "{" in text and "}" in text:
            candidates.append(text[text.index("{"): text.rindex("}") + 1])
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                obj = parsed
                break
        if obj is None:
            return reject("critic verdict is not parseable JSON")

    keys = [key for key, _ in CRITIC_CHECKLIST]
    bad = [key for key in ["approve", *keys] if not isinstance(obj.get(key), bool)]
    if bad:
        return reject(f"critic verdict missing or non-boolean field(s): {', '.join(bad)}")
    findings = obj.get("findings")
    if not isinstance(findings, list) or not all(isinstance(f, str) for f in findings):
        return reject("critic verdict `findings` must be a list of strings")
    checklist = {key: obj[key] for key in keys}
    failed = [key for key, ok in checklist.items() if not ok]
    if failed:
        return reject(f"critic checklist failed: {', '.join(failed)}", checklist, findings)
    if not obj["approve"]:
        return reject("critic did not approve", checklist, findings)
    return {"approve": True, "checklist": checklist, "findings": findings, "reason": None}


def pr_checks_state(returncode: int) -> str:
    """`gh pr checks`'s exit code as a state: `0` all passing -> `green`; `8` still running ->
    `pending`; anything else (a failure, or no checks reported at all) -> `not_green`. Only
    `green` can ever auto-merge -- an absent CI is not a passing CI.
    """
    if returncode == 0:
        return "green"
    if returncode == 8:
        return "pending"
    return "not_green"


def scope_violations(changed_files: list[str], scope_paths: list[str]) -> list[str]:
    """PR-changed files that are neither declared task scope nor `.tasks/` bookkeeping (the
    board, epics, the task file, archive, follow-up task files). A deterministic backstop for the
    critic's own scope check.
    """
    allowed = set(scope_paths)
    return [f for f in changed_files if f not in allowed and not f.startswith(".tasks/")]


def check_merge_cap(*, merged: int, cap: int | None) -> dict:
    """Whether the batch may auto-merge one more task, given how many it already has and
    `autonomous_merge_cap` (`None` = unlimited, `0` = never). Same `{"allowed", "message"}` shape
    and loud-on-bad-config behavior as `check_follow_up_limit`.
    """
    _validate_limit("autonomous_merge_cap", cap)
    if cap is None or merged < cap:
        return {"allowed": True, "message": None}
    return {
        "allowed": False,
        "message": f"auto-merge cap reached: {merged} auto-merged, autonomous_merge_cap is {cap}",
    }


def evaluate_auto_merge_gates(
    *, allow_auto_merge: object, cap_allowed: bool, checks_state: str,
    scope_violations: list[str], verdict_approve: bool,
) -> dict:
    """The auto-merge gates in their fixed priority order -- the first that blocks names the
    `reason`: `disabled` (project didn't opt in), `cap_reached` (a human checkpoint is forced
    *regardless* of the critic or CI, and the only one that also `halt`s the batch),
    `checks_pending` / `checks_not_green`, `scope_violation`, `critic_rejected`. Everything
    passing returns `{"proceed": True, ...}`. Returns `{"proceed", "reason", "halt"}`.
    """
    if allow_auto_merge is not True:
        return {"proceed": False, "reason": "disabled", "halt": False}
    if not cap_allowed:
        return {"proceed": False, "reason": "cap_reached", "halt": True}
    if checks_state == "pending":
        return {"proceed": False, "reason": "checks_pending", "halt": False}
    if checks_state != "green":
        return {"proceed": False, "reason": "checks_not_green", "halt": False}
    if scope_violations:
        return {"proceed": False, "reason": "scope_violation", "halt": False}
    if not verdict_approve:
        return {"proceed": False, "reason": "critic_rejected", "halt": False}
    return {"proceed": True, "reason": None, "halt": False}


def record_critic_review(state: dict, entry: dict) -> dict:
    """Append one critic-review record (`{task_id, pr, head_sha, approve, findings, checklist,
    outcome}`; `outcome` is `auto_merged`, `critic_rejected` or `skipped:<reason>`) to the batch
    state's ledger -- returns a new dict.
    """
    return {**state, "critic_reviews": [*state.get("critic_reviews", []), dict(entry)]}


def count_auto_merged(state: dict) -> int:
    return sum(1 for r in state.get("critic_reviews", []) if r.get("outcome") == "auto_merged")


def render_critic_summary(reviews: list[dict]) -> str:
    """The critic-findings section of the end-of-batch summary: one row per reviewed task --
    including the ones it approved, since that's the signal on whether the critic earns its cost.
    """
    if not reviews:
        return "Critic reviews: none"
    lines = ["Critic reviews:", "", "| Task | Outcome | Findings |", "|---|---|---|"]
    for review in reviews:
        findings = "; ".join(review.get("findings") or []) or "—"
        lines.append(f"| {review['task_id']} | {review['outcome']} | {findings} |")
    return "\n".join(lines)


def render_batch_result(*, order: list[str], outcomes: list[dict], halt: dict | None) -> str:
    """The headline of the end-of-batch summary: how many tasks the batch started with, how many
    completed (merged, i.e. outcome status `done`), and -- if it ended early -- which task ended
    it and why, plus the tasks that never started. `halt` is `None` for a batch that ran to
    completion, else `{"task_id", "kind", "reason"}`.
    """
    completed = [o for o in outcomes if o.get("status") == "done"]
    noun = "task" if len(order) == 1 else "tasks"
    lines = [f"Batch: {len(order)} {noun} selected, {len(completed)} completed."]
    if halt is not None:
        lines.append(f"Ended early at {halt['task_id']} ({halt['kind']}): {halt['reason']}")
        seen = {o["task_id"] for o in outcomes} | {halt["task_id"]}
        never_started = [t for t in order if t not in seen]
        if never_started:
            lines.append(f"Never started: {', '.join(never_started)}")
    return "\n".join(lines)


class TranscriptError(Exception):
    """A session transcript couldn't be read or understood -- missing file, unparseable line, or
    nothing recognisable inside. Expected whenever Claude Code's own (undocumented) transcript
    format changes, so callers report it plainly rather than treating it as a bug.
    """


_TOKEN_FIELDS = (
    "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
)


def compute_session_token_usage(transcript_path: Path) -> dict:
    """Exact cumulative token usage for a Claude Code session, summed from its transcript JSONL
    (`~/.claude/projects/<escaped-cwd>/<session-id>.jsonl`) -- ccstatusline's own
    `getTokenMetrics` algorithm: keep lines carrying `message.usage`; drop streaming partials (an
    entry with no `stop_reason` is an intermediate snapshot of a message whose final entry
    follows), except a trailing one, which is the turn still in progress; sum
    `input_tokens` + `output_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`.

    Returns `{"tokens_used": total, <each field>: its sum}`. Lines without `message.usage`
    (user turns, summaries, blank lines) are normal and skipped; a line that isn't valid JSON, or
    a transcript with no usage entries at all, raises `TranscriptError` -- both signal a format
    change rather than routine noise.
    """
    try:
        text = Path(transcript_path).read_text()
    except FileNotFoundError:
        raise TranscriptError(f"transcript not found: {transcript_path}") from None
    except OSError as exc:
        raise TranscriptError(f"transcript unreadable: {transcript_path}: {exc}") from None

    entries: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise TranscriptError(f"transcript line {lineno} is not valid JSON: {exc}") from None
        message = record.get("message") if isinstance(record, dict) else None
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            entries.append(message)
    if not entries:
        raise TranscriptError(
            f"no message.usage entries found in {transcript_path} -- transcript format changed?"
        )

    kept = [m for m in entries[:-1] if m.get("stop_reason")] + [entries[-1]]
    totals = {field: sum(int(m["usage"].get(field) or 0) for m in kept) for field in _TOKEN_FIELDS}
    return {"tokens_used": sum(totals.values()), **totals}


def render_usage_summary(*, context_pct: float, tokens_used: int, token_budget: int | None) -> str:
    """A one-line usage report for the end-of-batch summary -- printed every time, regardless of
    whether either threshold was ever crossed, so a human can judge whether an opt-in
    critic/auto-merge path is worth its cost on their plan tier.
    """
    budget_text = "no cap" if token_budget is None else str(token_budget)
    return f"Usage: context {context_pct:g}% · tokens {tokens_used} (budget: {budget_text})"


def resume_phase(*, in_flight: dict | None, working_tree_dirty: bool, gh_pr_state: str | None) -> dict:
    """The resume-detection table, as a pure function of already-gathered
    state (no git/gh calls in here -- see `cmd_resume_state` for the real gathering).

    `in_flight` is `None` (no in-progress/in-review task at all) or
    `{"id", "status", "pr", "merge_commit", "branch_exists"}` for the one task
    currently in flight. `gh_pr_state` is `"OPEN"` | `"MERGED"` | `"CLOSED"` | `None`
    (not fetched -- no `pr` yet, or `status` isn't `in-review`).

    Returns `{"phase": ..., "task_id": ..., "detail": ...}` -- `phase` is one of
    `phase1` | `phase2` | `phase3` | `phase4_open` | `phase4_merged` |
    `phase4_closed_not_merged` | `ambiguous` (with `detail` explaining why on the
    last one; surface this to the human rather than guess).
    """
    if in_flight is None or not in_flight.get("branch_exists"):
        return {"phase": "phase1"}

    task_id = in_flight["id"]
    status = in_flight["status"]
    pr = in_flight.get("pr")

    if status == "in-progress":
        if pr:
            return {"phase": "ambiguous", "task_id": task_id, "detail": "in-progress but pr is already set"}
        if working_tree_dirty:
            return {"phase": "phase2", "task_id": task_id}
        return {"phase": "phase3", "task_id": task_id}

    if status == "in-review":
        if not pr:
            return {"phase": "ambiguous", "task_id": task_id, "detail": "in-review with no pr recorded"}
        if gh_pr_state == "OPEN":
            return {"phase": "phase4_open", "task_id": task_id}
        if gh_pr_state == "MERGED":
            if in_flight.get("merge_commit"):
                return {
                    "phase": "ambiguous",
                    "task_id": task_id,
                    "detail": "merge_commit already recorded but status is still in-review",
                }
            return {"phase": "phase4_merged", "task_id": task_id}
        if gh_pr_state == "CLOSED":
            return {"phase": "phase4_closed_not_merged", "task_id": task_id}
        return {"phase": "ambiguous", "task_id": task_id, "detail": f"unexpected gh pr state {gh_pr_state!r}"}

    return {"phase": "ambiguous", "task_id": task_id, "detail": f"unexpected task status {status!r}"}


def decide_push_args(
    *, current_branch: str, task_branch: str, default_branch: str, remote: str, force: bool
) -> list[str]:
    """The `git push` argument list for phase 3's push -- plain, or
    `--force-with-lease` when `force` (a rebase actually rewrote already-pushed
    history). Raises `ValueError` -- refusing to build the command at all -- if
    `current_branch` isn't `task_branch` (guardrail: force-with-lease, and this push
    in general, only on the task's own branch) or if that branch is the default
    branch (never push task work to `default_branch`).
    """
    if current_branch != task_branch:
        raise ValueError(
            f"refusing to push: current branch {current_branch!r} is not this task's own "
            f"branch {task_branch!r}"
        )
    if current_branch == default_branch:
        raise ValueError(f"refusing to push task work to the default branch {default_branch!r}")
    args = ["push"]
    if force:
        args.append("--force-with-lease")
    args += [remote, current_branch]
    return args


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_resume_state(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    ignored_paths = effective_ignored_paths(config)

    artifacts = discover_or_exit(sync_mod, tasks_root)
    in_flight_tasks = [
        a for a in artifacts.values() if a.kind == "task" and a.fields.get("status") in _IN_FLIGHT_STATUSES
    ]
    if len(in_flight_tasks) > 1:
        print(json.dumps({
            "phase": "ambiguous",
            "detail": f"multiple in-flight tasks: {', '.join(sorted(t.id for t in in_flight_tasks))}",
        }))
        return 0

    in_flight = None
    if in_flight_tasks:
        task = in_flight_tasks[0]
        branch = task.fields.get("branch")
        exists = bool(branch) and (
            local_branch_exists(root, branch) or remote_branch_exists(root, remote, branch)
        )
        in_flight = {
            "id": task.id,
            "status": task.fields.get("status"),
            "pr": task.fields.get("pr"),
            "merge_commit": task.fields.get("merge_commit"),
            "branch_exists": exists,
        }

    working_dirty = bool(dirty_files(root, ignore=ignored_paths))

    gh_pr_state = None
    if in_flight and in_flight["status"] == "in-review" and in_flight["pr"]:
        view = subprocess.run(
            ["gh", "pr", "view", in_flight["pr"], "--json", "state,mergeCommit"],
            cwd=root, capture_output=True, text=True,
        )
        if view.returncode != 0:
            print(json.dumps({
                "phase": "ambiguous",
                "task_id": in_flight["id"],
                "detail": f"gh pr view failed: {view.stderr.strip()}",
            }))
            return 0
        gh_pr_state = json.loads(view.stdout)["state"]

    result = resume_phase(in_flight=in_flight, working_tree_dirty=working_dirty, gh_pr_state=gh_pr_state)
    batch = read_batch_state(batch_state_path(root))
    if batch is not None:
        result = {**result, "batch": batch_progress(batch)}
    print(json.dumps(result))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers.get("task_id")
    batch_mode = bool(answers.get("batch_mode", False))

    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    branch_prefix = config.get("branch_prefix", "task-")
    ignored_paths = effective_ignored_paths(config)

    dirty = dirty_files(root, ignore=ignored_paths)
    if dirty:
        print(f"implement-task: working tree is dirty: {', '.join(dirty)}", file=sys.stderr)
        return 2

    skipped: list[dict] = []
    if task_id is None:
        board_text = (tasks_root / "BOARD.md").read_text()
        picked = pick_top_unblocked(board_text, sync_mod)
        skipped = picked["skipped"]
        task_id = picked["task_id"]
        if task_id is None:
            print("implement-task: no unblocked TODO task found", file=sys.stderr)
            return 2

    artifacts = discover_or_exit(sync_mod, tasks_root)
    if task_id not in artifacts or artifacts[task_id].kind != "task":
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    if task.fields.get("status") != "todo":
        print(
            f"implement-task: {task_id} status is {task.fields.get('status')!r}, not 'todo' -- "
            "this looks like a resume, not a fresh start; use `resume-state` instead",
            file=sys.stderr,
        )
        return 2
    outstanding = [
        b for b in (task.fields.get("blocked_by") or [])
        if b not in artifacts or artifacts[b].fields.get("status") not in _DONE_STATUSES
    ]
    if outstanding:
        print(f"implement-task: {task_id} is still blocked by: {', '.join(outstanding)}", file=sys.stderr)
        return 2

    branch = task.fields.get("branch") or compute_branch_name(
        branch_prefix, task_id, slugify(task.fields.get("title", task_id))
    )

    fetch = subprocess.run(["git", "fetch", remote], cwd=root, capture_output=True, text=True)
    if fetch.returncode != 0:
        print(fetch.stderr, file=sys.stderr)
        return fetch.returncode
    checkout = subprocess.run(
        ["git", "checkout", "-b", branch, f"{remote}/{default_branch}"],
        cwd=root, capture_output=True, text=True,
    )
    if checkout.returncode != 0:
        print(checkout.stderr, file=sys.stderr)
        return checkout.returncode

    task.fields["status"] = "in-progress"
    task.fields["branch"] = branch
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    print(json.dumps({
        "task_id": task_id, "branch": branch, "skipped": skipped,
        "stop_required": stop_required_for_phase1(batch_mode=batch_mode),
    }))
    return 0


def cmd_wrap_up(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]
    paths = answers["paths"]

    artifacts = discover_or_exit(sync_mod, tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    branch = task.fields.get("branch")
    if not branch:
        print(f"implement-task: {task_id} has no branch set", file=sys.stderr)
        return 2

    cur = current_branch(root)
    if cur != branch:
        print(
            f"implement-task: current branch {cur!r} is not {task_id}'s branch {branch!r}",
            file=sys.stderr,
        )
        return 2

    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    rebase_before_pr = config.get("rebase_before_pr", True)
    ignored_paths = effective_ignored_paths(config)
    format_command = config.get("format_command")

    add_result = subprocess.run(["git", "add", "-A", "--", *paths], cwd=root, capture_output=True, text=True)
    if add_result.returncode != 0:
        print(add_result.stderr, file=sys.stderr)
        return add_result.returncode

    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        commit_result = subprocess.run(
            ["git", "commit", "-m", answers["commit_message"]], cwd=root, capture_output=True, text=True
        )
        if commit_result.returncode != 0:
            print(commit_result.stderr, file=sys.stderr)
            return commit_result.returncode

    remote_existed_before_rebase = remote_branch_exists(root, remote, branch)

    if rebase_before_pr:
        all_dirty = dirty_files(root, ignore=())
        dirty_ignored_paths = [p for p in ignored_paths if p in all_dirty]
        stashed = False
        if dirty_ignored_paths:
            # `-u`: an ignored path may never have been committed yet (git otherwise refuses to
            # stash a pathspec matching only untracked files).
            stash_result = subprocess.run(
                ["git", "stash", "push", "-u", "-m", "ignored-paths wip", "--", *dirty_ignored_paths],
                cwd=root, capture_output=True, text=True,
            )
            if stash_result.returncode != 0:
                print(stash_result.stderr, file=sys.stderr)
                return stash_result.returncode
            stashed = True

        fetch = subprocess.run(["git", "fetch", remote], cwd=root, capture_output=True, text=True)
        if fetch.returncode != 0:
            print(fetch.stderr, file=sys.stderr)
            return fetch.returncode

        rebase_result = subprocess.run(
            ["git", "rebase", f"{remote}/{default_branch}"], cwd=root, capture_output=True, text=True
        )
        if rebase_result.returncode != 0:
            print(rebase_result.stdout)
            print(rebase_result.stderr, file=sys.stderr)
            print(
                "implement-task: rebase conflict -- resolve it by hand, then `git rebase --continue`"
                + (" and `git stash pop`" if stashed else "") + ", and re-run wrap-up",
                file=sys.stderr,
            )
            return rebase_result.returncode

        if stashed:
            pop_result = subprocess.run(["git", "stash", "pop"], cwd=root, capture_output=True, text=True)
            if pop_result.returncode != 0:
                print(pop_result.stderr, file=sys.stderr)
                return pop_result.returncode

    amended = False
    if format_command:
        format_result = subprocess.run(
            format_command, shell=True, cwd=root, capture_output=True, text=True
        )
        if format_result.returncode != 0:
            print(format_result.stdout)
            print(format_result.stderr, file=sys.stderr)
            print(
                f"implement-task: format_command {format_command!r} exited "
                f"{format_result.returncode} -- STOP, resolve by hand and re-run wrap-up",
                file=sys.stderr,
            )
            return format_result.returncode

        formatted = dirty_files(root, ignore=ignored_paths)
        if formatted:
            format_add = subprocess.run(
                ["git", "add", "-A", "--", *formatted], cwd=root, capture_output=True, text=True
            )
            if format_add.returncode != 0:
                print(format_add.stderr, file=sys.stderr)
                return format_add.returncode
            amend_result = subprocess.run(
                ["git", "commit", "--amend", "--no-edit"], cwd=root, capture_output=True, text=True
            )
            if amend_result.returncode != 0:
                print(amend_result.stderr, file=sys.stderr)
                return amend_result.returncode
            amended = True

    push_args = decide_push_args(
        current_branch=current_branch(root),
        task_branch=branch,
        default_branch=default_branch,
        remote=remote,
        # An amend rewrites history exactly like a rebase would -- if this branch was already
        # pushed by an earlier, interrupted `wrap-up` run, a plain push would now be rejected.
        force=(rebase_before_pr or amended) and remote_existed_before_rebase,
    )
    push_result = subprocess.run(["git", *push_args], cwd=root, capture_output=True, text=True)
    if push_result.returncode != 0:
        print(push_result.stderr, file=sys.stderr)
        return push_result.returncode

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as body_file:
        body_file.write(answers["pr_body"])
        body_path = Path(body_file.name)
    try:
        pr_create = subprocess.run(
            ["gh", "pr", "create", "--title", answers["pr_title"], "--body-file", str(body_path)],
            cwd=root, capture_output=True, text=True,
        )
    finally:
        body_path.unlink(missing_ok=True)
    if pr_create.returncode != 0:
        print(pr_create.stderr, file=sys.stderr)
        return pr_create.returncode
    pr_url = pr_create.stdout.strip().splitlines()[-1]

    task.fields["pr"] = pr_url
    task.fields["status"] = "in-review"
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    # Commit+push the pr:/status: in-review update and sync's regenerated board/epic --
    # otherwise this sits as uncommitted local drift and the PR's own diff never reflects
    # it (found for real: `wrap-up` reported success, but `git status` immediately
    # after showed this exact change uncommitted).
    bookkeeping_add = stage_bookkeeping(root)
    if bookkeeping_add.returncode != 0:
        print(bookkeeping_add.stderr, file=sys.stderr)
        return bookkeeping_add.returncode
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        bookkeeping_commit = subprocess.run(
            ["git", "commit", "-m", answers["bookkeeping_commit_message"]],
            cwd=root, capture_output=True, text=True,
        )
        if bookkeeping_commit.returncode != 0:
            print(bookkeeping_commit.stderr, file=sys.stderr)
            return bookkeeping_commit.returncode
        bookkeeping_push_args = decide_push_args(
            current_branch=current_branch(root), task_branch=branch,
            default_branch=default_branch, remote=remote, force=False,
        )
        bookkeeping_push = subprocess.run(
            ["git", *bookkeeping_push_args], cwd=root, capture_output=True, text=True
        )
        if bookkeeping_push.returncode != 0:
            print(bookkeeping_push.stderr, file=sys.stderr)
            return bookkeeping_push.returncode

    checks = subprocess.run(["gh", "pr", "checks", pr_url], cwd=root, capture_output=True, text=True)
    print(json.dumps({
        "pr_url": pr_url,
        "checks_output": checks.stdout + checks.stderr,
        "checks_exit": checks.returncode,
    }))
    return 0


def cmd_finish_merge(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]

    artifacts = discover_or_exit(sync_mod, tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    pr = task.fields.get("pr")
    if not pr:
        print(f"implement-task: {task_id} has no pr recorded", file=sys.stderr)
        return 2

    view = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "state,mergeCommit"], cwd=root, capture_output=True, text=True
    )
    if view.returncode != 0:
        print(view.stderr, file=sys.stderr)
        return view.returncode
    data = json.loads(view.stdout)
    state = data["state"]
    if state != "MERGED":
        checks = subprocess.run(["gh", "pr", "checks", pr], cwd=root, capture_output=True, text=True)
        print(json.dumps({
            "merged": False,
            "state": state,
            "checks_output": checks.stdout + checks.stderr,
        }))
        return 0

    merge_commit = data["mergeCommit"]["oid"]
    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    delete_after = config.get("delete_branch_after_merge", True)
    branch = task.fields.get("branch")

    checkout = subprocess.run(["git", "checkout", default_branch], cwd=root, capture_output=True, text=True)
    if checkout.returncode != 0:
        print(checkout.stderr, file=sys.stderr)
        return checkout.returncode
    pull = subprocess.run(["git", "pull", "--ff-only"], cwd=root, capture_output=True, text=True)
    if pull.returncode != 0:
        print(pull.stderr, file=sys.stderr)
        return pull.returncode

    task.fields["status"] = "done"
    task.fields["merge_commit"] = merge_commit
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    if delete_after and branch:
        del_local = subprocess.run(["git", "branch", "-d", branch], cwd=root, capture_output=True, text=True)
        if del_local.returncode != 0:
            # a squash merge isn't a fast-forward ancestor of local HEAD; `gh pr
            # view` already confirmed it's genuinely MERGED, so force-deleting the
            # local branch is safe.
            del_local = subprocess.run(["git", "branch", "-D", branch], cwd=root, capture_output=True, text=True)
            if del_local.returncode != 0:
                print(del_local.stderr, file=sys.stderr)
                return del_local.returncode
        del_remote = subprocess.run(
            ["git", "push", remote, "--delete", branch], cwd=root, capture_output=True, text=True
        )
        if del_remote.returncode != 0 and "remote ref does not exist" not in del_remote.stderr:
            print(del_remote.stderr, file=sys.stderr)
            return del_remote.returncode

    check_result = _run_sync(tasks_root / "bin" / "sync", "check")
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr, file=sys.stderr)
        return check_result.returncode

    if current_branch(root) != default_branch:
        print(
            f"implement-task: not on {default_branch!r} -- refusing to run the bookkeeping commit",
            file=sys.stderr,
        )
        return 2
    add_result = stage_bookkeeping(root)
    if add_result.returncode != 0:
        print(add_result.stderr, file=sys.stderr)
        return add_result.returncode
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        commit_result = subprocess.run(
            ["git", "commit", "-m", answers["bookkeeping_commit_message"]],
            cwd=root, capture_output=True, text=True,
        )
        if commit_result.returncode != 0:
            print(commit_result.stderr, file=sys.stderr)
            return commit_result.returncode
        push_result = subprocess.run(
            ["git", "push", remote, default_branch], cwd=root, capture_output=True, text=True
        )
        if push_result.returncode != 0:
            print(push_result.stderr, file=sys.stderr)
            return push_result.returncode

    print(json.dumps({"merged": True, "merge_commit": merge_commit}))
    return 0


def cmd_bail_out(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]
    status = answers["status"]
    if status not in ("todo", "blocked"):
        print(f"implement-task: bail-out status must be 'todo' or 'blocked', got {status!r}", file=sys.stderr)
        return 2

    artifacts = discover_or_exit(sync_mod, tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    task.fields["status"] = status
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    print(json.dumps({"task_id": task_id, "status": status}))
    return 0


def cmd_record_outcome(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    try:
        outcomes = record_outcome(answers.get("outcomes") or [], answers["entry"])
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"outcomes": outcomes}))
    return 0


def cmd_batch_init(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    state = new_batch_state(answers["selection"], answers["order"])
    write_batch_state(batch_state_path(repo_root()), state)
    print(json.dumps(batch_progress(state)))
    return 0


def cmd_batch_update(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    path = batch_state_path(repo_root())
    state = read_batch_state(path)
    if state is None:
        print("implement-task: no active batch state to update", file=sys.stderr)
        return 2
    try:
        state = advance_batch_state(state, answers["entry"], accounted=bool(answers.get("accounted", False)))
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    if batch_is_complete(state):
        clear_batch_state(path)
        print(json.dumps({
            "complete": True, "outcomes": state["outcomes"], "follow_ups": state["follow_ups"],
            "critic_reviews": state["critic_reviews"],
        }))
        return 0
    write_batch_state(path, state)
    print(json.dumps({"complete": False, **batch_progress(state)}))
    return 0


_FOLLOW_UP_REQUIRED = ("title", "type", "why", "parent_task_id")


def cmd_create_follow_up(args: argparse.Namespace) -> int:
    """Create one follow-up task mid-batch via `add-task`'s own `run` (id allocation, task file,
    `sync`, TODO placement, `sync check`) -- or, once `autonomous_new_task_limit` is reached,
    create nothing and flag the need in the batch state instead. Reaching the limit is an
    isolated condition: exit 0, the batch keeps going.
    """
    answers = json.loads(Path(args.answers).read_text())
    missing = [key for key in _FOLLOW_UP_REQUIRED if not answers.get(key)]
    if missing:
        print(f"implement-task: create-follow-up missing required answer(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    root = repo_root()
    tasks_root = root / ".tasks"
    state_path = batch_state_path(root)
    state = read_batch_state(state_path)
    if state is None:
        print("implement-task: create-follow-up needs an active batch (no batch state found)", file=sys.stderr)
        return 2

    sync_mod = load_sync_module(tasks_root)
    limit = sync_mod.load_config(tasks_root).get("autonomous_new_task_limit", DEFAULT_FOLLOW_UP_LIMIT)
    try:
        verdict = check_follow_up_limit(created=count_created_follow_ups(state), limit=limit)
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2

    entry = {
        "task_id": None, "title": answers["title"], "why": answers["why"],
        "parent_task_id": answers["parent_task_id"], "created": False,
    }
    if not verdict["allowed"]:
        write_batch_state(state_path, record_follow_up(state, entry))
        print(json.dumps({"created": False, "flagged": True, "message": verdict["message"]}))
        return 0

    add_task_script = Path(__file__).resolve().parents[1] / "add-task" / "scaffold.py"
    if not add_task_script.is_file():
        raise SystemExit(f"implement-task: {add_task_script} not found -- the add-task skill is required")
    task_id = sync_mod.next_id(tasks_root, "task")
    add_answers = {
        "title": answers["title"], "type": answers["type"], "epic": answers.get("epic"),
        "blocked_by": answers.get("blocked_by") or [], "priority_mode": answers.get("priority_mode") or "end",
    }
    for optional in ("priority_after", "slug"):
        if answers.get(optional):
            add_answers[optional] = answers[optional]
    with tempfile.TemporaryDirectory() as tmp:
        add_answers_path = Path(tmp) / "add-task-answers.json"
        add_answers_path.write_text(json.dumps(add_answers))
        result = subprocess.run(
            [sys.executable, str(add_task_script), "run", str(add_answers_path)],
            cwd=root, capture_output=True, text=True,
        )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    written = sorted(tasks_root.glob(f"{task_id}-*.md"))
    if len(written) != 1:
        print(f"implement-task: add-task reported success but {task_id} was not written", file=sys.stderr)
        return 1

    rel_path = str(written[0].relative_to(root))
    state = record_follow_up(state, {**entry, "task_id": task_id, "created": True, "path": rel_path})
    write_batch_state(state_path, state)
    print(json.dumps({
        "created": True, "task_id": task_id, "path": rel_path,
        "follow_ups_created": count_created_follow_ups(state), "limit": limit,
    }))
    return 0


def cmd_render_follow_up_summary(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    print(json.dumps({"summary": render_follow_up_summary(answers.get("follow_ups") or [])}))
    return 0


DEFAULT_MERGE_CAP = 5
_MERGE_STRATEGY_FLAGS = {"squash": "--squash", "merge": "--merge", "rebase": "--rebase"}
_REASON_INTERRUPTS = {"critic_rejected": "critic_rejection", "cap_reached": "auto_merge_cap_reached"}
_UNRECORDED_REASONS = ("disabled", "checks_pending")  # nothing happened yet / will simply be retried


def _pr_number(pr: str) -> int:
    """The PR number from a task's `pr:` field (a URL ending in the number, or the bare number)."""
    match = re.search(r"(\d+)/?$", str(pr))
    if not match:
        raise ValueError(f"cannot read a PR number from {pr!r}")
    return int(match.group(1))


def _acceptance_criteria(task_body: str) -> str:
    """The task file's own `## Acceptance criteria` section, verbatim."""
    match = re.search(r"^## Acceptance criteria\s*\n(.*?)(?=^## |\Z)", task_body, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else "(no acceptance criteria section found)"


def _gh(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], cwd=root, capture_output=True, text=True)


def _in_review_task(sync_mod, tasks_root: Path, task_id: str):
    """The task, if it exists and is `in-review` with a PR recorded -- else `None`."""
    artifacts = discover_or_exit(sync_mod, tasks_root)
    task = artifacts.get(task_id)
    if task is None or task.kind != "task":
        return None
    if task.fields.get("status") != "in-review" or not task.fields.get("pr"):
        return None
    return task


def cmd_critic_prompt(args: argparse.Namespace) -> int:
    """Build the critic subagent's prompt from the task file and the live PR (acceptance
    criteria, changed files, the diff, the quality-gate results the caller reports plus CI's own).
    """
    answers = json.loads(Path(args.answers).read_text())
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    task = _in_review_task(sync_mod, tasks_root, answers["task_id"])
    if task is None:
        print(f"implement-task: {answers['task_id']} is not an in-review task with a PR recorded", file=sys.stderr)
        return 2
    pr = _pr_number(task.fields["pr"])
    view = _gh(root, "pr", "view", str(pr), "--json", "headRefOid,state")
    names = _gh(root, "pr", "diff", str(pr), "--name-only")
    diff = _gh(root, "pr", "diff", str(pr))
    checks = _gh(root, "pr", "checks", str(pr))
    for result in (view, names, diff):
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode
    changed = [line for line in names.stdout.splitlines() if line.strip()]
    head_sha = json.loads(view.stdout)["headRefOid"]
    gates = f"{answers.get('gates') or '(none reported)'}\n\nCI (`gh pr checks`):\n{checks.stdout.strip() or '(no output)'}"
    prompt = build_critic_prompt(
        task_id=task.id, title=task.fields.get("title", task.id), head_sha=head_sha,
        acceptance_criteria=_acceptance_criteria(task.body), changed_files=changed,
        scope_paths=answers.get("scope_paths") or [], gates=gates, diff=diff.stdout,
    )
    print(json.dumps({"prompt": prompt, "head_sha": head_sha, "changed_files": changed}))
    return 0


def cmd_auto_merge(args: argparse.Namespace) -> int:
    """The scripted, critic-gated, capped merge -- the only code path that ever runs `gh pr merge`.
    Every gate must pass (opt-in, cap, PR open at the reviewed head, CI green, changes within
    scope, critic approval, evaluated fail-closed); then it writes the guardrail marker for
    exactly this PR + head commit, asks the real guardrail evaluator whether its own merge
    command is allowed, runs it, and always removes the marker again. Any refusal exits `0` with
    `{"merged": false, "reason", "halt", "interrupt", "findings"}` -- `interrupt` names the
    `classify-interrupt` kind to route it through (or `None`: fall back to the ordinary
    human-merge wait). Errors (no batch, wrong task state, a failed `gh`) exit non-zero.
    """
    answers = json.loads(Path(args.answers).read_text())
    root = repo_root()
    tasks_root = root / ".tasks"
    state_path = batch_state_path(root)
    state = read_batch_state(state_path)
    if state is None:
        print("implement-task: auto-merge needs an active batch (no batch state found)", file=sys.stderr)
        return 2
    sync_mod = load_sync_module(tasks_root)
    task = _in_review_task(sync_mod, tasks_root, answers["task_id"])
    if task is None:
        print(f"implement-task: {answers['task_id']} is not an in-review task with a PR recorded", file=sys.stderr)
        return 2

    config = sync_mod.load_config(tasks_root)
    strategy = config.get("merge_strategy", "squash")
    if strategy not in _MERGE_STRATEGY_FLAGS:
        print(f"implement-task: unknown merge_strategy {strategy!r} in .tasks/config.md", file=sys.stderr)
        return 2
    try:
        cap_verdict = check_merge_cap(
            merged=count_auto_merged(state), cap=config.get("autonomous_merge_cap", DEFAULT_MERGE_CAP)
        )
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2

    verdict = evaluate_critic_verdict(answers.get("verdict"))
    pr = _pr_number(task.fields["pr"])
    reason: str | None = None
    if config.get("allow_auto_merge") is not True:
        reason = "disabled"
    elif not cap_verdict["allowed"]:
        reason = "cap_reached"
    else:
        view = _gh(root, "pr", "view", str(pr), "--json", "headRefOid,state")
        checks = _gh(root, "pr", "checks", str(pr))
        names = _gh(root, "pr", "diff", str(pr), "--name-only")
        for result in (view, names):
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
                return result.returncode
        live = json.loads(view.stdout)
        head_sha = live["headRefOid"]
        if live["state"] != "OPEN":
            reason = "pr_not_open"
        elif head_sha != answers.get("head_sha"):
            reason = "head_moved"  # the critic reviewed a different commit than the PR now has
        else:
            changed = [line for line in names.stdout.splitlines() if line.strip()]
            gates = evaluate_auto_merge_gates(
                allow_auto_merge=True, cap_allowed=True, checks_state=pr_checks_state(checks.returncode),
                scope_violations=scope_violations(changed, answers.get("scope_paths") or []),
                verdict_approve=verdict["approve"],
            )
            reason = gates["reason"]

    if reason is not None:
        if reason not in _UNRECORDED_REASONS:
            outcome = "critic_rejected" if reason == "critic_rejected" else f"skipped:{reason}"
            state = record_critic_review(state, {
                "task_id": task.id, "pr": pr, "head_sha": answers.get("head_sha"), "approve": verdict["approve"],
                "findings": verdict["findings"], "checklist": verdict["checklist"], "outcome": outcome,
            })
            write_batch_state(state_path, state)
        print(json.dumps({
            "merged": False, "reason": reason, "halt": reason == "cap_reached",
            "interrupt": _REASON_INTERRUPTS.get(reason), "findings": verdict["findings"],
            "detail": verdict["reason"] if reason == "critic_rejected" else (cap_verdict["message"] if reason == "cap_reached" else None),
        }))
        return 0

    guardrails = load_guardrails_module()
    merge_args = ["pr", "merge", str(pr), _MERGE_STRATEGY_FLAGS[strategy], "--match-head-commit", head_sha]
    guardrails.write_auto_merge_marker(root, pr=pr, head_sha=head_sha)
    try:
        allowed = guardrails.evaluate_bash_command(shlex.join(["gh", *merge_args]), root)
        if not allowed.allow:
            print(f"implement-task: the guardrail refused the scripted merge: {allowed.reason}", file=sys.stderr)
            return 2
        merged = _gh(root, *merge_args)
    finally:
        guardrails.clear_auto_merge_marker(root)
    if merged.returncode != 0:
        print(merged.stderr, file=sys.stderr)
        return merged.returncode

    state = record_critic_review(state, {
        "task_id": task.id, "pr": pr, "head_sha": head_sha, "approve": True,
        "findings": verdict["findings"], "checklist": verdict["checklist"], "outcome": "auto_merged",
    })
    write_batch_state(state_path, state)
    print(json.dumps({"merged": True, "pr": pr, "head_sha": head_sha, "findings": verdict["findings"]}))
    return 0


def cmd_render_critic_summary(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    print(json.dumps({"summary": render_critic_summary(answers.get("critic_reviews") or [])}))
    return 0


def cmd_render_batch_result(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    summary = render_batch_result(
        order=answers["order"], outcomes=answers.get("outcomes") or [], halt=answers.get("halt")
    )
    print(json.dumps({"summary": summary}))
    return 0


def cmd_batch_clear(args: argparse.Namespace) -> int:
    root = repo_root()
    load_guardrails_module().clear_auto_merge_marker(root)  # never leave a merge authorisation behind
    print(json.dumps({"cleared": clear_batch_state(batch_state_path(root))}))
    return 0


def cmd_render_outcome_table(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    table = render_outcome_table(answers.get("outcomes") or [])
    print(json.dumps({"table": table}))
    return 0


def cmd_classify_interrupt(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    try:
        result = interrupt_routing(answers["kind"])
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


def cmd_check_usage_thresholds(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    result = check_usage_thresholds(
        context_pct=answers["context_pct"], halt_pct=answers["halt_pct"],
        tokens_used=answers["tokens_used"], token_budget=answers.get("token_budget"),
    )
    print(json.dumps(result))
    return 0


def cmd_render_usage_summary(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    summary = render_usage_summary(
        context_pct=answers["context_pct"], tokens_used=answers["tokens_used"],
        token_budget=answers.get("token_budget"),
    )
    print(json.dumps({"summary": summary}))
    return 0


def cmd_session_token_usage(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    try:
        result = compute_session_token_usage(Path(answers["transcript_path"]))
    except TranscriptError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


def cmd_gh_auth_status(args: argparse.Namespace) -> int:
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    return result.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("resume-state", help="determine which phase to resume at")
    subparsers.add_parser("gh-auth-status", help="wrap `gh auth status`")

    for name, help_text in (
        ("start", "phase 1: pick/validate a task, branch, set status+branch, run sync"),
        ("wrap-up", "phase 3: commit, rebase, push, gh pr create, record pr, run sync"),
        ("finish-merge", "phase 4: observe the merge, record it, archive, clean up branches"),
        ("bail-out", "set status back to todo/blocked and run sync"),
        ("record-outcome", "batch mode: append one task's outcome to the accumulator"),
        ("batch-init", "batch mode: write the local batch-state file for a freshly selected batch"),
        ("batch-update", "batch mode: record one task's outcome/progress in the batch-state file"),
        ("batch-clear", "batch mode: delete the batch-state file (batch halted)"),
        ("create-follow-up", "batch mode: create a follow-up task via add-task, up to the per-batch limit"),
        ("render-follow-up-summary", "batch mode: render the follow-up-tasks part of the end-of-batch summary"),
        ("critic-prompt", "auto-merge: build the critic subagent's checklist prompt for a task's open PR"),
        ("auto-merge", "auto-merge: run every gate and, if all pass, the scripted critic-approved merge"),
        ("render-critic-summary", "auto-merge: render the critic-findings part of the end-of-batch summary"),
        ("render-batch-result", "batch mode: render the batch headline (size, completed, what ended it early)"),
        ("render-outcome-table", "batch mode: render the end-of-batch outcome table"),
        ("classify-interrupt", "batch mode: route an interrupt kind to isolated/systemic"),
        ("check-usage-thresholds", "batch mode: check context/token usage against config thresholds"),
        ("session-token-usage", "batch mode: exact token total from the session's transcript file"),
        ("render-usage-summary", "batch mode: render the end-of-batch usage report"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("answers", help="path to a JSON file with this subcommand's inputs")

    args = parser.parse_args(argv)
    dispatch = {
        "resume-state": cmd_resume_state,
        "gh-auth-status": cmd_gh_auth_status,
        "start": cmd_start,
        "wrap-up": cmd_wrap_up,
        "finish-merge": cmd_finish_merge,
        "bail-out": cmd_bail_out,
        "record-outcome": cmd_record_outcome,
        "batch-init": cmd_batch_init,
        "batch-update": cmd_batch_update,
        "batch-clear": cmd_batch_clear,
        "create-follow-up": cmd_create_follow_up,
        "render-follow-up-summary": cmd_render_follow_up_summary,
        "critic-prompt": cmd_critic_prompt,
        "auto-merge": cmd_auto_merge,
        "render-critic-summary": cmd_render_critic_summary,
        "render-batch-result": cmd_render_batch_result,
        "render-outcome-table": cmd_render_outcome_table,
        "classify-interrupt": cmd_classify_interrupt,
        "check-usage-thresholds": cmd_check_usage_thresholds,
        "session-token-usage": cmd_session_token_usage,
        "render-usage-summary": cmd_render_usage_summary,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
