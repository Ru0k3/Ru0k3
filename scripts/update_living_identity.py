#!/usr/bin/env python3
"""Refresh living-identity.svg: fetch the GitSkins hero panel and recolor it green."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "living-identity.svg"

# Blue/purple accents of the source panel -> the teal/emerald palette of the rest of the README.
RECOLOR = {
    "#3178c6": "#2dd4bf",
    "#b594ff": "#34d399",
    "#8a9bb9": "#8fb3aa",
    "#ecf4ff": "#e6fdf6",
    "#080c18": "#06110f",
}


def main() -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("PROFILE_OWNER")
    if not owner:
        raise SystemExit("GITHUB_REPOSITORY_OWNER or PROFILE_OWNER is required")

    user = Request(f"https://api.github.com/users/{owner}", headers={"User-Agent": "Ru0k3-living-identity"})
    with urlopen(user, timeout=30) as response:
        avatar = json.load(response)["avatar_url"]

    url = (
        f"https://www.gitskins.com/api/section/hero?username={owner.lower()}&theme=aurora"
        f"&avatar={quote(avatar, safe='')}&variant=living-identity"
    )
    svg = urlopen(Request(url, headers={"User-Agent": "Ru0k3-living-identity"}), timeout=60).read().decode("utf-8")

    if "<svg" not in svg or len(svg) < 20_000:
        raise SystemExit(f"unexpected panel payload ({len(svg)} bytes); keeping existing SVG")

    for old, new in RECOLOR.items():
        svg = svg.replace(old, new)
    if "pro preview" in svg.lower():
        print("source panel is watermarked; keeping existing SVG")
        return
    if "#2dd4bf" not in svg or "#3178c6" in svg:
        raise SystemExit("recolor check failed; keeping existing SVG")

    current = TARGET.read_text() if TARGET.exists() else ""
    if svg == current:
        print("living-identity.svg is already current")
        return

    TARGET.write_text(svg)
    print(f"updated {TARGET.name} ({len(svg)} bytes)")


if __name__ == "__main__":
    sys.exit(main())
