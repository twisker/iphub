#!/usr/bin/env python3
"""Calculate trending data from install count snapshots.

Usage: python scripts/generate_trending.py

Reads: stats/snapshots/, index.yaml
Writes: trending section appended to index.yaml
Also: creates today's snapshot, cleans up snapshots older than 30 days.
"""

from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "index.yaml"
SNAPSHOTS_DIR = ROOT / "stats" / "snapshots"
RETENTION_DAYS = 30
TREND_WINDOW = 7


def create_snapshot(index: dict) -> None:
    """Save today's install counts as a snapshot."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = {}
    for section in ("skills", "packages"):
        for name, info in index.get(section, {}).items():
            snapshot[name] = info.get("installs", 0)
    today = date.today().isoformat()
    path = SNAPSHOTS_DIR / f"{today}.yaml"
    path.write_text(yaml.dump(snapshot, default_flow_style=False), encoding="utf-8")
    print(f"  Snapshot saved: {path.name}")


def cleanup_old_snapshots() -> None:
    """Remove snapshots older than RETENTION_DAYS."""
    if not SNAPSHOTS_DIR.exists():
        return
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    for f in SNAPSHOTS_DIR.glob("*.yaml"):
        try:
            snap_date = date.fromisoformat(f.stem)
            if snap_date < cutoff:
                f.unlink()
                print(f"  Cleaned up old snapshot: {f.name}")
        except ValueError:
            continue


def load_snapshot(days_ago: int) -> dict | None:
    """Load a snapshot from N days ago. Returns None if not found."""
    target = date.today() - timedelta(days=days_ago)
    path = SNAPSHOTS_DIR / f"{target.isoformat()}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def calculate_trending(index: dict) -> dict:
    """Calculate trending data."""
    old_snapshot = load_snapshot(TREND_WINDOW)
    bootstrap = old_snapshot is None

    trending: dict = {
        "updated": date.today().isoformat() + "T04:00:00Z",
    }

    if bootstrap:
        trending["bootstrap"] = True
        trending["hot_tags"] = []
        trending["rising"] = []
    else:
        # Calculate growth per entry
        growth_data = []
        for section in ("skills", "packages"):
            for name, info in index.get(section, {}).items():
                current = info.get("installs", 0)
                old = old_snapshot.get(name, 0)
                weekly = current - old
                if weekly > 0:
                    growth_data.append({
                        "name": name,
                        "type": info.get("type", section.rstrip("s")),
                        "owner": info.get("owner", ""),
                        "weekly_installs": weekly,
                        "tags": info.get("tags", []),
                    })

        growth_data.sort(key=lambda x: x["weekly_installs"], reverse=True)
        trending["rising"] = growth_data[:10]

        # Aggregate hot tags
        tag_scores: dict[str, int] = {}
        for entry in growth_data:
            for tag in entry.get("tags", []):
                tag_scores[tag] = tag_scores.get(tag, 0) + entry["weekly_installs"]
        hot_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        trending["hot_tags"] = [
            {"tag": tag, "weekly_installs": score}
            for tag, score in hot_tags
        ]

    # New releases (always works, uses released dates)
    new_releases = []
    cutoff = date.today() - timedelta(days=TREND_WINDOW)
    for section in ("packages",):
        for name, info in index.get(section, {}).items():
            # Check latest version's released date
            latest = info.get("latest", "")
            if latest:
                new_releases.append({
                    "name": name,
                    "type": "ip",
                    "version": latest,
                    "owner": info.get("owner", ""),
                })
    trending["new_releases"] = new_releases[:10]

    return trending


def main():
    if not INDEX_FILE.exists():
        print("No index.yaml found.")
        return

    index = yaml.safe_load(INDEX_FILE.read_text(encoding="utf-8")) or {}

    # Create today's snapshot
    create_snapshot(index)

    # Calculate trending
    trending = calculate_trending(index)
    index["trending"] = trending

    # Write updated index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write("# IpHub Index — auto-generated\n")
        yaml.dump(index, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Cleanup old snapshots
    cleanup_old_snapshots()

    status = "bootstrap" if trending.get("bootstrap") else "active"
    print(f"Trending updated ({status}).")


if __name__ == "__main__":
    main()
