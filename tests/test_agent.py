import tempfile
import unittest
from pathlib import Path

from github_daily_agent.agent import run
from github_daily_agent.github import GitHubError


class FakeGitHub:
    def __init__(self):
        self.created = []

    def get_repo(self, name):
        return {"default_branch": "main", "archived": False}

    def get_tree(self, name, branch):
        return {"tree": []}

    def list_open_issues(self, name):
        return self.created.copy()

    def create_issue(self, name, title, body):
        item = {"title": title, "body": body, "html_url": "https://example.test/issue/1"}
        self.created.append(item)
        return item


class MultiRepoFakeGitHub:
    def __init__(self):
        self.created_by_repo = {}

    def get_repo(self, name):
        return {"default_branch": "main", "archived": False}

    def get_tree(self, name, branch):
        return {"tree": []}

    def list_open_issues(self, name):
        return self.created_by_repo.setdefault(name, []).copy()

    def create_issue(self, name, title, body):
        issues = self.created_by_repo.setdefault(name, [])
        item = {
            "title": title,
            "body": body,
            "html_url": f"https://example.test/{name}/{len(issues) + 1}",
        }
        issues.append(item)
        return item

    def all_created(self):
        return [
            (repo, issue)
            for repo, issues in self.created_by_repo.items()
            for issue in issues
        ]


class PermissionFailureFake(MultiRepoFakeGitHub):
    def list_open_issues(self, name):
        if name == "octo/blocked":
            raise GitHubError(
                "GitHub API 403 for /issues: Resource not accessible by personal access token",
                status_code=403,
                path="/repos/octo/blocked/issues",
            )
        return super().list_open_issues(name)


class TruncatedTreeFake(MultiRepoFakeGitHub):
    def get_tree(self, name, branch):
        return {"tree": [], "truncated": True}


class CreationFailureFake(MultiRepoFakeGitHub):
    def create_issue(self, name, title, body):
        if name == "octo/blocked":
            raise GitHubError(
                "GitHub API 403 for /issues: Resource not accessible by personal access token",
                status_code=403,
                path="/repos/octo/blocked/issues",
            )
        return super().create_issue(name, title, body)


class AgentTests(unittest.TestCase):
    def _config(self, report_dir, repositories=None):
        return {
            "repositories": repositories or ["octo/repo"],
            "create_issues": True,
            "max_issues_per_run": 5,
            "report_dir": report_dir,
            "checks": {
                "missing_readme": False,
                "missing_tests": True,
                "missing_ci": True,
            },
        }

    def test_creates_findings_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            fake = FakeGitHub()
            cfg = self._config(d)
            cfg["checks"] = {
                "missing_readme": True,
                "missing_tests": False,
                "missing_ci": False,
            }
            report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.created), 1)
            self.assertIn("Created issue", report)
            self.assertIn("\n\n<!-- github-daily-agent:missing-readme -->", fake.created[0]["body"])
            self.assertIn("Issues created: 1", report)
            self.assertTrue((Path(d) / "latest.md").exists())

    def test_deduplicates_open_agent_issue(self):
        with tempfile.TemporaryDirectory() as d:
            marker = "<!-- github-daily-agent:missing-readme -->"
            fake = FakeGitHub()
            fake.created = [{"body": marker}]
            cfg = self._config(d)
            cfg["checks"] = {
                "missing_readme": True,
                "missing_tests": False,
                "missing_ci": False,
            }
            run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.created), 1)

    def test_deferred_findings_are_created_over_later_runs_without_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            fake = MultiRepoFakeGitHub()
            repositories = [f"octo/repo-{i}" for i in range(7)]
            cfg = self._config(d, repositories)

            first_report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.all_created()), 5)
            self.assertEqual(first_report.count("Per-run issue creation limit reached."), 9)

            second_report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.all_created()), 10)
            self.assertIn("Existing open agent issue found; skipped duplicate.", second_report)

            third_report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.all_created()), 14)

            fourth_report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.all_created()), 14)

            created_keys = []
            for repo, issue in fake.all_created():
                marker = next(
                    key for key in ("missing-tests", "missing-ci")
                    if f"<!-- github-daily-agent:{key} -->" in issue["body"]
                )
                created_keys.append((repo, marker))

            self.assertEqual(len(created_keys), 14)
            self.assertEqual(len(set(created_keys)), 14)
            self.assertIn("Existing open agent issue found; skipped duplicate.", fourth_report)

    def test_truncated_tree_does_not_create_false_positive_issues(self):
        with tempfile.TemporaryDirectory() as d:
            fake = TruncatedTreeFake()
            cfg = self._config(d, ["octo/large"])

            report = run(cfg, "unused", client=fake)

            self.assertIn("Scan incomplete", report)
            self.assertEqual(fake.all_created(), [])

    def test_issue_read_permission_failure_does_not_stop_other_repositories(self):
        with tempfile.TemporaryDirectory() as d:
            fake = PermissionFailureFake()
            cfg = self._config(d, ["octo/blocked", "octo/allowed"])

            report = run(cfg, "unused", client=fake)

            self.assertIn("Issue processing warning", report)
            self.assertIn("Issues permission set to Read and write", report)
            self.assertEqual(len(fake.created_by_repo.get("octo/blocked", [])), 0)
            self.assertEqual(len(fake.created_by_repo.get("octo/allowed", [])), 2)
            self.assertIn("Issues created: 2", report)

    def test_issue_creation_permission_failure_does_not_stop_other_findings_or_repositories(self):
        with tempfile.TemporaryDirectory() as d:
            fake = CreationFailureFake()
            cfg = self._config(d, ["octo/blocked", "octo/allowed"])

            report = run(cfg, "unused", client=fake)

            self.assertIn("Issue creation warning", report)
            self.assertEqual(len(fake.created_by_repo.get("octo/blocked", [])), 0)
            self.assertEqual(len(fake.created_by_repo.get("octo/allowed", [])), 2)
            self.assertIn("Issues created: 2", report)


if __name__ == "__main__":
    unittest.main()
