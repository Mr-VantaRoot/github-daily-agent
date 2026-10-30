import unittest

from github_daily_agent.analyzer import analyze


class AnalyzerTests(unittest.TestCase):
    def test_reports_missing_readme_tests_and_ci(self):
        findings = analyze({}, {"tree": []}, {
            "missing_readme": True, "missing_tests": True, "missing_ci": True
        })
        self.assertEqual({f.key for f in findings}, {
            "missing-readme", "missing-tests", "missing-ci"
        })

    def test_no_findings_when_basics_exist(self):
        tree = {"tree": [
            {"path": "README.md"},
            {"path": "tests/test_app.py"},
            {"path": ".github/workflows/ci.yml"},
        ]}
        self.assertEqual(analyze({}, tree, {
            "missing_readme": True, "missing_tests": True, "missing_ci": True
        }), [])

    def test_disabled_checks_are_ignored(self):
        self.assertEqual(analyze({}, {"tree": []}, {
            "missing_readme": False, "missing_tests": False, "missing_ci": False
        }), [])


if __name__ == "__main__":
    unittest.main()
