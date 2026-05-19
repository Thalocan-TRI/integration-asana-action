import pytest

COMMON_ENV = {
    "ASANA_PAT": "fake-asana-pat",
    "GITHUB_TOKEN": "fake-github-token",
    "GITHUB_REPOSITORY": "ivanjun10r/github-actions-test",
    "INPUT_ASANA_PROJECT_ID": "project-123",
    "INPUT_ASANA_SECTION_TO_DO": "section-todo-123",
    "INPUT_ASANA_SECTION_DONE": "section-done-123",
    "INPUT_ISSUE_NUMBER": "",
}


@pytest.fixture(autouse=True)
def set_common_env(monkeypatch):
    for key, value in COMMON_ENV.items():
        monkeypatch.setenv(key, value)
