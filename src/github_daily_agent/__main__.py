import argparse
import os
import sys

from .agent import run
from .config import load_config


def main():
    parser = argparse.ArgumentParser(description="Scan explicitly selected GitHub repositories.")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    token = os.environ.get("GH_AGENT_TOKEN")
    if not token:
        print("ERROR: GH_AGENT_TOKEN environment variable is required.", file=sys.stderr)
        raise SystemExit(2)
    config = load_config(args.config)
    report = run(config, token)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
