"""
Integration tests for Integration Asana Action.

Covers all scenarios from the README behavior summary table.
Each test mocks the Asana SDK and GitHub HTTP calls — no real network requests are made.

Scenarios:
    1.  opened  | title starts with "Asana:"           → creates task + comments task ID
    2.  opened  | title does NOT start with "Asana:"   → nothing
    3.  edited  | title starts with "Asana:", not synced → creates task + comments task ID
    4.  edited  | already synced                        → nothing
    5.  edited  | no "Asana:" prefix                   → nothing
    6.  closed  | comment with "Asana Task ID:" found  → moves task to "Done"
    7.  closed  | no task ID comment                   → nothing
    8.  workflow_dispatch | ISSUE_NUMBER set, not synced → creates task + comments task ID
    9.  workflow_dispatch | ISSUE_NUMBER set, already synced → nothing
    10. workflow_dispatch | no ISSUE_NUMBER             → nothing
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import main
from tests.helpers import make_response

EVENTS_DIR = Path(__file__).parent / "events"

FAKE_TASK_GID = "task-gid-999"


@pytest.fixture()
def mock_asana():
    with (
        patch("asana.Configuration"),
        patch("asana.ApiClient"),
        patch("asana.TasksApi") as mock_tasks_api,
        patch("asana.SectionsApi") as mock_sections_api,
    ):
        mock_tasks_api.return_value.create_task.return_value = {"gid": FAKE_TASK_GID}
        yield {
            "tasks": mock_tasks_api,
            "sections": mock_sections_api,
        }


# ---------------------------------------------------------------------------
# Scenario 1 — opened | title starts with "Asana:" → creates task + comments
# ---------------------------------------------------------------------------
def test_opened_with_asana_prefix_creates_task_and_comments(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-01.json"))

    with (
        patch("requests.get") as mock_get,
        patch("requests.post", return_value=make_response(201, {})) as mock_post,
    ):
        main.run()

    mock_get.assert_not_called()
    mock_asana["tasks"].return_value.create_task.assert_called_once()
    mock_post.assert_called_once()
    assert (
        f"Asana Task ID: {FAKE_TASK_GID}" in mock_post.call_args.kwargs["json"]["body"]
    )


# ---------------------------------------------------------------------------
# Scenario 2 — opened | no "Asana:" prefix → nothing
# ---------------------------------------------------------------------------
def test_opened_without_asana_prefix_does_nothing(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-02.json"))

    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_not_called()
    mock_get.assert_not_called()
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3 — edited | "Asana:" prefix, not yet synced → creates task + comments
# ---------------------------------------------------------------------------
def test_edited_with_asana_prefix_not_synced_creates_task(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-03.json"))

    with (
        patch(
            "requests.get",
            return_value=make_response(200, [{"body": "unrelated comment"}]),
        ),
        patch("requests.post", return_value=make_response(201, {})) as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_called_once()
    mock_post.assert_called_once()
    assert (
        f"Asana Task ID: {FAKE_TASK_GID}" in mock_post.call_args.kwargs["json"]["body"]
    )


# ---------------------------------------------------------------------------
# Scenario 4 — edited | already synced → nothing
# ---------------------------------------------------------------------------
def test_edited_already_synced_does_nothing(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-03.json"))

    with (
        patch(
            "requests.get",
            return_value=make_response(200, [{"body": "Asana Task ID: existing-111"}]),
        ),
        patch("requests.post") as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_not_called()
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 5 — edited | no "Asana:" prefix → nothing
# ---------------------------------------------------------------------------
def test_edited_without_asana_prefix_does_nothing(monkeypatch, mock_asana, tmp_path):
    event = {
        "action": "edited",
        "issue": {
            "number": 9,
            "title": "just a plain title with no prefix",
            "body": "some body",
            "comments_url": "https://api.github.com/repos/test/issues/9/comments",
        },
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event))

    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_not_called()
    mock_get.assert_not_called()
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 6 — closed | "Asana Task ID:" comment found → moves task to "Done"
# ---------------------------------------------------------------------------
def test_closed_with_task_id_comment_moves_to_done(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-04.json"))

    with patch(
        "requests.get",
        return_value=make_response(200, [{"body": f"Asana Task ID: {FAKE_TASK_GID}"}]),
    ):
        main.run()

    mock_asana["sections"].return_value.add_task_for_section.assert_called_once_with(
        "section-done-123",
        {"body": {"data": {"task": FAKE_TASK_GID}}},
    )


# ---------------------------------------------------------------------------
# Scenario 7 — closed | no task ID comment → nothing
# ---------------------------------------------------------------------------
def test_closed_without_task_id_comment_does_nothing(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(EVENTS_DIR / "event-04.json"))

    with patch(
        "requests.get", return_value=make_response(200, [{"body": "just a comment"}])
    ):
        main.run()

    mock_asana["sections"].return_value.add_task_for_section.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 8 — workflow_dispatch | ISSUE_NUMBER set, not synced → creates task + comments
# ---------------------------------------------------------------------------
def test_workflow_dispatch_not_synced_creates_task_and_comments(
    monkeypatch, mock_asana
):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("INPUT_ISSUE_NUMBER", "1")

    issue_payload = {
        "title": "Asana: nova issue",
        "body": "issue body",
        "comments_url": "https://api.github.com/repos/ivanjun10r/github-actions-test/issues/1/comments",
    }

    with (
        patch(
            "requests.get",
            side_effect=[
                make_response(200, issue_payload),
                make_response(200, []),
            ],
        ),
        patch("requests.post", return_value=make_response(201, {})) as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_called_once()
    mock_post.assert_called_once()
    assert (
        f"Asana Task ID: {FAKE_TASK_GID}" in mock_post.call_args.kwargs["json"]["body"]
    )


# ---------------------------------------------------------------------------
# Scenario 9 — workflow_dispatch | ISSUE_NUMBER set, already synced → nothing
# ---------------------------------------------------------------------------
def test_workflow_dispatch_already_synced_does_nothing(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("INPUT_ISSUE_NUMBER", "1")

    issue_payload = {
        "title": "Asana: nova issue",
        "body": "issue body",
        "comments_url": "https://api.github.com/repos/ivanjun10r/github-actions-test/issues/1/comments",
    }

    with (
        patch(
            "requests.get",
            side_effect=[
                make_response(200, issue_payload),
                make_response(200, [{"body": "Asana Task ID: existing-111"}]),
            ],
        ),
        patch("requests.post") as mock_post,
    ):
        main.run()

    mock_asana["tasks"].return_value.create_task.assert_not_called()
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 10 — workflow_dispatch | no ISSUE_NUMBER → nothing
# ---------------------------------------------------------------------------
def test_workflow_dispatch_without_issue_number_does_nothing(monkeypatch, mock_asana):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("INPUT_ISSUE_NUMBER", "")

    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
    ):
        main.run()

    mock_get.assert_not_called()
    mock_asana["tasks"].return_value.create_task.assert_not_called()
    mock_post.assert_not_called()
