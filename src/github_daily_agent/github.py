import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


class GitHubError(RuntimeError):
    def __init__(self, message, status_code=None, path=None):
        super().__init__(message)
        self.status_code = status_code
        self.path = path


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
            try:
                message = json.loads(detail).get("message", detail)
            except (json.JSONDecodeError, AttributeError):
                message = detail
            raise GitHubError(
                f"GitHub API {exc.code} for {path}: {message}",
                status_code=exc.code,
                path=path,
            ) from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"GitHub API connection error: {exc}", path=path) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubError(f"GitHub API returned an invalid response for {path}: {exc}", path=path) from exc

    def get_repo(self, full_name):
        owner, repo = full_name.split("/", 1)
        return self.request("GET", f"/repos/{owner}/{repo}")

    def get_tree(self, full_name, branch):
        owner, repo = full_name.split("/", 1)
        encoded = urllib.parse.quote(branch, safe="")
        return self.request("GET", f"/repos/{owner}/{repo}/git/trees/{encoded}?recursive=1")

    def list_open_issues(self, full_name):
        owner, repo = full_name.split("/", 1)
        issues = []
        page = 1
        while True:
            batch = self.request(
                "GET",
                f"/repos/{owner}/{repo}/issues?state=open&per_page=100&page={page}",
            )
            if not isinstance(batch, list):
                raise GitHubError(
                    f"GitHub returned an unexpected issue-list response for {full_name}",
                    path=f"/repos/{owner}/{repo}/issues",
                )
            issues.extend(batch)
            if len(batch) < 100:
                return issues
            page += 1

    def create_issue(self, full_name, title, body, labels=None):
        owner, repo = full_name.split("/", 1)
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self.request("POST", f"/repos/{owner}/{repo}/issues", payload)
