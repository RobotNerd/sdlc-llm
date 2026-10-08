"""Loading secrets from .env, with the environment taking precedence."""

import pytest

from lib.env import EnvError, load_env, require_secret

FAKE_SECRET = "fake-secret-a1b2c3"


def write_env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text)
    return path


def test_values_load_when_env_has_comments_blank_lines_and_quotes(tmp_path):
    path = write_env(
        tmp_path,
        "# a comment\n"
        "\n"
        "PLAIN=plain-value\n"
        'DOUBLE="double # quoted"\n'
        "SINGLE='single quoted'\n"
        "export EXPORTED=exported-value\n"
        "TRAILING=trailing-value  # a trailing comment\n"
        "EMPTY=\n",
    )

    values = load_env(path, environ={})

    assert values == {
        "DOUBLE": "double # quoted",
        "EMPTY": "",
        "EXPORTED": "exported-value",
        "PLAIN": "plain-value",
        "SINGLE": "single quoted",
        "TRAILING": "trailing-value",
    }


def test_environment_value_wins_when_a_key_is_in_both(tmp_path, monkeypatch):
    path = write_env(tmp_path, "KANEO_API_KEY=from-dotenv\n")
    monkeypatch.setenv("KANEO_API_KEY", "from-environment")

    assert load_env(path)["KANEO_API_KEY"] == "from-environment"


def test_environment_values_load_when_env_file_is_missing(tmp_path):
    values = load_env(tmp_path / ".env", environ={"KANEO_API_KEY": "from-environment"})

    assert values["KANEO_API_KEY"] == "from-environment"


@pytest.mark.parametrize(
    "line",
    [
        FAKE_SECRET,
        f"KANEO_API_KEY {FAKE_SECRET}",
        f"not a key={FAKE_SECRET}",
        f'KANEO_API_KEY="{FAKE_SECRET}',
        f"KANEO_API_KEY='{FAKE_SECRET}",
    ],
)
def test_error_names_the_line_and_hides_the_value_when_a_line_is_malformed(tmp_path, line):
    path = write_env(tmp_path, f"# first line\n{line}\n")

    with pytest.raises(EnvError) as error:
        load_env(path, environ={})

    message = str(error.value)
    assert f"{path}:2" in message
    assert FAKE_SECRET not in message
    assert error.value.__cause__ is None
    assert error.value.__context__ is None or FAKE_SECRET not in str(error.value.__context__)


def test_error_names_the_key_and_file_when_a_required_secret_is_missing(tmp_path):
    path = write_env(tmp_path, f"OTHER_KEY={FAKE_SECRET}\n")

    with pytest.raises(EnvError) as error:
        require_secret(load_env(path, environ={}), "KANEO_API_KEY", path)

    message = str(error.value)
    assert "KANEO_API_KEY" in message
    assert str(path) in message
    assert FAKE_SECRET not in message


def test_required_secret_returns_its_value_when_set(tmp_path):
    path = write_env(tmp_path, f"KANEO_API_KEY={FAKE_SECRET}\n")

    assert require_secret(load_env(path, environ={}), "KANEO_API_KEY", path) == FAKE_SECRET
