"""
Unit tests for error scenarios in main.py.

Complements the integration tests by targeting branches that require
specific failure conditions on external dependencies.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from asana.rest import ApiException

import main
from tests.helpers import make_response

FAKE_HEADERS = {
    "Authorization": "Bearer fake",
    "Accept": "application/vnd.github.v3+json",
}


# ---------------------------------------------------------------------------
# _create_task_and_comment — POST comment returns non-201
# ---------------------------------------------------------------------------
def test_create_task_and_comment_post_fails_prints_error(capsys):
    with (
        patch("asana.TasksApi") as mock_tasks_api,
        patch("asana.SectionsApi"),
        patch("requests.post", return_value=make_response(500, {})),
    ):
        mock_tasks_api.return_value.create_task.return_value = {"gid": "task-111"}

        main._create_task_and_comment(
            title="Asana: task name",
            body="body",
            comments_url="https://api.github.com/repos/test/issues/1/comments",
            api_client=MagicMock(),
            headers=FAKE_HEADERS,
            asana_section_to_do="section-todo",
            asana_project_id="project-123",
        )

    assert "Failed to create comment: 500" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# handle_workflow_dispatch — called without github_repository
# ---------------------------------------------------------------------------
def test_handle_workflow_dispatch_missing_github_repository(capsys):
    with patch("requests.get") as mock_get:
        main.handle_workflow_dispatch(
            api_client=MagicMock(),
            headers=FAKE_HEADERS,
            issue_number="42",
            github_repository=None,
            asana_section_to_do="section-todo",
            asana_project_id="project-123",
        )

    mock_get.assert_not_called()
    assert (
        "GITHUB_REPOSITORY environment variable is not set" in capsys.readouterr().out
    )


# ---------------------------------------------------------------------------
# handle_workflow_dispatch — GitHub API returns 404 for issue
# ---------------------------------------------------------------------------
def test_handle_workflow_dispatch_issue_fetch_returns_404(capsys):
    with (
        patch("requests.get", return_value=make_response(404, {})),
        patch("asana.TasksApi") as mock_tasks_api,
    ):
        main.handle_workflow_dispatch(
            api_client=MagicMock(),
            headers=FAKE_HEADERS,
            issue_number="42",
            github_repository="owner/repo",
            asana_section_to_do="section-todo",
            asana_project_id="project-123",
        )

    mock_tasks_api.return_value.create_task.assert_not_called()
    assert "Failed to fetch issue #42" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run() — pull_request event (not an issue)
# ---------------------------------------------------------------------------
def test_run_pull_request_opened_with_asana_prefix(monkeypatch, tmp_path):
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

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    with (
        patch("asana.Configuration"),
        patch("asana.ApiClient"),
        patch("asana.TasksApi") as mock_tasks_api,
        patch("asana.SectionsApi"),
        patch("requests.post", return_value=make_response(201, {})) as mock_post,
    ):
        mock_tasks_api.return_value.create_task.return_value = {"gid": "pr-task-999"}
        main.run()

    mock_tasks_api.return_value.create_task.assert_called_once()
    assert "Asana Task ID: pr-task-999" in mock_post.call_args.kwargs["json"]["body"]


# ---------------------------------------------------------------------------
# run() closed — Asana raises ApiException on move
# ---------------------------------------------------------------------------
def test_closed_move_task_raises_api_exception(monkeypatch, tmp_path):
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

    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    with (
        patch("asana.Configuration"),
        patch("asana.ApiClient"),
        patch("asana.SectionsApi") as mock_sections_api,
        patch(
            "requests.get",
            return_value=make_response(200, [{"body": "Asana Task ID: task-111"}]),
        ),
    ):
        mock_sections_api.return_value.add_task_for_section.side_effect = ApiException()
        main.run()  # ApiException must be caught internally — should not propagate


# ---------------------------------------------------------------------------
# run() closed — GET comments returns non-200
# ---------------------------------------------------------------------------
def test_closed_get_comments_fails_prints_error(monkeypatch, tmp_path, capsys):
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

    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    with (
        patch("asana.Configuration"),
        patch("asana.ApiClient"),
        patch("asana.SectionsApi"),
        patch("requests.get", return_value=make_response(500, {})),
    ):
        main.run()

    assert "Failed to fetch comments: 500" in capsys.readouterr().out
