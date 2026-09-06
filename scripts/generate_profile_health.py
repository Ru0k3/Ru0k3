#!/usr/bin/env python3
"""Write a weekly Markdown health report from GitHub repository and Actions data."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import json

ROOT = Path(__file__).resolve().parents[1]

def api(url: str, token: str | None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Ru0k3-profile-health"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)

def main() -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("PROFILE_OWNER")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not owner or not repository:
        raise SystemExit("GitHub repository context is required")

    user = api(f"https://api.github.com/users/{owner}", token)
    repo = api(f"https://api.github.com/repos/{repository}", token)
    runs = api(f"https://api.github.com/repos/{repository}/actions/runs?per_page=20", token).get("workflow_runs", [])
    workflows = {}
    for run in runs:
        workflows.setdefault(run.get("name", "Unknown"), run)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Weekly GitHub Profile Health Report",
        "",
        f"Generated: **{updated}**",
        "",
        "## Profile statistics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Public repositories | {user.get('public_repos', 0)} |",
        f"| Followers | {user.get('followers', 0)} |",
        f"| Following | {user.get('following', 0)} |",
        f"| Repository stars | {repo.get('stargazers_count', 0)} |",
        f"| Repository forks | {repo.get('forks_count', 0)} |",
        "",
        "## Workflow health",
        "",
        "| Workflow | Latest status | Conclusion | Last run |",
        "|---|---|---|---|",
    ]
    for name, run in sorted(workflows.items()):
        lines.append(f"| {name} | {run.get('status', 'unknown')} | {run.get('conclusion', '—')} | {run.get('updated_at', '—')} |")
    if not workflows:
        lines.append("| No recent workflow runs found | — | — | — |")
    lines += [
        "",
        "> This report is generated automatically each week. GitHub statistics cards in the README remain live and are refreshed by their providers when the profile is viewed.",
        "",
    ]
    (ROOT / "PROFILE_HEALTH.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated weekly health report with {len(workflows)} workflow entries")

if __name__ == "__main__":
    main()
