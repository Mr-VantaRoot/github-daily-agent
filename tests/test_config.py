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
            p.write_text("repositories: []\n")
            with self.assertRaises(ValueError):
                load_config(p)


if __name__ == "__main__":
    unittest.main()
