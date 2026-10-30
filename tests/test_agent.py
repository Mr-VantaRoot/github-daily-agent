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


if __name__ == "__main__":
    unittest.main()
