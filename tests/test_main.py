"""
Unit tests for main._validate_env.
"""

import pytest

import main

_ALL_REQUIRED = {
    "ASANA_PAT": "fake-pat",
    "GITHUB_TOKEN": "fake-token",
    "INPUT_ASANA_PROJECT_ID": "project-123",
    "INPUT_ASANA_SECTION_TO_DO": "section-todo",
    "INPUT_ASANA_SECTION_DONE": "section-done",
    "GITHUB_EVENT_NAME": "issues",
}


@pytest.fixture(autouse=True)
def set_required_env(monkeypatch):
    for key, value in _ALL_REQUIRED.items():
        monkeypatch.setenv(key, value)


def test_validate_env_passes_when_all_vars_set():
    main._validate_env()  # must not raise


def test_validate_env_exits_when_var_missing(monkeypatch):
    monkeypatch.delenv("ASANA_PAT")

    with pytest.raises(SystemExit) as exc_info:
        main._validate_env()

    assert exc_info.value.code == 1


def test_validate_env_exits_when_multiple_vars_missing(monkeypatch, capsys):
    monkeypatch.delenv("ASANA_PAT")
    monkeypatch.delenv("GITHUB_TOKEN")

    with pytest.raises(SystemExit):
        main._validate_env()

    output = capsys.readouterr().out
    assert "ASANA_PAT" in output
    assert "GITHUB_TOKEN" in output
