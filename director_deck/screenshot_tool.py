from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def screenshot_deck(
    html_path: Path,
    output_dir: Path,
    slide_count: int,
) -> list[Path]:
    """
    Screenshot each slide div from a rendered HTML deck file.

    Opens headless Chromium at a 960×540 viewport, loads the HTML via file://
    URL, then captures ``#slide-N`` elements (1-indexed) as PNGs.

    Args:
        html_path: Absolute (or resolvable) path to the deck HTML file.
        output_dir: Directory to write PNGs into (created if it does not exist).
        slide_count: Number of slides to capture; must match actual slide divs.

    Returns:
        List of Paths to the created PNG files in slide order:
        ``[output_dir/slide-1.png, output_dir/slide-2.png, ...]``

    Raises:
        RuntimeError: If ``#slide-N`` is not found in the DOM for any N.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    png_paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 960, "height": 540})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")

        for n in range(1, slide_count + 1):
            out_path = output_dir / f"slide-{n}.png"
            element = page.query_selector(f"#slide-{n}")
            if element is None:
                browser.close()
                raise RuntimeError(
                    f"Slide element #slide-{n} not found in {html_path}. "
                    "Ensure slide IDs are 1-indexed in the rendered HTML."
                )
            element.screenshot(path=str(out_path))
            png_paths.append(out_path)

        browser.close()

    return png_paths
