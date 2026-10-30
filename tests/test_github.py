import unittest
from unittest.mock import Mock

from github_daily_agent.github import GitHub


class GitHubClientTests(unittest.TestCase):
    def test_open_issues_are_paginated_until_last_page(self):
        client = GitHub("unused")
        first_page = [{"number": i} for i in range(100)]
        second_page = [{"number": 101}, {"number": 102}]
        client.request = Mock(side_effect=[first_page, second_page])

        issues = client.list_open_issues("octo/repo")

        self.assertEqual(len(issues), 102)
        self.assertEqual(client.request.call_count, 2)
        self.assertIn("page=1", client.request.call_args_list[0].args[1])
        self.assertIn("page=2", client.request.call_args_list[1].args[1])

    def test_empty_issue_list_returns_empty_list(self):
        client = GitHub("unused")
        client.request = Mock(return_value=[])

        self.assertEqual(client.list_open_issues("octo/repo"), [])


if __name__ == "__main__":
    unittest.main()
