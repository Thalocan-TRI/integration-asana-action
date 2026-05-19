"""
Tests for SyncService — all GitHub Action sync scenarios.

Covers all scenarios from the README behavior summary table.
Each test injects mock AsanaClient / GitHubClient — no SDK or HTTP mocking needed.

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
from unittest.mock import MagicMock

from asana.rest import ApiException

from services.sync_service import SyncService

EVENTS_DIR = Path(__file__).parent / "events"

FAKE_TASK_GID = "task-gid-999"


@pytest.fixture()
def mock_asana_client():
    client = MagicMock()
    client.create_task.return_value = {"gid": FAKE_TASK_GID}
    return client


@pytest.fixture()
def mock_github_client():
    client = MagicMock()
    client.is_already_synced.return_value = False
    client.get_comments.return_value = []
    return client


@pytest.fixture()
def service(mock_asana_client, mock_github_client):
    return SyncService(
        asana_client=mock_asana_client,
        github_client=mock_github_client,
        project_id="project-123",
        section_to_do="section-todo-123",
        section_done="section-done-123",
    )


# ---------------------------------------------------------------------------
# Scenario 1 — opened | title starts with "Asana:" → creates task + comments
# ---------------------------------------------------------------------------
def test_opened_with_asana_prefix_creates_task_and_comments(
    service, mock_asana_client, mock_github_client
):
    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-01.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_called_once()
    mock_github_client.post_task_comment.assert_called_once()
    assert mock_github_client.post_task_comment.call_args[0][1] == FAKE_TASK_GID


# ---------------------------------------------------------------------------
# Scenario 2 — opened | no "Asana:" prefix → nothing
# ---------------------------------------------------------------------------
def test_opened_without_asana_prefix_does_nothing(
    service, mock_asana_client, mock_github_client
):
    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-02.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_not_called()
    mock_github_client.post_task_comment.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3 — edited | "Asana:" prefix, not yet synced → creates task + comments
# ---------------------------------------------------------------------------
def test_edited_with_asana_prefix_not_synced_creates_task(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.is_already_synced.return_value = False

    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-03.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_called_once()
    mock_github_client.post_task_comment.assert_called_once()
    assert mock_github_client.post_task_comment.call_args[0][1] == FAKE_TASK_GID


# ---------------------------------------------------------------------------
# Scenario 4 — edited | already synced → nothing
# ---------------------------------------------------------------------------
def test_edited_already_synced_does_nothing(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.is_already_synced.return_value = True

    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-03.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_not_called()
    mock_github_client.post_task_comment.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 5 — edited | no "Asana:" prefix → nothing
# ---------------------------------------------------------------------------
def test_edited_without_asana_prefix_does_nothing(
    service, mock_asana_client, mock_github_client, tmp_path
):
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

    service.run(
        event_name="issues",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_not_called()
    mock_github_client.is_already_synced.assert_not_called()
    mock_github_client.post_task_comment.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 6 — closed | "Asana Task ID:" comment found → moves task to "Done"
# ---------------------------------------------------------------------------
def test_closed_with_task_id_comment_moves_to_done(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.get_comments.return_value = [
        {"body": f"Asana Task ID: {FAKE_TASK_GID}"}
    ]

    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-04.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.move_task_to_section.assert_called_once_with(
        FAKE_TASK_GID, "section-done-123"
    )


# ---------------------------------------------------------------------------
# Scenario 7 — closed | no task ID comment → nothing
# ---------------------------------------------------------------------------
def test_closed_without_task_id_comment_does_nothing(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.get_comments.return_value = [{"body": "just a comment"}]

    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-04.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.move_task_to_section.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 8 — workflow_dispatch | ISSUE_NUMBER set, not synced → creates task + comments
# ---------------------------------------------------------------------------
def test_workflow_dispatch_not_synced_creates_task_and_comments(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.get_issue.return_value = {
        "title": "Asana: nova issue",
        "body": "issue body",
        "comments_url": "https://api.github.com/repos/ivanjun10r/github-actions-test/issues/1/comments",
    }
    mock_github_client.is_already_synced.return_value = False

    service.run(
        event_name="workflow_dispatch",
        event_path="",
        github_repository="ivanjun10r/github-actions-test",
        issue_number="1",
    )

    mock_asana_client.create_task.assert_called_once()
    mock_github_client.post_task_comment.assert_called_once()
    assert mock_github_client.post_task_comment.call_args[0][1] == FAKE_TASK_GID


# ---------------------------------------------------------------------------
# Scenario 9 — workflow_dispatch | ISSUE_NUMBER set, already synced → nothing
# ---------------------------------------------------------------------------
def test_workflow_dispatch_already_synced_does_nothing(
    service, mock_asana_client, mock_github_client
):
    mock_github_client.get_issue.return_value = {
        "title": "Asana: nova issue",
        "body": "issue body",
        "comments_url": "https://api.github.com/repos/ivanjun10r/github-actions-test/issues/1/comments",
    }
    mock_github_client.is_already_synced.return_value = True

    service.run(
        event_name="workflow_dispatch",
        event_path="",
        github_repository="ivanjun10r/github-actions-test",
        issue_number="1",
    )

    mock_asana_client.create_task.assert_not_called()
    mock_github_client.post_task_comment.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 10 — workflow_dispatch | no ISSUE_NUMBER → nothing
# ---------------------------------------------------------------------------
def test_workflow_dispatch_without_issue_number_does_nothing(
    service, mock_asana_client, mock_github_client
):
    service.run(
        event_name="workflow_dispatch",
        event_path="",
        github_repository="ivanjun10r/github-actions-test",
        issue_number="",
    )

    mock_github_client.get_issue.assert_not_called()
    mock_asana_client.create_task.assert_not_called()
    mock_github_client.post_task_comment.assert_not_called()


# ---------------------------------------------------------------------------
# pull_request event — opened with "Asana:" prefix
# ---------------------------------------------------------------------------
def test_opened_pull_request_with_asana_prefix_creates_task(
    service, mock_asana_client, mock_github_client, tmp_path
):
    event = {
        "action": "opened",
        "pull_request": {
            "title": "Asana: PR task",
            "body": "PR body",
            "_links": {
                "comments": {
                    "href": "https://api.github.com/repos/owner/repo/issues/5/comments"
                }
            },
        },
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event))

    service.run(
        event_name="pull_request",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )

    mock_asana_client.create_task.assert_called_once()
    mock_github_client.post_task_comment.assert_called_once()


# ---------------------------------------------------------------------------
# closed — ApiException is caught and does not propagate
# ---------------------------------------------------------------------------
def test_closed_move_task_raises_api_exception_is_caught(
    service, mock_asana_client, mock_github_client, tmp_path
):
    event = {
        "action": "closed",
        "issue": {
            "number": 1,
            "title": "Asana: test",
            "body": "",
            "comments_url": "https://api.github.com/repos/owner/repo/issues/1/comments",
        },
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event))

    mock_github_client.get_comments.return_value = [{"body": "Asana Task ID: task-111"}]
    mock_asana_client.move_task_to_section.side_effect = ApiException()

    # Must not raise
    service.run(
        event_name="issues",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )


# ---------------------------------------------------------------------------
# opened — ApiException on create_task is caught; comment is NOT posted
# ---------------------------------------------------------------------------
def test_opened_create_task_raises_api_exception_is_caught(
    service, mock_asana_client, mock_github_client
):
    mock_asana_client.create_task.side_effect = ApiException()

    # Must not raise
    service.run(
        event_name="issues",
        event_path=str(EVENTS_DIR / "event-01.json"),
        github_repository=None,
        issue_number=None,
    )

    mock_github_client.post_task_comment.assert_not_called()
