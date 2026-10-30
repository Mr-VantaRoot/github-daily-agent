import tempfile
import unittest
from pathlib import Path

from github_daily_agent.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_allowlist_and_deduplicates(self):
        raw = """repositories:
  - octo/repo
  - octo/repo
create_issues: false
checks:
  missing_ci: true
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.yaml"
            p.write_text(raw)
            cfg = load_config(p)
        self.assertEqual(cfg["repositories"], ["octo/repo"])
        self.assertFalse(cfg["create_issues"])
        self.assertTrue(cfg["checks"]["missing_ci"])

    def test_rejects_empty_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.yaml"
            p.write_text("repositories: []\\n")
            with self.assertRaises(ValueError):
                load_config(p)

    def test_rejects_invalid_repository_names(self):
        for invalid in ("octo", "/repo", "octo/", "octo/repo name"):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as d:
                p = Path(d) / "config.yaml"
                p.write_text(f"repositories:\\n  - {invalid}\\n")
                with self.assertRaises(ValueError):
                    load_config(p)

    def test_rejects_nonpositive_issue_limit(self):
        for limit in (0, -1):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as d:
                p = Path(d) / "config.yaml"
                p.write_text(
                    f"repositories:\\n  - octo/repo\\nmax_issues_per_run: {limit}\\n"
                )
                with self.assertRaises(ValueError):
                    load_config(p)

    def test_rejects_invalid_check_values(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.yaml"
            p.write_text(
                "repositories:\\n  - octo/repo\\nchecks:\\n  missing_ci: yes\\n"
            )
            with self.assertRaises(ValueError):
                load_config(p)


if __name__ == "__main__":
    unittest.main()
