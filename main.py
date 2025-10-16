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
    status_id: str,
    status_enum_id: str,
    name: str,
    notes: str | None = None,
):
    api_task_client = asana.TasksApi(api_client)

    body = {
        "data": {
            "name": name,
            "projects": [project_id],
            "custom_fields": {status_id: status_enum_id},
        }
    }

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


ASANA_PAT = os.getenv("ASANA_PAT")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
EVENT_NAME = os.getenv("GITHUB_EVENT_NAME")

ASANA_PROJECT_ID = os.getenv("INPUT_ASANA_PROJECT_ID")
ASANA_SECTION_TO_DO = os.getenv("INPUT_ASANA_SECTION_TO_DO")
ASANA_SECTION_DONE = os.getenv("INPUT_ASANA_SECTION_DONE")
ASANA_WORKSPACE_ID = os.getenv("INPUT_ASANA_WORKSPACE_ID")
ASANA_CUSTOM_FIELD_STATUS_ID = os.getenv("INPUT_ASANA_CUSTOM_FIELD_STATUS_ID")
ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID = os.getenv(
    "INPUT_ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID"
)
ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID = os.getenv(
    "INPUT_ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID"
)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

configuration = asana.Configuration()
configuration.access_token = ASANA_PAT
api_client = asana.ApiClient(configuration)


def run():
    with open("/github/workflow/event.json", "r") as file:
        event_data = json.load(file)
        # pprint(event_data, indent=2)

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

        # base_branch = event_data["pull_request"]["base"]["ref"]
        # pprint("Base branch: ", base_branch, action)

        if action == "opened":
            pprint("Pull request opened")

            if title.startswith("Asana:"):
                asana_task_name = title.split("Asana:")[1].strip()
                asana_task = create_asana_task(
                    api_client,
                    ASANA_SECTION_TO_DO,
                    ASANA_PROJECT_ID,
                    ASANA_CUSTOM_FIELD_STATUS_ID,
                    ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID,
                    asana_task_name,
                    body,
                )

                data = {"body": "Asana Task ID: %s" % asana_task["gid"]}

                response = requests.post(commit_url, json=data, headers=headers)

                if response.status_code == 201:
                    print("Comment created successfully")
                else:
                    print(f"Failed to create comment: {response.status_code}")

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
                                ASANA_SECTION_DONE,
                            )
                        except ApiException as e:
                            print(e)
                        break
            else:
                pprint(f"Failed to fetch comments: {response.status_code}")


if __name__ == "__main__":
    run()
