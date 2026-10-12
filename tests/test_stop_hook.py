"""The Stop hook: a notification with the state a turn ended in, unless a skill already sent one."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from notify_fakes import MARKER, fake_environment, make_repo

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks/stop_notify.py"


LINKED_REPLY = (
    "[EX-26](https://kaneo.example/t/1) ready for review: [PR #114](https://github.example/pull/114). Details follow."
)
LOCAL_ZONE = "America/Los_Angeles"
PROMPT = {"type": "user", "message": {"role": "user", "content": "do the task"}}
WRAP_UP = {"type": "user", "isMeta": True, "usageLimitNote": "wrap_up", "message": {"content": "[Usage limit reached]"}}


def run_hook(repo, discord, stop_hook_active=False, **fields):
    stop_input = {
        "cwd": str(repo),
        "hook_event_name": "Stop",
        "session_id": "test-session",
        "stop_hook_active": stop_hook_active,
        "transcript_path": str(repo / "transcript.jsonl"),
        **fields,
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        capture_output=True,
        check=False,
        cwd=ROOT,
        env={**fake_environment(discord), "TZ": LOCAL_ZONE},
        input=json.dumps(stop_input),
        text=True,
        timeout=60,
    )


def write_transcript(repo, *entries):
    with (repo / "transcript.jsonl").open("a") as transcript:
        for entry in entries:
            transcript.write(json.dumps(entry) + "\n")


def sent_text(discord, timeout=10):
    deadline = time.monotonic() + timeout
    while not discord.requests and time.monotonic() < deadline:
        time.sleep(0.05)
    assert len(discord.requests) == 1
    prefix, text = discord.requests[0]["json"]["content"].split(": ", 1)
    assert prefix.endswith(" · session · STOP")
    return text


def zone_abbreviation():
    return datetime.now(ZoneInfo(LOCAL_ZONE)).strftime("%Z")


def write_marker(repo):
    (repo / MARKER).parent.mkdir(parents=True, exist_ok=True)
    (repo / MARKER).write_text("{}")


def test_nothing_is_sent_when_the_stop_hook_flag_is_off(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=False)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert result.stdout == ""
    assert discord.requests == []
    assert telegram.requests == []


def test_one_generic_message_is_sent_when_the_flag_is_on_and_there_is_no_marker(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    result = run_hook(repo, discord)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert len(discord.requests) == 1
    assert telegram.requests == []
    assert not (repo / MARKER).exists()


def test_nothing_is_sent_and_the_marker_is_cleared_when_a_skill_already_notified(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)
    write_marker(repo)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert discord.requests == []
    assert not (repo / MARKER).exists()


def test_the_next_stop_notifies_again_when_the_hook_sent_the_last_message(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord)
    run_hook(repo, discord)

    assert len(discord.requests) == 2


def test_the_stop_is_not_blocked_when_both_channels_fail(tmp_path, servers):
    discord, telegram = servers([(503, None)]), servers([(503, None)])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert "block" not in result.stdout


def test_nothing_happens_when_the_project_has_no_config(tmp_path, servers):
    discord = servers([(204, None)])
    (tmp_path / ".git").mkdir()

    result = run_hook(tmp_path, discord)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert discord.requests == []


def test_hooks_file_runs_the_hook_on_stop_and_stop_failure_from_the_plugin_root():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]

    for event in ("Stop", "StopFailure"):
        commands = [hook["command"] for entry in hooks[event] for hook in entry["hooks"]]

        assert commands == ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop_notify.py"']


def test_a_usage_limit_stop_failure_gives_the_reset_time(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    result = run_hook(
        repo,
        discord,
        hook_event_name="StopFailure",
        error="rate_limit",
        last_assistant_message="You've hit your session limit · resets 3:40pm (America/Los_Angeles)",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert sent_text(discord) == f"usage limit reached; resets at 1540 {zone_abbreviation()}"


def test_a_usage_limit_stop_gives_the_rerun_time_claude_code_writes_after_the_hook(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)
    write_transcript(repo, PROMPT, WRAP_UP)

    result = run_hook(repo, discord, last_assistant_message="Your usage limit was reached, so the PR isn't open yet.")
    write_transcript(
        repo, {"type": "system", "content": "Usage limit reached · continuing automatically at 3:40pm · esc to cancel"}
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert sent_text(discord) == f"usage limit reached; will automatically rerun at 1540 {zone_abbreviation()}"
    time.sleep(0.5)
    assert not (repo / MARKER).exists()


def test_a_usage_limit_stop_without_a_rerun_or_reset_time_says_so(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)
    write_transcript(repo, PROMPT, WRAP_UP)

    run_hook(repo, discord, last_assistant_message="Your usage limit was reached.")

    assert sent_text(discord) == "usage limit reached"


def test_a_usage_limit_note_from_an_earlier_turn_is_ignored(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)
    write_transcript(repo, PROMPT, WRAP_UP, PROMPT)

    run_hook(repo, discord, last_assistant_message="Tests pass.")

    assert sent_text(discord) == "Tests pass."


def test_the_first_sentence_of_the_last_reply_is_sent(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord, last_assistant_message="Tests pass. Next I'll open the PR.\n\n**Done:** more detail")

    assert sent_text(discord) == "Tests pass."


def test_a_long_first_sentence_is_cut_to_200_characters(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord, last_assistant_message="word " * 60)

    text = sent_text(discord)
    assert len(text) == 200
    assert text.endswith("…")


def test_links_in_the_first_sentence_reach_discord_as_markdown(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord, last_assistant_message=LINKED_REPLY)

    assert sent_text(discord) == (
        "[EX-26](https://kaneo.example/t/1) ready for review: [PR #114](https://github.example/pull/114)."
    )


def test_links_in_the_first_sentence_reach_telegram_as_anchors(tmp_path, servers):
    discord, telegram = servers([(503, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord, last_assistant_message="Tests <passed> & " + LINKED_REPLY)

    assert len(telegram.requests) == 1
    request = telegram.requests[0]["json"]
    assert request["parse_mode"] == "HTML"
    assert request["text"].endswith(
        ': Tests &lt;passed&gt; &amp; <a href="https://kaneo.example/t/1">EX-26</a> ready for review: '
        '<a href="https://github.example/pull/114">PR #114</a>.'
    )


def test_a_turn_with_no_last_reply_sends_the_generic_text(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord)

    assert sent_text(discord) == "Claude Code is waiting for you"
