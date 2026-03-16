#!/usr/bin/env python3
"""Sync tag labels to counter issues.

Reads registry tags, compares with issue labels, adds/removes tag:* labels.
Requires GH_TOKEN env var.
"""

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "index.yaml"


def get_issues_with_counter_label() -> list[dict]:
    """Get all issues with [counter] label."""
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", os.environ.get("GITHUB_REPOSITORY", "twisker/iphub"),
         "--label", "[counter]", "--json", "number,title,labels", "--limit", "500"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return []
    import json
    return json.loads(result.stdout) or []


def sync_labels(issue_number: int, desired_tags: list[str], current_labels: list[str]) -> None:
    """Add/remove tag: labels on an issue."""
    desired = {f"tag:{t}" for t in desired_tags}
    current = {l for l in current_labels if l.startswith("tag:")}

    to_add = desired - current
    to_remove = current - desired

    repo = os.environ.get("GITHUB_REPOSITORY", "twisker/iphub")
    for label in to_add:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--add-label", label],
            capture_output=True, check=False,
        )
    for label in to_remove:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--remove-label", label],
            capture_output=True, check=False,
        )


def main():
    if not INDEX_FILE.exists():
        print("No index.yaml found.")
        return

    index = yaml.safe_load(INDEX_FILE.read_text(encoding="utf-8")) or {}

    # Build name → tags mapping
    tag_map: dict[str, list[str]] = {}
    for section in ("skills", "packages"):
        for name, info in index.get(section, {}).items():
            tags = info.get("tags", [])
            if tags:
                tag_map[name] = tags

    if not tag_map:
        print("No tags to sync.")
        return

    issues = get_issues_with_counter_label()
    synced = 0
    for issue in issues:
        title = issue.get("title", "")
        for name, tags in tag_map.items():
            if name in title:
                current_labels = [l.get("name", "") for l in issue.get("labels", [])]
                sync_labels(issue["number"], tags, current_labels)
                synced += 1
                break

    print(f"Synced labels for {synced} issues.")


if __name__ == "__main__":
    main()
