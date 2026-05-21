"""
Unit tests for AsanaClient.
"""

from unittest.mock import patch

import pytest

from clients.asana_client import AsanaClient


@pytest.fixture()
def mock_asana_sdk():
    with (
        patch("clients.asana_client.asana.Configuration"),
        patch("clients.asana_client.asana.ApiClient"),
        patch("clients.asana_client.asana.TasksApi") as mock_tasks_api,
        patch("clients.asana_client.asana.SectionsApi") as mock_sections_api,
    ):
        mock_tasks_api.return_value.create_task.return_value = {"gid": "task-001"}
        client = AsanaClient("fake-pat")
        yield client, {"tasks": mock_tasks_api, "sections": mock_sections_api}


# ---------------------------------------------------------------------------
# create_task — calls TasksApi.create_task with correct payload
# ---------------------------------------------------------------------------
def test_create_task_calls_tasks_api(mock_asana_sdk):
    client, mocks = mock_asana_sdk

    client.create_task("section-1", "project-1", "My Task")

    mocks["tasks"].return_value.create_task.assert_called_once_with(
        {"data": {"name": "My Task", "projects": ["project-1"]}}, {}
    )


# ---------------------------------------------------------------------------
# create_task — adds notes to payload only when provided
# ---------------------------------------------------------------------------
def test_create_task_includes_notes_when_provided(mock_asana_sdk):
    client, mocks = mock_asana_sdk

    client.create_task("section-1", "project-1", "My Task", notes="Some notes")

    call_args = mocks["tasks"].return_value.create_task.call_args
    assert call_args[0][0]["data"]["notes"] == "Some notes"


def test_create_task_excludes_notes_when_not_provided(mock_asana_sdk):
    client, mocks = mock_asana_sdk

    client.create_task("section-1", "project-1", "My Task")

    call_args = mocks["tasks"].return_value.create_task.call_args
    assert "notes" not in call_args[0][0]["data"]


# ---------------------------------------------------------------------------
# create_task — calls SectionsApi.add_task_for_section to place task in section
# ---------------------------------------------------------------------------
def test_create_task_moves_task_to_section(mock_asana_sdk):
    client, mocks = mock_asana_sdk

    client.create_task("section-1", "project-1", "My Task")

    mocks["sections"].return_value.add_task_for_section.assert_called_once_with(
        "section-1", {"body": {"data": {"task": "task-001"}}}
    )


# ---------------------------------------------------------------------------
# move_task_to_section — calls SectionsApi.add_task_for_section correctly
# ---------------------------------------------------------------------------
def test_move_task_to_section(mock_asana_sdk):
    client, mocks = mock_asana_sdk

    client.move_task_to_section("task-999", "section-done")

    mocks["sections"].return_value.add_task_for_section.assert_called_once_with(
        "section-done", {"body": {"data": {"task": "task-999"}}}
    )
