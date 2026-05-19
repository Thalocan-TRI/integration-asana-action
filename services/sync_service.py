import json
from pprint import pprint

from asana.rest import ApiException

from clients.asana_client import AsanaClient
from clients.github_client import GitHubClient


class SyncService:
    def __init__(
        self,
        asana_client: AsanaClient,
        github_client: GitHubClient,
        project_id: str,
        section_to_do: str,
        section_done: str,
    ):
        self._asana = asana_client
        self._github = github_client
        self._project_id = project_id
        self._section_to_do = section_to_do
        self._section_done = section_done

    def run(
        self,
        event_name: str,
        event_path: str,
        github_repository: str | None,
        issue_number: str | None,
    ) -> None:
        if event_name == "workflow_dispatch":
            self._handle_workflow_dispatch(github_repository, issue_number)
            return

        with open(event_path, "r", encoding="utf-8") as file:
            event_data = json.load(file)

        action = event_data["action"]

        if "issue" in event_data:
            comments_url = event_data["issue"]["comments_url"]
            title = event_data["issue"]["title"]
            body = event_data["issue"]["body"]
        else:
            comments_url = event_data["pull_request"]["_links"]["comments"]["href"]
            title: str = event_data["pull_request"]["title"]
            body: str | None = event_data["pull_request"]["body"]

        if action == "opened":
            pprint("Pull request opened")
            if title.startswith("Asana:"):
                self._sync_issue_or_pr(title, body, comments_url)

        elif action == "edited":
            if title.startswith("Asana:") and not self._github.is_already_synced(
                comments_url
            ):
                print("Issue/PR edited with Asana prefix — syncing to Asana")
                self._sync_issue_or_pr(title, body, comments_url)

        elif action == "closed":
            pprint("Pull request closed")
            comments = self._github.get_comments(comments_url)
            for comment in comments:
                if "Asana Task ID:" in comment["body"]:
                    asana_task_id = comment["body"].split("Asana Task ID:")[1].strip()
                    try:
                        self._asana.move_task_to_section(
                            asana_task_id, self._section_done
                        )
                    except ApiException as e:
                        print(e)
                    break

    def _sync_issue_or_pr(
        self,
        title: str,
        body: str | None,
        comments_url: str,
    ) -> None:
        asana_task_name = (
            title.split("Asana:")[1].strip() if title.startswith("Asana:") else title
        )
        try:
            asana_task = self._asana.create_task(
                self._section_to_do,
                self._project_id,
                asana_task_name,
                body,
            )
        except ApiException as e:
            print(f"Failed to create Asana task: {e}")
            return
        self._github.post_task_comment(comments_url, asana_task["gid"])

    def _handle_workflow_dispatch(
        self,
        github_repository: str | None,
        issue_number: str | None,
    ) -> None:
        if not issue_number:
            print("INPUT_ISSUE_NUMBER not provided for workflow_dispatch")
            return
        if not github_repository:
            print("GITHUB_REPOSITORY environment variable is not set")
            return

        issue_data = self._github.get_issue(github_repository, issue_number)
        if issue_data is None:
            return

        title = issue_data["title"]
        body = issue_data.get("body")
        comments_url = issue_data["comments_url"]

        if self._github.is_already_synced(comments_url):
            print(f"Issue #{issue_number} is already synced to Asana")
            return

        print(f"Syncing issue #{issue_number} to Asana")
        self._sync_issue_or_pr(title, body, comments_url)
