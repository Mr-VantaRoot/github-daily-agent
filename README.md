# GitHub Daily Agent

A scheduled maintenance scanner for seven selected repositories. It checks for basic project-health gaps, opens deduplicated GitHub issues when configured, and saves a Markdown report.

## What it checks

- A README is present.
- A conventional tests directory or test-prefixed file is present.
- A GitHub Actions workflow exists under `.github/workflows/`.

These are lightweight checks, not a full code audit. Findings are suggestions and may miss nonstandard layouts.

## Repositories monitored

The allowlist is in `config.yaml`:

- `Mr-VantaRoot/port_scanner`
- `Mr-VantaRoot/Network-Monitor`
- `Mr-VantaRoot/file_encryptor`
- `Mr-VantaRoot/password_checker.py`
- `Mr-VantaRoot/check_ip.py`
- `Mr-VantaRoot/Birhanguard`
- `Mr-VantaRoot/milky-smiles-connect`

Only these repositories are scanned. Edit the allowlist deliberately if you want to change it.

## Schedule

GitHub Actions runs daily at **03:00 UTC (06:00 Ethiopia time)**. You can also start it manually from **Actions → Daily Repository Scan → Run workflow**.

GitHub may delay scheduled runs during high load. Check the Actions tab to confirm each run.

## Permission warnings

The scanner separates repository inspection from issue management. If it can inspect a repository but cannot read or create issues, the report records the warning and continues with the other repositories. For a fine-grained token, confirm that the affected repository is selected and **Issues** is set to **Read and write**. The agent will not create issues when it cannot first list open issues, because doing so could create duplicates.

If GitHub returns a truncated repository tree, that repository is marked as incomplete and no absence-based findings are generated for it.

## Setup

1. In your GitHub account, create a **fine-grained personal access token**.
2. Set the resource owner to `Mr-VantaRoot`.
3. Set repository access to **Only select repositories**, and select the seven monitored repositories.
4. Grant only:
   - **Metadata:** Read-only
   - **Contents:** Read-only
   - **Issues:** Read and write
5. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
6. Name the secret `GH_AGENT_TOKEN` and paste the token value.

Do not put the token in `config.yaml`, source files, or commits. Do not grant administration, workflow, secrets, deployment, or contents-write permissions.

## Run locally on Fedora

Python 3.10+; no third-party packages are needed.

```bash
git clone https://github.com/Mr-VantaRoot/github-daily-agent.git
cd github-daily-agent
python3 -m venv .venv
source .venv/bin/activate
export GH_AGENT_TOKEN="YOUR_FINE_GRAINED_TOKEN"
PYTHONPATH=src python -m github_daily_agent --config config.yaml
```

The report is written to `reports/latest.md`.

## Safety and limitations

- The agent does **not** edit application source code, create commits, create pull requests, or merge anything.
- It can create up to five actionable issues per run, and checks existing open issues to avoid duplicates.
- It does not manufacture commits or activity to manipulate the contribution graph.
- An automated run does not guarantee a contribution-graph square.
- Review each finding before making changes; the scanner is intentionally limited.

## Project layout

```text
.github/workflows/daily-scan.yml
config.yaml
src/github_daily_agent/
  __init__.py
  __main__.py
  agent.py
  analyzer.py
  config.py
  github.py
tests/
  test_agent.py
  test_analyzer.py
  test_config.py
  test_github.py
```

## Tests

Run the test suite locally:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
