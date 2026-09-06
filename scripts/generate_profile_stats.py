#!/usr/bin/env python3
"""Generate a dependency-free SVG profile badge from GitHub API data."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def api(url: str, token: str | None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Ru0k3-profile-stats"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def esc(value: object) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def main() -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("PROFILE_OWNER")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN")
    if not owner:
        raise SystemExit("GITHUB_REPOSITORY_OWNER or PROFILE_OWNER is required")

    user = api(f"https://api.github.com/users/{owner}", token)
    repos = api(f"https://api.github.com/users/{owner}/repos?per_page=100&type=owner", token)
    stars = sum(int(item.get("stargazers_count", 0)) for item in repos)
    forks = sum(int(item.get("forks_count", 0)) for item in repos)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    values = [("Repos", user.get("public_repos", 0)), ("Followers", user.get("followers", 0)), ("Stars", stars), ("Forks", forks)]

    rows = []
    for index, (label, value) in enumerate(values):
        x = 70 + index * 300
        rows.append(f'<text x="{x}" y="51" text-anchor="middle" fill="#94A3B8" font-size="14">{esc(label)}</text>')
        rows.append(f'<text x="{x}" y="91" text-anchor="middle" fill="#22D3EE" font-size="30" font-weight="700">{esc(value)}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="126" viewBox="0 0 1200 126" role="img" aria-labelledby="title desc">
<title id="title">Ru0k3 GitHub profile statistics</title>
<desc id="desc">Live public repositories, followers, stars, and forks updated daily.</desc>
<rect width="1200" height="126" rx="14" fill="#0A101F" stroke="#22D3EE" stroke-opacity=".7"/>
<text x="28" y="23" fill="#A78BFA" font-family="Consolas,Menlo,monospace" font-size="12">LIVE PROFILE TELEMETRY · {esc(now)}</text>
{''.join(rows)}
<text x="1170" y="113" text-anchor="end" fill="#64748B" font-family="Consolas,Menlo,monospace" font-size="11">{esc(repo)}</text>
</svg>\n'''
    (ROOT / "profile-stats.svg").write_text(svg, encoding="utf-8")
    (ROOT / "profile-stats.json").write_text(json.dumps({"updated": now, "owner": owner, "repository": repo, "stats": dict(values)}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated profile stats for {owner}: {dict(values)}")


if __name__ == "__main__":
    main()
