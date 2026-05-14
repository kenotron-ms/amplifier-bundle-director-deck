#!/usr/bin/env python3
"""
Screenshot each slide from a wireframe HTML deck at 1536x864 (16:9).

Uses device_scale_factor=1.6 so 960px CSS elements render at 1536px physical pixels.

Usage:
    python scripts/screenshot_wireframe.py <run_dir>

Example:
    python scripts/screenshot_wireframe.py runs/2026-04-30-compounding-stack-director
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def screenshot_wireframe(run_dir: Path) -> list[Path]:
    html_path = run_dir / "deck_wireframe.html"
    keyframes_dir = run_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    # Load JSON to get slide count
    import json
    with open(run_dir / "slide_deck.json") as f:
        deck = json.load(f)
    slide_count = deck["meta"]["slide_count"]

    print(f"Screenshotting {slide_count} slides from {html_path}")
    print(f"Output: {keyframes_dir}")

    # Scale factor: 960px CSS * 1.6 = 1536px physical | 540px * 1.6 = 864px
    DEVICE_SCALE = 1.6
    CSS_W, CSS_H = 960, 540

    png_paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use device_scale_factor to render at 1536x864 physical pixels
        context = browser.new_context(
            viewport={"width": CSS_W, "height": CSS_H},
            device_scale_factor=DEVICE_SCALE,
        )
        page = context.new_page()
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")

        for n in range(1, slide_count + 1):
            out_path = keyframes_dir / f"slide-{n}.png"
            element = page.query_selector(f"#slide-{n}")
            if element is None:
                browser.close()
                raise RuntimeError(f"Element #slide-{n} not found in HTML")
            element.screenshot(path=str(out_path))
            png_paths.append(out_path)
            print(f"  slide-{n}.png → {out_path}")

        browser.close()

    print(f"\nDone. {len(png_paths)} keyframes written.")
    return png_paths


if __name__ == "__main__":
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "runs/2026-04-30-compounding-stack-director"
    )
    screenshot_wireframe(run_dir)
