import tempfile
import unittest
from pathlib import Path

from github_daily_agent.agent import run


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


class AgentTests(unittest.TestCase):
    def test_creates_findings_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            fake = FakeGitHub()
            cfg = {
                "repositories": ["octo/repo"], "create_issues": True,
                "max_issues_per_run": 5, "report_dir": d,
                "checks": {"missing_readme": True, "missing_tests": False, "missing_ci": False}
            }
            report = run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.created), 1)
            self.assertIn("Created issue", report)
            self.assertIn("\n\n<!-- github-daily-agent:missing-readme -->", fake.created[0]["body"])
            self.assertTrue((Path(d) / "latest.md").exists())

    def test_deduplicates_open_agent_issue(self):
        with tempfile.TemporaryDirectory() as d:
            marker = "<!-- github-daily-agent:missing-readme -->"
            fake = FakeGitHub()
            fake.created = [{"body": marker}]
            cfg = {
                "repositories": ["octo/repo"], "create_issues": True,
                "max_issues_per_run": 5, "report_dir": d,
                "checks": {"missing_readme": True, "missing_tests": False, "missing_ci": False}
            }
            run(cfg, "unused", client=fake)
            self.assertEqual(len(fake.created), 1)

    def test_deferred_findings_are_created_over_later_runs_without_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            fake = MultiRepoFakeGitHub()
            repositories = [f"octo/repo-{i}" for i in range(7)]
            cfg = {
                "repositories": repositories,
                "create_issues": True,
                "max_issues_per_run": 5,
                "report_dir": d,
                "checks": {
                    "missing_readme": False,
                    "missing_tests": True,
                    "missing_ci": True,
                },
            }

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


if __name__ == "__main__":
    unittest.main()
