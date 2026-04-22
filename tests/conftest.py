import pytest

# ---------------------------------------------------------------------------
# Module-level constants — import these directly in tests that need raw data
# ---------------------------------------------------------------------------

SAMPLE_DECK_DATA: dict = {
    "meta": {"title": "Test Deck", "prompt": "test prompt", "slide_count": 2},
    "slides": [
        {
            "id": 1,
            "title": "Slide One",
            "bullets": ["Point A", "Point B"],
            "speaker_notes": "Emphasise the scale of the pain.",
            "image_brief": "A lone developer staring at a wall of error logs, cinematic",
            "backdrop_brief": "Dark gradient, subtle circuit board texture, no text",
        },
        {
            "id": 2,
            "title": "Slide Two",
            "bullets": ["Point C"],
            "speaker_notes": "Show the solution clearly.",
            "image_brief": "A clean dashboard with green metrics and happy users",
            "backdrop_brief": "Soft light gradient, minimal texture, no people",
        },
    ],
}

SAMPLE_DESIGN_MD: str = """\
---
name: Test Deck
colors:
  primary: "#0F172A"
  accent: "#38BDF8"
  surface: "#1E293B"
  on-surface: "#F1F5F9"
typography:
  h1:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: 700
  body-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
spacing:
  slide-padding: 64px
  section-gap: 32px
---

## Overview
High-stakes tech pitch. Clean, confident, dark-mode-first.

## Colors
- **Primary (#0F172A):** Near-black slide backgrounds.
- **Accent (#38BDF8):** Sky blue for headlines and key callouts only.

## Do's and Don'ts
- Do use accent only on the single most important element per slide
"""


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_deck_data() -> dict:
    return SAMPLE_DECK_DATA


@pytest.fixture
def sample_design_md(tmp_path):
    """Write SAMPLE_DESIGN_MD to a temp file and return its Path."""
    p = tmp_path / "DESIGN.md"
    p.write_text(SAMPLE_DESIGN_MD, encoding="utf-8")
    return p
