import os
import asana
from asana.rest import ApiException
from pprint import pprint
import json
import requests


def create_asana_task(
    api_client,
    section_id: str,
    project_id: str,
    name: str,
    notes: str | None = None,
):
    api_task_client = asana.TasksApi(api_client)

    body = {"data": {"name": name, "projects": [project_id]}}

    if notes is not None:
        body["data"]["notes"] = notes

    task = api_task_client.create_task(body, {})
    task_id = task["gid"]

    api_section_client = asana.SectionsApi(api_client)
    api_section_client.add_task_for_section(
        section_id, {"body": {"data": {"task": task_id}}}
    )
    return task


def move_asana_task_to_section(api_client, task_id: str, section_id: str):
    api_section_client = asana.SectionsApi(api_client)

    return api_section_client.add_task_for_section(
        section_id, {"body": {"data": {"task": task_id}}}
    )


def _is_already_synced(comments_url: str, headers: dict) -> bool:
    response = requests.get(comments_url, headers=headers)
    if response.status_code == 200:
        for comment in response.json():
            if "Asana Task ID:" in comment["body"]:
                return True
    return False


def _create_task_and_comment(
    title: str,
    body: str | None,
    comments_url: str,
    api_client,
    headers: dict,
    asana_section_to_do: str,
    asana_project_id: str,
):
    asana_task_name = (
        title.split("Asana:")[1].strip() if title.startswith("Asana:") else title
    )
    asana_task = create_asana_task(
        api_client,
        asana_section_to_do,
        asana_project_id,
        asana_task_name,
        body,
    )
    data = {"body": "Asana Task ID: %s" % asana_task["gid"]}
    response = requests.post(comments_url, json=data, headers=headers)
    if response.status_code == 201:
        print("Comment created successfully")
    else:
        print(f"Failed to create comment: {response.status_code}")


def handle_workflow_dispatch(
    api_client,
    headers: dict,
    issue_number: str | None,
    github_repository: str | None,
    asana_section_to_do: str,
    asana_project_id: str,
):
    if not issue_number:
        print("INPUT_ISSUE_NUMBER not provided for workflow_dispatch")
        return
    if not github_repository:
        print("GITHUB_REPOSITORY environment variable is not set")
        return

    issue_url = (
        f"https://api.github.com/repos/{github_repository}/issues/{issue_number}"
    )
    response = requests.get(issue_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch issue #{issue_number}: {response.status_code}")
        return

    issue_data = response.json()
    title = issue_data["title"]
    body = issue_data.get("body")
    comments_url = issue_data["comments_url"]

    if _is_already_synced(comments_url, headers):
        print(f"Issue #{issue_number} is already synced to Asana")
        return

    print(f"Syncing issue #{issue_number} to Asana")
    _create_task_and_comment(
        title,
        body,
        comments_url,
        api_client,
        headers,
        asana_section_to_do,
        asana_project_id,
    )


def run():
    asana_pat = os.getenv("ASANA_PAT")
    github_token = os.getenv("GITHUB_TOKEN")
    event_name = os.getenv("GITHUB_EVENT_NAME")
    github_repository = os.getenv("GITHUB_REPOSITORY")

    asana_project_id = os.getenv("INPUT_ASANA_PROJECT_ID")
    asana_section_to_do = os.getenv("INPUT_ASANA_SECTION_TO_DO")
    asana_section_done = os.getenv("INPUT_ASANA_SECTION_DONE")
    issue_number = os.getenv("INPUT_ISSUE_NUMBER")

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    configuration = asana.Configuration()
    configuration.access_token = asana_pat
    api_client = asana.ApiClient(configuration)

    if event_name == "workflow_dispatch":
        handle_workflow_dispatch(
            api_client,
            headers,
            issue_number,
            github_repository,
            asana_section_to_do,
            asana_project_id,
        )
        return

    event_path = os.getenv("GITHUB_EVENT_PATH", "/github/workflow/event.json")
    with open(event_path, "r") as file:
        event_data = json.load(file)

        action = event_data["action"]
        title = ""
        body = ""
        commit_url = ""

        if "issue" in event_data:
            commit_url = event_data["issue"]["comments_url"]
            title = event_data["issue"]["title"]
            body = event_data["issue"]["body"]
        else:
            commit_url = event_data["pull_request"]["_links"]["comments"]["href"]
            title: str = event_data["pull_request"]["title"]
            body: str | None = event_data["pull_request"]["body"]

        if action == "opened":
            pprint("Pull request opened")

            if title.startswith("Asana:"):
                _create_task_and_comment(
                    title,
                    body,
                    commit_url,
                    api_client,
                    headers,
                    asana_section_to_do,
                    asana_project_id,
                )

        elif action == "edited":
            if title.startswith("Asana:") and not _is_already_synced(
                commit_url, headers
            ):
                print("Issue/PR edited with Asana prefix — syncing to Asana")
                _create_task_and_comment(
                    title,
                    body,
                    commit_url,
                    api_client,
                    headers,
                    asana_section_to_do,
                    asana_project_id,
                )

        elif action == "closed":
            pprint("Pull request closed")

            response = requests.get(commit_url, headers=headers)
            if response.status_code == 200:
                comments = response.json()
                for comment in comments:
                    if "Asana Task ID:" in comment["body"]:
                        asana_task_id = (
                            comment["body"].split("Asana Task ID:")[1].strip()
                        )

                        try:
                            move_asana_task_to_section(
                                api_client,
                                asana_task_id,
                                asana_section_done,
                            )
                        except ApiException as e:
                            print(e)
                        break
            else:
                pprint(f"Failed to fetch comments: {response.status_code}")


if __name__ == "__main__":
    run()
