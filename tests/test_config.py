"""Loading .sdlc/config.toml from the repo root."""

import pytest

from lib.config import ConfigError, SUPPORTED_CONFIG_VERSION, load_config, setting

VALID_CONFIG = """\
config_version = 1

[docs]
backend = "outline"

[tracker]
backend = "kaneo"
"""


def make_repo(tmp_path, config_text=None):
    (tmp_path / ".git").mkdir()
    if config_text is not None:
        (tmp_path / ".sdlc").mkdir()
        (tmp_path / ".sdlc/config.toml").write_text(config_text)
    return tmp_path


def test_config_loads_when_every_required_key_is_present(tmp_path):
    repo = make_repo(tmp_path, VALID_CONFIG)

    config = load_config(repo)

    assert config["tracker"]["backend"] == "kaneo"
    assert config["docs"]["backend"] == "outline"


def test_config_loads_when_started_from_a_subdirectory(tmp_path):
    repo = make_repo(tmp_path, VALID_CONFIG)
    subdirectory = repo / "skills/some-skill"
    subdirectory.mkdir(parents=True)

    assert load_config(subdirectory)["tracker"]["backend"] == "kaneo"


def test_error_names_the_expected_path_when_config_is_missing(tmp_path):
    repo = make_repo(tmp_path)

    with pytest.raises(ConfigError) as error:
        load_config(repo)

    assert ".sdlc/config.toml" in str(error.value)


def test_error_names_the_key_when_a_required_key_is_missing(tmp_path):
    repo = make_repo(tmp_path, VALID_CONFIG.replace('[tracker]\nbackend = "kaneo"\n', ""))

    with pytest.raises(ConfigError) as error:
        load_config(repo)

    assert "tracker.backend" in str(error.value)


def test_error_names_the_supported_version_when_config_version_is_unknown(tmp_path):
    repo = make_repo(tmp_path, VALID_CONFIG.replace("config_version = 1", "config_version = 99"))

    with pytest.raises(ConfigError) as error:
        load_config(repo)

    message = str(error.value)
    assert "99" in message
    assert f"config_version {SUPPORTED_CONFIG_VERSION}" in message


def test_error_names_the_file_when_config_is_not_valid_toml(tmp_path):
    repo = make_repo(tmp_path, "config_version = = 1\n")

    with pytest.raises(ConfigError) as error:
        load_config(repo)

    assert ".sdlc/config.toml" in str(error.value)


def test_error_says_so_when_not_inside_a_git_repo(tmp_path):
    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert "git repository" in str(error.value)


def test_default_eval_command_is_used_when_config_does_not_set_one(tmp_path):
    config = load_config(make_repo(tmp_path, VALID_CONFIG))

    command = setting(config, "evals.command")

    assert command.startswith("claude plugin eval . --tag {tag}")
    assert "--runs 1" in command
    assert "--ablation none" in command


def test_configured_eval_command_wins_when_config_sets_one(tmp_path):
    config = load_config(make_repo(tmp_path, VALID_CONFIG + '\n[evals]\ncommand = "custom"\n'))

    assert setting(config, "evals.command") == "custom"
