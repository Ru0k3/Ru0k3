#!/usr/bin/env python3
"""Refresh the profile avatar and rendered banner assets.

The GitHub Actions workflow supplies the repository owner's current avatar URL.
The script keeps the source SVGs and the GitHub-safe PNG banners synchronized.
"""
from __future__ import annotations

import base64
import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import cairosvg
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
AVATAR_PATH = ROOT / "profile-avatar.png"
SVG_NAMES = ("light_mode.svg", "dark_mode.svg")
PNG_NAMES = ("light_mode.png", "dark_mode.png")
IMAGE_DATA_RE = re.compile(r"data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=]+")


def fetch_avatar(url: str) -> Image.Image:
    request = Request(url, headers={"User-Agent": "Ru0k3-profile-assets-updater"})
    with urlopen(request, timeout=30) as response:
        data = response.read()
    with Image.open(BytesIO(data)) as image:
        image = ImageOps.fit(image.convert("RGB"), (460, 460), method=Image.Resampling.LANCZOS)
        return image.copy()


def update_svg_avatar(path: Path, jpeg_data_uri: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not IMAGE_DATA_RE.search(text):
        raise RuntimeError(f"No embedded avatar data URI found in {path}")
    updated = IMAGE_DATA_RE.sub(jpeg_data_uri, text, count=1)
    path.write_text(updated, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: update_profile_assets.py AVATAR_URL")

    avatar = fetch_avatar(sys.argv[1])
    avatar.save(AVATAR_PATH, format="PNG", optimize=True)

    jpeg_buffer = BytesIO()
    avatar.save(jpeg_buffer, format="JPEG", quality=96, optimize=True, progressive=True, subsampling=0)
    jpeg_data_uri = "data:image/jpeg;base64," + base64.b64encode(jpeg_buffer.getvalue()).decode("ascii")

    for name in SVG_NAMES:
        update_svg_avatar(ROOT / name, jpeg_data_uri)

    for svg_name, png_name in zip(SVG_NAMES, PNG_NAMES):
        cairosvg.svg2png(
            url=str(ROOT / svg_name),
            write_to=str(ROOT / png_name),
            output_width=1400,
            output_height=620,
        )

    print("Updated profile-avatar.png, light_mode.svg/.png, and dark_mode.svg/.png")


if __name__ == "__main__":
    main()
