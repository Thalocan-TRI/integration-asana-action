"""
Unit tests for GitHubClient.
"""

from unittest.mock import patch

import pytest

from clients.github_client import GitHubClient
from tests.helpers import make_response


@pytest.fixture()
def client():
    return GitHubClient("fake-token")


# ---------------------------------------------------------------------------
# is_already_synced — returns True when Asana Task ID comment exists
# ---------------------------------------------------------------------------
def test_is_already_synced_returns_true_when_comment_found(client):
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(200, [{"body": "Asana Task ID: task-123"}]),
    ):
        assert (
            client.is_already_synced("https://api.github.com/repos/x/issues/1/comments")
            is True
        )


def test_is_already_synced_returns_false_when_no_matching_comment(client):
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(200, [{"body": "just a comment"}]),
    ):
        assert (
            client.is_already_synced("https://api.github.com/repos/x/issues/1/comments")
            is False
        )


def test_is_already_synced_returns_false_on_http_error(client):
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(500, {}),
    ):
        assert (
            client.is_already_synced("https://api.github.com/repos/x/issues/1/comments")
            is False
        )


# ---------------------------------------------------------------------------
# post_task_comment — posts correct payload and handles non-201 response
# ---------------------------------------------------------------------------
def test_post_task_comment_posts_correct_payload(client):
    with patch(
        "clients.github_client.requests.post",
        return_value=make_response(201, {}),
    ) as mock_post:
        client.post_task_comment(
            "https://api.github.com/repos/x/issues/1/comments", "task-999"
        )

    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"]["body"] == "Asana Task ID: task-999"


def test_post_task_comment_prints_error_on_non_201(client, capsys):
    with patch(
        "clients.github_client.requests.post",
        return_value=make_response(500, {}),
    ):
        client.post_task_comment(
            "https://api.github.com/repos/x/issues/1/comments", "task-999"
        )

    assert "Failed to create comment. Response code: 500" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# get_issue — returns dict on success, None on HTTP error
# ---------------------------------------------------------------------------
def test_get_issue_returns_issue_dict(client):
    issue = {"title": "My Issue", "body": "body", "comments_url": "https://..."}
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(200, issue),
    ):
        result = client.get_issue("owner/repo", "42")

    assert result == issue


def test_get_issue_returns_none_on_http_error(client, capsys):
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(404, {}),
    ):
        result = client.get_issue("owner/repo", "42")

    assert result is None
    assert "Failed to fetch issue #42" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# get_comments — returns list on success, empty list on HTTP error
# ---------------------------------------------------------------------------
def test_get_comments_returns_list(client):
    comments = [{"body": "hello"}, {"body": "world"}]
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(200, comments),
    ):
        result = client.get_comments("https://api.github.com/repos/x/issues/1/comments")

    assert result == comments


def test_get_comments_returns_empty_list_on_http_error(client, capsys):
    with patch(
        "clients.github_client.requests.get",
        return_value=make_response(500, {}),
    ):
        result = client.get_comments("https://api.github.com/repos/x/issues/1/comments")

    assert result == []
    assert "Failed to fetch comments. Response code: 500" in capsys.readouterr().out
