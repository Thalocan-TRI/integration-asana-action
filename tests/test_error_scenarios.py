"""
Tests for error/edge-case branches in the refactored layers.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from asana.rest import ApiException

from clients.asana_client import AsanaClient
from clients.github_client import GitHubClient
from services.sync_service import SyncService
from tests.helpers import make_response


def _make_service(asana_client=None, github_client=None):
    asana_client = asana_client or MagicMock()
    github_client = github_client or MagicMock()
    github_client.is_already_synced.return_value = False
    github_client.get_comments.return_value = []
    return SyncService(
        asana_client=asana_client,
        github_client=github_client,
        project_id="project-123",
        section_to_do="section-todo",
        section_done="section-done",
    )


# ---------------------------------------------------------------------------
# GitHubClient.post_task_comment — POST returns non-201
# ---------------------------------------------------------------------------
def test_post_task_comment_non_201_prints_error(capsys):
    with patch(
        "clients.github_client.requests.post",
        return_value=make_response(500, {}),
    ):
        client = GitHubClient("fake-token")
        client.post_task_comment(
            "https://api.github.com/repos/test/issues/1/comments", "task-111"
        )

    assert "Failed to create comment. Response code: 500" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# SyncService._handle_workflow_dispatch — missing github_repository
# ---------------------------------------------------------------------------
def test_handle_workflow_dispatch_missing_github_repository(capsys):
    service = _make_service()
    service.run(
        event_name="workflow_dispatch",
        event_path="",
        github_repository=None,
        issue_number="42",
    )

    assert (
        "GITHUB_REPOSITORY environment variable is not set" in capsys.readouterr().out
    )


# ---------------------------------------------------------------------------
# SyncService._handle_workflow_dispatch — GitHub API returns 404 for issue
# ---------------------------------------------------------------------------
def test_handle_workflow_dispatch_issue_fetch_returns_404(capsys):
    mock_github = MagicMock()
    mock_github.get_issue.return_value = None

    service = _make_service(github_client=mock_github)
    service.run(
        event_name="workflow_dispatch",
        event_path="",
        github_repository="owner/repo",
        issue_number="42",
    )

    mock_github.get_issue.assert_called_once_with("owner/repo", "42")
    service._asana.create_task.assert_not_called()


# ---------------------------------------------------------------------------
# SyncService.run — pull_request event opened with "Asana:" prefix
# ---------------------------------------------------------------------------
def test_run_pull_request_opened_with_asana_prefix(tmp_path):
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

    mock_asana = MagicMock()
    mock_asana.create_task.return_value = {"gid": "pr-task-999"}

    service = _make_service(asana_client=mock_asana)
    service.run(
        event_name="pull_request",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )

    mock_asana.create_task.assert_called_once()
    service._github.post_task_comment.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/issues/5/comments", "pr-task-999"
    )


# ---------------------------------------------------------------------------
# SyncService.run closed — Asana raises ApiException on move
# ---------------------------------------------------------------------------
def test_closed_move_task_raises_api_exception(tmp_path):
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

    mock_asana = MagicMock()
    mock_asana.move_task_to_section.side_effect = ApiException()

    mock_github = MagicMock()
    mock_github.get_comments.return_value = [{"body": "Asana Task ID: task-111"}]

    service = _make_service(asana_client=mock_asana, github_client=mock_github)
    # ApiException must be caught internally — should not propagate
    service.run(
        event_name="issues",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )


# ---------------------------------------------------------------------------
# SyncService.run closed — GET comments returns non-200 (empty list)
# ---------------------------------------------------------------------------
def test_closed_get_comments_fails_does_not_move_task(tmp_path):
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

    mock_asana = MagicMock()
    mock_github = MagicMock()
    mock_github.get_comments.return_value = []  # simulates failed fetch

    service = _make_service(asana_client=mock_asana, github_client=mock_github)
    service.run(
        event_name="issues",
        event_path=str(event_file),
        github_repository=None,
        issue_number=None,
    )

    mock_asana.move_task_to_section.assert_not_called()
