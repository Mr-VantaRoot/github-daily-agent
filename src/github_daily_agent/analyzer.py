from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    key: str
    title: str
    body: str
    severity: str = "low"


def analyze(repo, tree, checks):
    paths = {item.get("path", "").lower() for item in tree.get("tree", [])}
    findings = []

    if checks.get("missing_readme", True):
        if not any(p.rsplit("/", 1)[-1].startswith("readme") for p in paths):
            findings.append(Finding(
                "missing-readme",
                "Consider adding a project README",
                "## Finding\nNo README file was found at the repository root or in the scanned tree.\n\n"
                "## Why this matters\nA concise README helps users understand the project's purpose, setup, usage, and limitations.\n\n"
                "## Suggested action\nAdd or restore a README with an accurate overview, installation steps, usage examples, and project status. "
                "Do not add claims that have not been verified."
            ))

    if checks.get("missing_tests", True):
        has_tests = any(
            p.startswith(("test/", "tests/")) or "/tests/" in p or p.startswith(("spec/", "specs/"))
            or p.rsplit("/", 1)[-1].startswith(("test_", "tests."))
            for p in paths
        )
        if not has_tests:
            findings.append(Finding(
                "missing-tests",
                "Consider adding automated tests",
                "## Finding\nNo conventional test directory or test-prefixed file was detected by the repository tree scan.\n\n"
                "## Why this matters\nAutomated tests can catch regressions and make future changes safer.\n\n"
                "## Suggested action\nIdentify the project's critical behavior and add focused tests using its existing language and test framework. "
                "This scan may miss nonstandard test layouts."
            ))

    if checks.get("missing_ci", True):
        has_ci = any(p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")) for p in paths)
        if not has_ci:
            findings.append(Finding(
                "missing-ci",
                "Consider adding a continuous-integration workflow",
                "## Finding\nNo GitHub Actions workflow file was detected under .github/workflows/.\n\n"
                "## Why this matters\nA CI workflow can run tests and basic checks when changes are proposed.\n\n"
                "## Suggested action\nAdd a minimal workflow that installs the project's dependencies and runs its existing tests. "
                "Review required permissions and avoid exposing secrets to untrusted pull requests."
            ))
    return findings
