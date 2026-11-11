#!/usr/bin/env python3
"""Build the four README panels locally from live GitHub data.

Writes panels/city.svg, panels/stats.svg, panels/projects.svg and panels/social.svg.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "panels"

BG_A, BG_B = "#042f2e", "#134e4a"
TEAL, TEAL_HI = "#2dd4bf", "#5eead4"
TEXT, MUTED = "#e6fdf6", "#8fb3aa"
WIDTH = 860
MONO = "'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif"


def api(url: str, token: str | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Ru0k3-panels"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def graphql(query: str, token: str | None) -> dict:
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Ru0k3-panels",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        raise RuntimeError(payload["errors"][0]["message"])
    return payload["data"]


def esc(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def shade(color: str, factor: float) -> str:
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    clamp = lambda v: max(0, min(255, int(v)))
    return "#%02x%02x%02x" % (clamp(r * factor), clamp(g * factor), clamp(b * factor))


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def wrap(text: str, limit: int, lines: int) -> list[str]:
    words, out, line = text.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) <= limit:
            line = candidate
        else:
            if line:
                out.append(line)
            line = word
            if len(out) == lines:
                break
    if line and len(out) < lines:
        out.append(line)
    if len(out) == lines and (len(" ".join(out)) < len(text)):
        out[-1] = out[-1][: limit - 1].rstrip() + "…"
    return out


def frame(svg_id: str, height: int, aria: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{esc(aria)}">',
        "<defs>",
        f'<linearGradient id="{svg_id}-bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{BG_A}"/><stop offset="54%" stop-color="{BG_B}"/>'
        f'<stop offset="100%" stop-color="{BG_A}"/></linearGradient>',
        f'<radialGradient id="{svg_id}-glow"><stop stop-color="{TEAL}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{WIDTH}" height="{height}" rx="18" fill="url(#{svg_id}-bg)"/>',
        f'<ellipse cx="660" cy="{height // 2}" rx="320" ry="{height // 2}" fill="url(#{svg_id}-glow)"/>',
        f'<rect x="1" y="1" width="{WIDTH - 2}" height="{height - 2}" rx="17" fill="none" '
        f'stroke="{TEAL}" stroke-opacity=".3"/>',
    ]


def text(value: str, x: float, y: float, size: float = 12, fill: str = MUTED,
         family: str = MONO, weight: int = 400, spacing: float = 0, anchor: str = "start") -> str:
    bits = [f'x="{x:g}"', f'y="{y:g}"', f'font-family="{family}"', f'font-size="{size:g}"', f'fill="{fill}"']
    if weight != 400:
        bits.append(f'font-weight="{weight}"')
    if spacing:
        bits.append(f'letter-spacing="{spacing:g}"')
    if anchor != "start":
        bits.append(f'text-anchor="{anchor}"')
    return f'<text {" ".join(bits)}>{esc(value)}</text>'


def city_svg(calendar: dict, owner: str) -> str:
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    counts = [int(day["contributionCount"]) for day in days]
    total, busiest = sum(counts), max(counts)
    active = sum(1 for c in counts if c)

    weeks: list[list[int]] = []
    for day in days:
        if int(day["weekday"]) == 0 or not weeks:
            weeks.append([0] * 7)
        weeks[-1][int(day["weekday"])] = int(day["contributionCount"])

    def level(count: int) -> str:
        if count <= 0:
            return "#0c3b36"
        if count <= 2:
            return "#0f766e"
        if count <= 5:
            return "#14b8a6"
        if count <= 9:
            return TEAL
        return TEAL_HI

    w, h, ox, oy = 7.0, 3.5, 470.0, 150.0
    cells = sorted(
        (col + row, col, row, count)
        for col, week in enumerate(weeks)
        for row, count in enumerate(week)
    )
    city: list[str] = []
    for _, col, row, count in cells:
        x, y = ox + (col - row) * w, oy + (col + row) * h
        height = 0.0 if count == 0 else 3.0 + 5.0 * math.sqrt(count)
        base = level(count)
        top, left, right = shade(base, 1.35), shade(base, 0.5), shade(base, 0.78)
        if count == 0:
            top = left = right = base
        city.append(
            f'<polygon points="{x:.1f},{y - height:.1f} {x + w:.1f},{y - height - h:.1f} '
            f'{x + w:.1f},{y - h:.1f} {x:.1f},{y - height + h:.1f}" fill="{top}"/>'
            f'<polygon points="{x:.1f},{y - height + h:.1f} {x + w:.1f},{y - h:.1f} '
            f'{x + w:.1f},{y:.1f} {x:.1f},{y + h:.1f}" fill="{right}"/>'
            f'<polygon points="{x - w:.1f},{y - height:.1f} {x:.1f},{y - height + h:.1f} '
            f'{x:.1f},{y + h:.1f} {x - w:.1f},{y:.1f}" fill="{left}"/>'
        )

    lines = frame("city", 420, f"Contribution city: {total} contributions in the last year")
    lines += [
        text("CONTRIBUTION CITY", 30, 44, 12, TEAL_HI, spacing=2),
        text("last 12 months", 830, 44, 11, MUTED, anchor="end"),
        text(f"{total}", 30, 116, 52, TEXT, family=SANS, weight=700),
        text("contributions in the last year", 30, 140, 12, MUTED),
        text(f"{active} active days", 30, 176, 12, MUTED),
        text(f"Busiest day: {busiest}", 30, 196, 12, MUTED),
        text(f"@{owner}", 830, 392, 11, MUTED, anchor="end"),
        '<g shape-rendering="geometricPrecision">',
        *city,
        "</g>",
        text("every tile is a day · taller means more contributions", 30, 392, 11, MUTED),
    ]
    return "\n".join(lines + ["</svg>"])


def stats_svg(stats: list[tuple[str, int]]) -> str:
    height = 268
    lines = frame("stats", height, "Profile signal: stars, contributions, repos, followers")
    lines += [
        text("Profile Signal", 30, 56, 26, TEXT, family=SANS, weight=700),
        text("live GitHub stats, rendered locally", 30, 78, 11, MUTED),
    ]
    peak = max(value for _, value in stats) or 1
    for index, (name, value) in enumerate(stats):
        x, y = 30 + index * 200, 104
        fill_ratio = max(0.04, value / peak)
        lines += [
            f'<rect x="{x}" y="{y}" width="190" height="126" rx="14" fill="#06201e" '
            f'stroke="{TEAL}" stroke-opacity=".22"/>',
            text(name.upper(), x + 18, y + 34, 10, MUTED, spacing=1.5),
            text(f"{value}", x + 18, y + 88, 40, TEXT, family=SANS, weight=700),
            f'<rect x="{x + 18}" y="{y + 104}" width="154" height="6" rx="3" fill="{TEAL}" fill-opacity=".12"/>',
            f'<rect x="{x + 18}" y="{y + 104}" width="{154 * fill_ratio:.1f}" height="6" rx="3" fill="{TEAL}"/>',
        ]
    return "\n".join(lines + ["</svg>"])


def projects_svg(repos: list[dict]) -> str:
    height = 112 + 2 * 158
    lines = frame("projects", height, "Recent projects")
    lines += [
        text("PROJECTS.LIST", 30, 44, 12, TEAL_HI, spacing=2),
        text("./projects.sh --all", 176, 44, 11, MUTED),
        text(f"{len(repos)} projects", 830, 44, 11, MUTED, anchor="end"),
        f'<line x1="30" y1="58" x2="830" y2="58" stroke="{TEAL}" stroke-opacity=".35"/>',
    ]
    for index, repo in enumerate(repos):
        col, row = index % 2, index // 2
        x, y = 30 + col * 400, 78 + row * 158
        description = repo.get("description") or "No description provided."
        lines += [
            f'<rect x="{x}" y="{y}" width="380" height="142" rx="12" fill="#06201e" '
            f'stroke="{TEAL}" stroke-opacity=".2"/>',
            text(cut(repo["name"], 32), x + 18, y + 36, 17, TEXT, family=SANS, weight=700),
        ]
        for offset, chunk in enumerate(wrap(description, 48, 2)):
            lines.append(text(chunk, x + 18, y + 60 + offset * 16, 12, MUTED))
        pill = repo.get("language") or "code"
        pill_width = 12 + 7.2 * len(pill)
        lines += [
            f'<rect x="{x + 18}" y="{y + 104}" width="{pill_width:.0f}" height="20" rx="10" '
            f'fill="{TEAL}" fill-opacity=".12"/>',
            text(pill, x + 18 + pill_width / 2, y + 118, 11, TEAL_HI, anchor="middle"),
            text(
                f"{repo.get('stargazers_count', 0)} stars · updated {repo.get('age', 'recently')}",
                x + 362, y + 118, 11, MUTED, anchor="end",
            ),
        ]
    return "\n".join(lines + ["</svg>"])


def social_svg(links: list[tuple[str, str]]) -> str:
    rows: list[list[tuple[str, str, float]]] = [[]]
    used = 0.0
    for name, value in links:
        width = max(120.0, 96 + 6.4 * len(value))
        if used + width > 800 and rows[-1]:
            rows.append([])
            used = 0.0
        rows[-1].append((name, value, width))
        used += width + 14

    height = 44 + 62 * len(rows)
    lines = frame("social", height, "Links: GitHub, portfolio, LinkedIn, Instagram, email")
    for row_index, row in enumerate(rows):
        total = sum(item[2] for item in row) + 14 * (len(row) - 1)
        x = (WIDTH - total) / 2
        y = 34 + row_index * 62
        for name, value, width in row:
            lines += [
                f'<rect x="{x:.1f}" y="{y}" width="{width:.0f}" height="48" rx="24" fill="#06201e" '
                f'stroke="{TEAL}" stroke-opacity=".3"/>',
                f'<circle cx="{x + 26:.1f}" cy="{y + 24}" r="13" fill="{TEAL}" fill-opacity=".16"/>',
                text(name[0], x + 26, y + 29, 13, TEAL_HI, family=SANS, weight=700, anchor="middle"),
                text(name, x + 46, y + 19, 9, MUTED, spacing=1.2),
                text(cut(value, 30), x + 46, y + 35, 12, TEXT, family=SANS, weight=600),
            ]
            x += width + 14
    return "\n".join(lines + ["</svg>"])


HERO = ROOT / "living-identity.svg"


def refresh_hero(values: dict[str, int]) -> bool:
    """Keep the committed hero panel's stat row in sync with live numbers."""
    if not HERO.exists():
        return False
    svg = original = HERO.read_text()
    for name, value in values.items():
        pattern = rf'(>{name}</text><text y="38" fill="#e6fdf6" font-size="28">)\d+'
        svg = re.sub(pattern, lambda m: m.group(1) + str(value), svg)
    desc = ", ".join(f"{name.title()}: {value}" for name, value in values.items())
    svg = re.sub(r"(<desc>.*?)(REPOSITORIES: \d+.*?FOLLOWERS: \d+)", lambda m: m.group(1) + desc, svg)
    if svg == original:
        return False
    HERO.write_text(svg)
    return True


