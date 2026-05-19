import requests

_REQUEST_TIMEOUT = 10


class GitHubClient:
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def is_already_synced(self, comments_url: str) -> bool:
        response = requests.get(
            comments_url, headers=self._headers, timeout=_REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            for comment in response.json():
                if "Asana Task ID:" in comment["body"]:
                    return True
        return False

    def post_task_comment(self, comments_url: str, task_gid: str) -> None:
        data = {"body": "Asana Task ID: %s" % task_gid}
        response = requests.post(
            comments_url, json=data, headers=self._headers, timeout=_REQUEST_TIMEOUT
        )
        if response.status_code == 201:
            print("Comment created successfully")
        else:
            print(f"Failed to create comment. Response code: {response.status_code}")

    def get_issue(self, repository: str, issue_number: str) -> dict | None:
        url = f"https://api.github.com/repos/{repository}/issues/{issue_number}"
        response = requests.get(url, headers=self._headers, timeout=_REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(
                f"Failed to fetch issue #{issue_number}. Response code: {response.status_code}"
            )
            return None
        return response.json()

    def get_comments(self, comments_url: str) -> list:
        response = requests.get(
            comments_url, headers=self._headers, timeout=_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            print(f"Failed to fetch comments. Response code: {response.status_code}")
            return []
        return response.json()
