#!/usr/bin/env python3
"""Sync .velarium/status.json into site/data/, enriching with latest commit info."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_FILE = REPO_ROOT / ".velarium" / "status.json"
SITE_DATA_DIR = REPO_ROOT / "site" / "data"
PROJECTS_DIR = SITE_DATA_DIR / "projects"
GITHUB_API_COMMITS = "https://api.github.com/repos/VRM-AI/vcse/commits/main"


def fetch_github_commit():
    req = urllib.request.Request(
        GITHUB_API_COMMITS,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "vcse-site-sync/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        sha = data["sha"]
        message = data["commit"]["message"].splitlines()[0]
        committed_at = data["commit"]["committer"]["date"]
        url = data["html_url"]
        return {"sha": sha, "short_sha": sha[:7], "message": message, "url": url, "committed_at": committed_at}
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"GitHub API unavailable ({exc}), falling back to local git.", file=sys.stderr)
        return None


def fetch_local_git_commit():
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        message = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"], cwd=REPO_ROOT, text=True
        ).strip()
        committed_at = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"], cwd=REPO_ROOT, text=True
        ).strip()
        url = f"https://github.com/VRM-AI/vcse/commit/{sha}"
        return {"sha": sha, "short_sha": sha[:7], "message": message, "url": url, "committed_at": committed_at}
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        print(f"Local git fallback failed: {exc}", file=sys.stderr)
        return None


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True


def main():
    if not STATUS_FILE.exists():
        sys.exit(f"ERROR: status file not found: {STATUS_FILE}")

    status = json.loads(STATUS_FILE.read_text())

    latest_commit = fetch_github_commit() or fetch_local_git_commit()
    if latest_commit is None:
        sys.exit("ERROR: both GitHub API and local git fallback failed — cannot determine latest commit")

    project = {
        "project_id": status["project_id"],
        "project_name": status["project_name"],
        "project_full_name": status.get("project_full_name", ""),
        "organization": status["organization"],
        "repo": status["repo"],
        "public_url": status.get("public_url", ""),
        "current_version": status["current_version"],
        "latest_release_tag": status["latest_release_tag"],
        "latest_release_url": status["latest_release_url"],
        "latest_validated_release": status["latest_validated_release"],
        "latest_commit": latest_commit,
        "validation": status["validation"],
        "capabilities": status["capabilities"],
        "roadmap": status["roadmap"],
        "immediate_focus": status["immediate_focus"],
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    vcse_json = json.dumps(project, indent=2) + "\n"
    changed_vcse = write_if_changed(PROJECTS_DIR / "vcse.json", vcse_json)

    projects_index = json.dumps([project], indent=2) + "\n"
    changed_index = write_if_changed(SITE_DATA_DIR / "projects.json", projects_index)

    if changed_vcse:
        print(f"Updated: {PROJECTS_DIR / 'vcse.json'}")
    if changed_index:
        print(f"Updated: {SITE_DATA_DIR / 'projects.json'}")
    if not changed_vcse and not changed_index:
        print("No changes.")

    print(f"Latest commit: {latest_commit['short_sha']} — {latest_commit['message']}")


if __name__ == "__main__":
    main()
