#!/usr/bin/env python3
# ABOUTME: Renders favicon.svg to the PNG favicon sizes with headless Chromium.
# ABOUTME: Run once and commit the PNGs; re-run whenever favicon.svg changes.

import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "favicon.svg"

TARGETS = [
    (32, ROOT / "favicon-32.png"),
    (180, ROOT / "apple-touch-icon.png"),
]


def sized_svg(svg_text: str, size: int) -> str:
    resized = re.sub(r'width="128"', f'width="{size}"', svg_text, count=1)
    resized = re.sub(r'height="128"', f'height="{size}"', resized, count=1)
    return resized


def render():
    svg_text = SVG_PATH.read_text()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for size, out_path in TARGETS:
                page = browser.new_page(viewport={"width": size, "height": size})
                html = f"<html><body style='margin:0'>{sized_svg(svg_text, size)}</body></html>"
                page.set_content(html)
                page.screenshot(path=str(out_path))
                page.close()
                print(f"wrote {out_path} ({size}x{size})")
        finally:
            browser.close()


if __name__ == "__main__":
    render()