def main() -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("PROFILE_OWNER")
    token = os.environ.get("GITHUB_TOKEN")
    if not owner:
        raise SystemExit("GITHUB_REPOSITORY_OWNER or PROFILE_OWNER is required")

    user = api(f"https://api.github.com/users/{owner}", token)
    repos = api(f"https://api.github.com/users/{owner}/repos?per_page=100&type=owner&sort=pushed", token)
    calendar = graphql(
        f'query {{ user(login: "{owner}") {{ contributionsCollection {{ contributionCalendar '
        f"{{ totalContributions weeks {{ contributionDays {{ date contributionCount weekday }} }} }} }} }} }}",
        token,
    )["user"]["contributionsCollection"]["contributionCalendar"]

    now = datetime.now(timezone.utc)
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    owned = [repo for repo in repos if not repo.get("fork") and repo["name"].lower() != owner.lower()]
    owned.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)
    top = []
    for repo in owned[:4]:
        pushed = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        days = max(0, (now - pushed).days)
        repo["age"] = f"{days}d ago" if days else "today"
        top.append(repo)

    social = [
        ("GitHub", f"@{owner}"),
        ("Website", "ru0k3.github.io"),
        ("LinkedIn", "venkata-rama-krishna-dulam"),
        ("Instagram", "@r._krishna_21"),
        ("Email", "ramakrishnadulam10@gmail.com"),
    ]
    values = {
        "REPOSITORIES": int(user.get("public_repos", 0)),
        "STARS": stars,
        "CONTRIBUTIONS": int(calendar["totalContributions"]),
        "FOLLOWERS": int(user.get("followers", 0)),
    }
    panels = {
        "city.svg": city_svg(calendar, owner),
        "stats.svg": stats_svg(
            [
                ("Stars", stars),
                ("Contributions", calendar["totalContributions"]),
                ("Repos", user.get("public_repos", 0)),
                ("Followers", user.get("followers", 0)),
            ]
        ),
        "projects.svg": projects_svg(top),
        "social.svg": social_svg(social),
    }

    OUT.mkdir(exist_ok=True)
    changed = []
    for name, svg in panels.items():
        target = OUT / name
        if target.exists() and target.read_text() == svg:
            continue
        target.write_text(svg)
        changed.append(name)
    if refresh_hero(values):
        changed.append("living-identity.svg")
    print(f"panels updated: {', '.join(changed) if changed else 'none'}")


if __name__ == "__main__":
    sys.exit(main())
