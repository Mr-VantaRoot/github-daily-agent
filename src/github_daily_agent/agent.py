from datetime import datetime, timezone
from pathlib import Path

from .analyzer import analyze
from .github import GitHub, GitHubError


def _issue_exists(issues, key):
    marker = f"<!-- github-daily-agent:{key} -->"
    for issue in issues:
        if issue.get("pull_request"):
            continue
        body = issue.get("body") or ""
        if marker in body:
            return True
    return False


def _permission_hint(exc):
    if exc.status_code == 403:
        return (
            "Check that the fine-grained token includes this repository and has "
            "Issues permission set to Read and write."
        )
    if exc.status_code == 404:
        return (
            "Check that the repository exists and is selected in the fine-grained "
            "token; GitHub can return 404 when the token cannot access a repository."
        )
    return "Check the token permissions and GitHub API response."


def run(config, token, client=None):
    gh = client or GitHub(token)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# GitHub Daily Agent report", "", f"Scanned: {now}", ""]
    created = 0
    max_issues = int(config.get("max_issues_per_run", 5))

    for full_name in config["repositories"]:
        lines += [f"## {full_name}", ""]
        try:
            repo = gh.get_repo(full_name)
            if repo.get("archived"):
                lines += ["Skipped: repository is archived.", ""]
                continue

            branch = repo.get("default_branch") or "main"
            tree = gh.get_tree(full_name, branch)
            if tree.get("truncated"):
                lines += [
                    "Scan incomplete: GitHub returned a truncated file tree.",
                    "  - No findings or issues were generated for this repository because absence checks would be unreliable.",
                    "",
                ]
                continue

            findings = analyze(repo, tree, config.get("checks", {}))
        except GitHubError as exc:
            lines += [
                f"Scan warning: unable to inspect this repository ({exc}).",
                f"  - {_permission_hint(exc)}",
                "",
            ]
            continue

        if not findings:
            lines += ["No configured repository-health findings detected.", ""]
            continue

        lines += [f"Detected {len(findings)} finding(s):", ""]
        if not config.get("create_issues"):
            for finding in findings:
                lines += [
                    f"- **{finding.title}** ({finding.key})",
                    "  - Issue creation is disabled.",
                ]
            lines.append("")
            continue

        # Read existing issues before creating anything. If this read fails,
        # skip issue creation for this repository to avoid duplicate issues.
        try:
            issues = gh.list_open_issues(full_name)
        except GitHubError as exc:
            lines += [
                f"- Issue processing warning: could not list open issues ({exc}).",
                f"  - {_permission_hint(exc)}",
                "  - Findings were detected, but no issues were created for this repository.",
                "",
            ]
            continue

        for finding in findings:
            lines += [f"- **{finding.title}** ({finding.key})"]
            if _issue_exists(issues, finding.key):
                lines += ["  - Existing open agent issue found; skipped duplicate."]
                continue
            if created >= max_issues:
                lines += ["  - Per-run issue creation limit reached. Will retry on a later run."]
                continue

            marker = f"\n\n<!-- github-daily-agent:{finding.key} -->"
            body = finding.body + marker
            try:
                result = gh.create_issue(full_name, finding.title, body)
            except GitHubError as exc:
                lines += [
                    f"  - Issue creation warning: {exc}",
                    f"  - {_permission_hint(exc)}",
                ]
                continue

            created += 1
            issues.append(result)
            lines += [f"  - Created issue: {result.get('html_url', '(URL unavailable)')}"]
        lines.append("")

    lines += [f"## Run summary", "", f"- Issues created: {created}", ""]
    report = "\n".join(lines)
    report_dir = Path(config.get("report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "latest.md").write_text(report + "\n", encoding="utf-8")
    return report
