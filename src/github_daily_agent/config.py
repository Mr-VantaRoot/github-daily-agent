import json
from pathlib import Path


def load_config(path):
    # JSON is a valid YAML subset. This project uses a small YAML subset to
    # avoid third-party runtime dependencies.
    raw = Path(path).read_text(encoding="utf-8")
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError:
        cfg = _minimal_yaml(raw)

    if not isinstance(cfg, dict):
        raise ValueError("config must be a mapping")

    repos = cfg.get("repositories", [])
    if not isinstance(repos, list) or not repos:
        raise ValueError("config must contain a non-empty repositories list")

    clean = []
    for repo in repos:
        if not isinstance(repo, str) or repo.count("/") != 1:
            raise ValueError(f"Invalid repository name: {repo!r}")
        owner, name = repo.split("/")
        if not owner or not name or any(c.isspace() for c in repo):
            raise ValueError(f"Invalid repository name: {repo!r}")
        if repo not in clean:
            clean.append(repo)

    cfg["repositories"] = clean
    cfg.setdefault("create_issues", False)
    cfg.setdefault("max_issues_per_run", 5)
    cfg.setdefault("report_dir", "reports")
    cfg.setdefault("checks", {})

    if not isinstance(cfg["create_issues"], bool):
        raise ValueError("create_issues must be true or false")
    limit = cfg["max_issues_per_run"]
    if type(limit) is not int or limit < 1:
        raise ValueError("max_issues_per_run must be a positive integer")
    if not isinstance(cfg["report_dir"], str) or not cfg["report_dir"].strip():
        raise ValueError("report_dir must be a non-empty path string")
    if not isinstance(cfg["checks"], dict):
        raise ValueError("checks must be a mapping")
    for name, enabled in cfg["checks"].items():
        if not isinstance(enabled, bool):
            raise ValueError(f"check {name!r} must be true or false")

    return cfg


def _minimal_yaml(raw):
    result, section = {}, None
    for original in raw.splitlines():
        line = original.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if line.startswith("  ") and section == "checks":
            key, sep, val = stripped.partition(":")
            if not sep:
                raise ValueError(f"Unsupported YAML line: {original}")
            result["checks"][key.strip()] = _scalar(val.strip())
        elif line.startswith("  - ") and section == "repositories":
            result["repositories"].append(stripped[2:].strip())
        elif not line.startswith(" "):
            key, sep, val = stripped.partition(":")
            if not sep:
                raise ValueError(f"Unsupported YAML line: {original}")
            key, val = key.strip(), val.strip()
            if not val:
                section = key
                result[key] = [] if key == "repositories" else {}
            else:
                section = None
                result[key] = _scalar(val)
        else:
            raise ValueError(f"Unsupported YAML indentation: {original}")
    return result


def _scalar(value):
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value.strip(chr(34) + "'")
