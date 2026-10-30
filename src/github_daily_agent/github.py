import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token):
        self.token = token

    def request(self, method, path, body=None):
        url = path if path.startswith("https://") else API + path
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "github-daily-agent/0.1")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = response.read()
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise GitHubError(f"GitHub API {exc.code} for {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"GitHub API connection error: {exc}") from exc

    def get_repo(self, full_name):
        owner, repo = full_name.split("/", 1)
        return self.request("GET", f"/repos/{owner}/{repo}")

    def get_tree(self, full_name, branch):
        owner, repo = full_name.split("/", 1)
        encoded = urllib.parse.quote(branch, safe="")
        return self.request("GET", f"/repos/{owner}/{repo}/git/trees/{encoded}?recursive=1")

    def list_open_issues(self, full_name):
        owner, repo = full_name.split("/", 1)
        return self.request("GET", f"/repos/{owner}/{repo}/issues?state=open&per_page=100")

    def create_issue(self, full_name, title, body, labels=None):
        owner, repo = full_name.split("/", 1)
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self.request("POST", f"/repos/{owner}/{repo}/issues", payload)
