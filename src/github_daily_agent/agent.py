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


def run(config, token, client=None):
    gh = client or GitHub(token)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# GitHub Daily Agent report", "", f"Scanned: {now}", ""]
    created = 0
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
                lines += ["Warning: Git tree response was truncated; findings may be incomplete.", ""]
            findings = analyze(repo, tree, config.get("checks", {}))
            if not findings:
                lines += ["No configured repository-health findings detected.", ""]
                continue
            lines += [f"Detected {len(findings)} finding(s):", ""]
            issues = gh.list_open_issues(full_name) if config.get("create_issues") else []
            for finding in findings:
                lines += [f"- **{finding.title}** ({finding.key})"]
                if not config.get("create_issues"):
                    lines += ["  - Issue creation disabled."]
                    continue
                if _issue_exists(issues, finding.key):
                    lines += ["  - Existing open agent issue found; skipped duplicate."]
                    continue
                if created >= int(config.get("max_issues_per_run", 5)):
                    lines += ["  - Per-run issue creation limit reached."]
                    continue
                marker = f"\n\n<!-- github-daily-agent:{finding.key} -->"
                body = finding.body + marker
                result = gh.create_issue(full_name, finding.title, body)
                created += 1
                issues.append(result)
                lines += [f"  - Created issue: {result.get('html_url', '(URL unavailable)')}"]
            lines.append("")
        except GitHubError as exc:
            lines += [f"Scan error: {exc}", ""]
    report = "\n".join(lines)
    report_dir = Path(config.get("report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "latest.md").write_text(report + "\n", encoding="utf-8")
    return report
