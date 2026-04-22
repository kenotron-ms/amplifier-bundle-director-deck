# Director Deck — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build amplifier-bundle-director-deck — a 5-agent Amplifier bundle that turns a text prompt into a polished PPTX with AI-generated images and Veo 3.1 video transitions.

**Architecture:** Python package `director_deck` with 4 utility tools, 5 agent markdown files, and a staged recipe with 3 human approval gates. DESIGN.md (Stitch spec format) drives visual identity across all agents.

**Tech Stack:** python-pptx, playwright, Pydantic v2, PyYAML, @google/design.md (npm), Veo 3.1, amplifier-module-tool-openai-images

---

## File Map

All files created by this plan. The repo root IS the bundle root.

```
(repo root)/
├── bundle.md
├── pyproject.toml
├── director_deck/
│   ├── __init__.py
│   ├── schema.py              # Pydantic models: SlideDeck, DesignTokens, disk I/O
│   ├── html_renderer.py       # DESIGN.md tokens → CSS vars + per-slide HTML at 960×540
│   ├── pptx_builder.py        # SlideDeck → PPTX wireframe/enriched via python-pptx
│   ├── screenshot_tool.py     # Playwright headless: HTML file → per-slide PNG keyframes
│   └── pptx_stitcher.py       # Embed MP4 transitions into PPTX zip + <p:transition> XML
├── agents/
│   ├── ghost-deck-writer.md   # Prompt → slide_deck.json + DESIGN.md
│   ├── slide-architect.md     # slide_deck.json + DESIGN.md → HTML + PPTX
│   ├── visual-director.md     # Image briefs + DESIGN.md → generated assets
│   ├── transition-director.md # HTML slides → Veo 3.1 transition clips
│   └── deck-stitcher.md       # All assets → final_deck.pptx
├── recipes/
│   └── director-deck.yaml     # Staged recipe: 4 work stages + 3 approval gates
├── runs/
│   └── .gitkeep
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures: SAMPLE_DECK_DATA, SAMPLE_DESIGN_MD
    ├── test_schema.py
    ├── test_html_renderer.py
    ├── test_pptx_builder.py
    ├── test_screenshot_tool.py
    └── test_pptx_stitcher.py
```

**Module responsibilities:**

| File | Owns |
|---|---|
| `schema.py` | All Pydantic models; `SlideDeck.from_file/to_file`; `DesignTokens.from_design_md`; `_extract_frontmatter` |
| `html_renderer.py` | `tokens_to_css_vars`, `render_deck_html`, `write_deck_html`; no disk I/O except write helper |
| `pptx_builder.py` | `build_pptx`, `_add_slide`, `_hex_to_rgb`; slide layout constants |
| `screenshot_tool.py` | `screenshot_deck`; all Playwright lifecycle |
| `pptx_stitcher.py` | `embed_transitions`, `_add_video_relationship`, `_inject_transition`; zip manipulation |
| `agents/*.md` | LLM system prompts consumed by Amplifier runtime |
| `recipes/director-deck.yaml` | Top-level orchestration; wires all agents with gates |
| `tests/conftest.py` | `SAMPLE_DECK_DATA` dict, `SAMPLE_DESIGN_MD` str, pytest fixtures wrapping them |

---

## Task 1 — Scaffolding

**Goal:** Lay out the full directory structure and install dependencies. No logic yet.

### Steps

- [ ] Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "director-deck"
version = "0.1.0"
description = "Amplifier bundle: AI-powered slide deck generator with Veo 3.1 transitions"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "python-pptx>=0.6.23",
    "playwright>=1.44",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-cov>=5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests that require external tools (playwright, network)",
]

[tool.hatch.build.targets.wheel]
packages = ["director_deck"]
```

- [ ] Create `bundle.md`:

```markdown
---
name: director-deck
version: 0.1.0
description: "Turn a text prompt into a polished PPTX with AI-generated images and Veo 3.1 video transitions"
agents:
  - agents/ghost-deck-writer.md
  - agents/slide-architect.md
  - agents/visual-director.md
  - agents/transition-director.md
  - agents/deck-stitcher.md
tools:
  - director_deck/html_renderer.py
  - director_deck/pptx_builder.py
  - director_deck/screenshot_tool.py
  - director_deck/pptx_stitcher.py
recipes:
  - recipes/director-deck.yaml
external_deps:
  - amplifier-module-tool-openai-images
  - veo (Amplifier built-in)
---

# Director Deck

An Amplifier bundle that transforms a plain-text prompt into a polished PowerPoint deck
with AI-generated images and Veo 3.1 video transitions between slides.

## Workflow

```
prompt → ghost-deck-writer → slide-architect → [Gate 1: content & identity review]
       → visual-director → slide-architect (enriched) → [Gate 2: visual review]
       → transition-director → [Gate 3: transition review]
       → deck-stitcher → final_deck.pptx
```

## Usage

```bash
amplifier recipe run recipes/director-deck.yaml \
  --context prompt="Series A pitch for a B2B SaaS devtools company"
```

## Run Directory Structure

Each run is isolated under `./runs/<date>-<slug>/`:

```
runs/2026-04-22-series-a-pitch/
├── DESIGN.md            # Visual identity (Google Stitch DESIGN.md spec)
├── slide_deck.json      # Slide content — shared contract between all agents
├── deck_wireframe.html
├── deck_wireframe.pptx
├── deck_enriched.html
├── deck_enriched.pptx
├── assets/              # Generated content images and backdrops
├── keyframes/           # Playwright PNG screenshots (Veo input)
├── transitions/         # Veo 3.1 MP4 clips
└── final_deck.pptx
```
```

- [ ] Create empty package and test init files:

```bash
mkdir -p director_deck agents recipes runs tests
touch director_deck/__init__.py tests/__init__.py runs/.gitkeep
```

- [ ] Install dependencies:

```bash
pip install -e ".[dev]"
playwright install chromium
```

- [ ] Verify installation:

```bash
python -c "import director_deck; print('package importable')"
pytest --collect-only
# Expected: 0 tests collected, no errors
```

- [ ] Commit:

```bash
git add . && git commit -m "feat: scaffold director-deck bundle structure"
```

---

## Task 2 — Schema

**Goal:** Pydantic v2 models for `SlideDeck` (all slide content) and `DesignTokens` (parsed from DESIGN.md YAML frontmatter). These are the shared data contracts consumed by every other module.

### TDD — Write tests first

Create `tests/conftest.py`:

```python
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
High-stakes tech pitch. Clean, confident, dark-mode-first. Every slide should
feel like a Bloomberg terminal meets a well-funded startup.

## Colors
- **Primary (#0F172A):** Near-black slide backgrounds.
- **Accent (#38BDF8):** Sky blue for headlines and key callouts only.
- **Surface (#1E293B):** Card and panel backgrounds.

## Do's and Don'ts
- Do use accent only on the single most important element per slide
- Don't use more than 2 fonts
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
```

Create `tests/test_schema.py`:

```python
import pytest
from pathlib import Path
from director_deck.schema import (
    Slide,
    SlideAssets,
    DeckMeta,
    SlideDeck,
    DesignColors,
    DesignTypographyEntry,
    DesignTokens,
    _extract_frontmatter,
)
from tests.conftest import SAMPLE_DESIGN_MD


class TestSlideDeck:
    def test_valid_deck_parses(self, sample_deck_data):
        deck = SlideDeck.model_validate(sample_deck_data)
        assert deck.meta.title == "Test Deck"
        assert len(deck.slides) == 2

    def test_slide_count_mismatch_raises(self, sample_deck_data):
        bad = {**sample_deck_data, "meta": {**sample_deck_data["meta"], "slide_count": 99}}
        with pytest.raises(ValueError, match="slide_count"):
            SlideDeck.model_validate(bad)

    def test_slide_assets_default_none(self, sample_deck_data):
        deck = SlideDeck.model_validate(sample_deck_data)
        assert deck.slides[0].assets.image is None
        assert deck.slides[0].assets.backdrop is None

    def test_slide_transition_default_none(self, sample_deck_data):
        deck = SlideDeck.model_validate(sample_deck_data)
        assert deck.slides[0].transition_to_next is None

    def test_round_trip_file(self, sample_deck_data, tmp_path):
        deck = SlideDeck.model_validate(sample_deck_data)
        p = tmp_path / "slide_deck.json"
        deck.to_file(p)
        loaded = SlideDeck.from_file(p)
        assert loaded.meta.title == "Test Deck"
        assert len(loaded.slides) == 2
        assert loaded.slides[1].title == "Slide Two"

    def test_to_file_creates_parent_dirs(self, sample_deck_data, tmp_path):
        deck = SlideDeck.model_validate(sample_deck_data)
        nested = tmp_path / "deep" / "nested" / "slide_deck.json"
        deck.to_file(nested)
        assert nested.exists()

    def test_from_file_preserves_assets_and_transition(self, tmp_path, sample_deck_data):
        data = {
            **sample_deck_data,
            "meta": {**sample_deck_data["meta"], "slide_count": 1},
            "slides": [{
                **sample_deck_data["slides"][0],
                "assets": {
                    "image": "assets/slide-1-image.png",
                    "backdrop": "assets/slide-1-backdrop.png",
                },
                "transition_to_next": "transitions/slide-1-to-2.mp4",
            }],
        }
        deck = SlideDeck.model_validate(data)
        p = tmp_path / "slide_deck.json"
        deck.to_file(p)
        loaded = SlideDeck.from_file(p)
        assert loaded.slides[0].assets.image == "assets/slide-1-image.png"
        assert loaded.slides[0].assets.backdrop == "assets/slide-1-backdrop.png"
        assert loaded.slides[0].transition_to_next == "transitions/slide-1-to-2.mp4"

    def test_meta_fields_preserved(self, sample_deck_data):
        deck = SlideDeck.model_validate(sample_deck_data)
        assert deck.meta.prompt == "test prompt"
        assert deck.meta.slide_count == 2

    def test_slide_fields_accessible(self, sample_deck_data):
        deck = SlideDeck.model_validate(sample_deck_data)
        s = deck.slides[0]
        assert s.id == 1
        assert s.title == "Slide One"
        assert s.bullets == ["Point A", "Point B"]
        assert "scale" in s.speaker_notes
        assert "developer" in s.image_brief
        assert "gradient" in s.backdrop_brief


class TestDesignTokens:
    def test_parses_name(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.name == "Test Deck"

    def test_parses_primary_color(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.colors.primary == "#0F172A"

    def test_parses_accent_color(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.colors.accent == "#38BDF8"

    def test_parses_surface_color(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.colors.surface == "#1E293B"

    def test_on_surface_alias_resolved(self, sample_design_md):
        """The YAML key 'on-surface' (hyphen) must map to .on_surface (underscore)."""
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.colors.on_surface == "#F1F5F9"

    def test_typography_h1_parsed(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.typography is not None
        h1 = tokens.typography["h1"]
        assert h1.fontFamily == "Inter"
        assert h1.fontSize == "48px"
        assert h1.fontWeight == 700

    def test_typography_body_md_parsed(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.typography is not None
        assert "body-md" in tokens.typography
        assert tokens.typography["body-md"].fontSize == "18px"

    def test_spacing_parsed(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.spacing is not None
        assert tokens.spacing["slide-padding"] == "64px"
        assert tokens.spacing["section-gap"] == "32px"

    def test_missing_frontmatter_raises(self, tmp_path):
        p = tmp_path / "DESIGN.md"
        p.write_text("## No frontmatter fence here\n", encoding="utf-8")
        with pytest.raises(ValueError, match="---"):
            DesignTokens.from_design_md(p)

    def test_unclosed_frontmatter_raises(self, tmp_path):
        p = tmp_path / "DESIGN.md"
        p.write_text("---\nname: Foo\n## Oops no closing fence\n", encoding="utf-8")
        with pytest.raises(ValueError, match="closed"):
            DesignTokens.from_design_md(p)


class TestExtractFrontmatter:
    def test_extracts_content_between_fences(self):
        text = "---\nname: Foo\ncolors:\n  primary: '#000'\n---\n## Body\n"
        result = _extract_frontmatter(text)
        assert "name: Foo" in result
        assert "## Body" not in result

    def test_does_not_include_fence_lines(self):
        text = "---\nname: Bar\n---\n"
        result = _extract_frontmatter(text)
        assert "---" not in result

    def test_multiline_frontmatter(self):
        text = "---\na: 1\nb: 2\nc: 3\n---\nbody\n"
        result = _extract_frontmatter(text)
        assert result == "a: 1\nb: 2\nc: 3"
```

- [ ] Run tests — all must fail (schema.py does not exist yet):

```bash
pytest tests/test_schema.py -v
# Expected: ModuleNotFoundError: No module named 'director_deck.schema'
```

### Implementation

Create `director_deck/schema.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# SlideDeck schema — content contract shared by all agents
# ---------------------------------------------------------------------------

class SlideAssets(BaseModel):
    """Paths to generated image assets for a slide (relative to run_dir)."""
    image: Optional[str] = None
    backdrop: Optional[str] = None


class Slide(BaseModel):
    id: int
    title: str
    bullets: list[str]
    speaker_notes: str
    image_brief: str
    backdrop_brief: str
    assets: SlideAssets = SlideAssets()
    transition_to_next: Optional[str] = None


class DeckMeta(BaseModel):
    title: str
    prompt: str
    slide_count: int


class SlideDeck(BaseModel):
    meta: DeckMeta
    slides: list[Slide]

    @model_validator(mode="after")
    def _validate_slide_count(self) -> "SlideDeck":
        if len(self.slides) != self.meta.slide_count:
            raise ValueError(
                f"slide_count={self.meta.slide_count} but {len(self.slides)} slides present"
            )
        return self

    @classmethod
    def from_file(cls, path: Path) -> "SlideDeck":
        """Load and validate a SlideDeck from a JSON file."""
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def to_file(self, path: Path) -> None:
        """Serialise to indented JSON and write to path; creates parent dirs."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# DesignTokens schema — visual identity parsed from DESIGN.md frontmatter
# ---------------------------------------------------------------------------

class DesignColors(BaseModel):
    """Color tokens from DESIGN.md. The YAML key 'on-surface' maps to on_surface."""
    model_config = ConfigDict(populate_by_name=True)

    primary: str
    accent: Optional[str] = None
    surface: Optional[str] = None
    on_surface: Optional[str] = Field(None, alias="on-surface")


class DesignTypographyEntry(BaseModel):
    fontFamily: str
    fontSize: str
    fontWeight: int


class DesignTokens(BaseModel):
    name: str
    colors: DesignColors
    typography: Optional[dict[str, DesignTypographyEntry]] = None
    spacing: Optional[dict[str, str]] = None

    @classmethod
    def from_design_md(cls, path: Path) -> "DesignTokens":
        """Parse DESIGN.md and return DesignTokens from its YAML frontmatter."""
        text = path.read_text(encoding="utf-8")
        frontmatter = _extract_frontmatter(text)
        data = yaml.safe_load(frontmatter)
        return cls.model_validate(data)


def _extract_frontmatter(text: str) -> str:
    """
    Extract YAML content between the first pair of '---' fences.

    Raises:
        ValueError: If the file does not start with '---', or the closing fence is missing.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("DESIGN.md does not start with a --- frontmatter fence")
    try:
        end = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        raise ValueError("DESIGN.md frontmatter is not closed with a --- fence")
    return "\n".join(lines[1:end])
```

- [ ] Run tests — all must pass:

```bash
pytest tests/test_schema.py -v
# Expected: 20 passed
```

- [ ] Commit:

```bash
git add director_deck/schema.py tests/conftest.py tests/test_schema.py
git commit -m "feat: add schema.py — SlideDeck and DesignTokens Pydantic v2 models"
```

---

## Task 3 — HTML Renderer

**Goal:** Convert `SlideDeck` + `DesignTokens` into a single HTML document. Each slide is a `960×540px` `<div id="slide-N">`. Two modes: **wireframe** (placeholder divs for image areas) and **enriched** (`<img>` tags when assets are populated).

### TDD — Write tests first

Create `tests/test_html_renderer.py`:

```python
import pytest
from pathlib import Path
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.html_renderer import tokens_to_css_vars, render_deck_html, write_deck_html


@pytest.fixture
def tokens(sample_design_md):
    return DesignTokens.from_design_md(sample_design_md)


@pytest.fixture
def deck(sample_deck_data):
    return SlideDeck.model_validate(sample_deck_data)


@pytest.fixture
def enriched_deck(sample_deck_data):
    """A one-slide deck with fully populated assets."""
    data = {
        **sample_deck_data,
        "meta": {**sample_deck_data["meta"], "slide_count": 1},
        "slides": [{
            **sample_deck_data["slides"][0],
            "assets": {
                "image": "assets/slide-1-image.png",
                "backdrop": "assets/slide-1-backdrop.png",
            },
        }],
    }
    return SlideDeck.model_validate(data)


class TestTokensToCssVars:
    def test_primary_color_present(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--color-primary: #0F172A;" in css

    def test_accent_color_present(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--color-accent: #38BDF8;" in css

    def test_on_surface_color_present(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--color-on-surface: #F1F5F9;" in css

    def test_h1_family_var(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--font-h1-family: Inter;" in css

    def test_h1_size_var(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--font-h1-size: 48px;" in css

    def test_h1_weight_var(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--font-h1-weight: 700;" in css

    def test_body_md_vars_present(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--font-body-md-family: Inter;" in css
        assert "--font-body-md-size: 18px;" in css

    def test_spacing_slide_padding(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--spacing-slide-padding: 64px;" in css

    def test_spacing_section_gap(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--spacing-section-gap: 32px;" in css

    def test_wrapped_in_root_block(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert css.startswith(":root {")
        assert css.strip().endswith("}")


class TestRenderDeckHtml:
    def test_all_slide_divs_present(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert 'id="slide-1"' in html
        assert 'id="slide-2"' in html

    def test_wireframe_mode_has_placeholder_class(self, deck, tokens):
        html = render_deck_html(deck, tokens, enriched=False)
        assert 'class="image-placeholder"' in html

    def test_wireframe_mode_has_no_img_tags(self, deck, tokens):
        html = render_deck_html(deck, tokens, enriched=False)
        assert "<img " not in html

    def test_wireframe_image_brief_in_placeholder(self, deck, tokens):
        html = render_deck_html(deck, tokens, enriched=False)
        assert "A lone developer staring at a wall of error logs" in html

    def test_enriched_no_assets_still_shows_placeholder(self, deck, tokens):
        """Enriched mode with no assets set should still fall back to placeholder."""
        html = render_deck_html(deck, tokens, enriched=True)
        assert 'class="image-placeholder"' in html

    def test_enriched_with_assets_shows_img_tag(self, enriched_deck, tokens):
        html = render_deck_html(enriched_deck, tokens, enriched=True)
        assert "<img " in html
        assert "assets/slide-1-image.png" in html

    def test_enriched_with_backdrop_has_background_image_style(self, enriched_deck, tokens):
        html = render_deck_html(enriched_deck, tokens, enriched=True)
        assert "background-image" in html
        assert "assets/slide-1-backdrop.png" in html

    def test_slide_titles_in_output(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert "Slide One" in html
        assert "Slide Two" in html

    def test_bullet_text_in_output(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert "Point A" in html
        assert "Point B" in html
        assert "Point C" in html

    def test_css_vars_injected_in_style_block(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert "--color-primary" in html

    def test_html_doctype_present(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert html.startswith("<!DOCTYPE html>")

    def test_slide_class_present(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert 'class="slide"' in html


class TestWriteDeckHtml:
    def test_writes_file_to_disk(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.html"
        result = write_deck_html(deck, tokens, out)
        assert result == out
        assert out.exists()

    def test_creates_parent_dirs(self, deck, tokens, tmp_path):
        out = tmp_path / "nested" / "output" / "deck.html"
        write_deck_html(deck, tokens, out)
        assert out.exists()

    def test_file_content_matches_render(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.html"
        write_deck_html(deck, tokens, out)
        written = out.read_text(encoding="utf-8")
        expected = render_deck_html(deck, tokens)
        assert written == expected

    def test_enriched_flag_passes_through(self, enriched_deck, tokens, tmp_path):
        out = tmp_path / "deck_enriched.html"
        write_deck_html(enriched_deck, tokens, out, enriched=True)
        content = out.read_text()
        assert "<img " in content
```

- [ ] Run tests — all must fail:

```bash
pytest tests/test_html_renderer.py -v
# Expected: ModuleNotFoundError: No module named 'director_deck.html_renderer'
```

### Implementation

Create `director_deck/html_renderer.py`:

```python
from __future__ import annotations

from pathlib import Path

from director_deck.schema import DesignTokens, Slide, SlideDeck


# ---------------------------------------------------------------------------
# Design token → CSS custom property conversion
# ---------------------------------------------------------------------------

def tokens_to_css_vars(tokens: DesignTokens) -> str:
    """
    Return a CSS ``:root { ... }`` block populated from DesignTokens.

    Typography keys use hyphens in CSS vars (e.g. ``--font-body-md-size``),
    matching the YAML key names directly.
    """
    lines: list[str] = [":root {"]

    c = tokens.colors
    lines.append(f"  --color-primary: {c.primary};")
    if c.accent:
        lines.append(f"  --color-accent: {c.accent};")
    if c.surface:
        lines.append(f"  --color-surface: {c.surface};")
    if c.on_surface:
        lines.append(f"  --color-on-surface: {c.on_surface};")

    if tokens.typography:
        for role, entry in tokens.typography.items():
            # role is e.g. "h1", "body-md" — keep hyphens in var names
            lines.append(f"  --font-{role}-family: {entry.fontFamily};")
            lines.append(f"  --font-{role}-size: {entry.fontSize};")
            lines.append(f"  --font-{role}-weight: {entry.fontWeight};")

    if tokens.spacing:
        for key, value in tokens.spacing.items():
            lines.append(f"  --spacing-{key}: {value};")

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-slide div rendering
# ---------------------------------------------------------------------------

_SLIDE_BASE_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #111; font-family: sans-serif; }
.slide {
  width: 960px;
  height: 540px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin: 0 auto 4px;
  background: var(--color-primary, #0F172A);
}
.slide-content {
  padding: var(--spacing-slide-padding, 48px);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.slide-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: var(--font-h1-size, 36px);
  font-weight: var(--font-h1-weight, 700);
  color: var(--color-accent, #38BDF8);
  margin-bottom: 24px;
  flex-shrink: 0;
}
.slide-body {
  display: flex;
  flex: 1;
  gap: 24px;
  overflow: hidden;
}
.slide-text { flex: 55; }
.slide-image-area {
  flex: 40;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bullets { list-style: none; }
.bullet {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: var(--font-body-md-size, 16px);
  font-weight: var(--font-body-md-weight, 400);
  color: var(--color-on-surface, #F1F5F9);
  margin-bottom: 12px;
  padding-left: 20px;
  position: relative;
}
.bullet::before {
  content: '\u2192';
  position: absolute;
  left: 0;
  color: var(--color-accent, #38BDF8);
}
.image-placeholder {
  width: 100%;
  min-height: 180px;
  background: var(--color-surface, #1E293B);
  border: 2px dashed var(--color-accent, #38BDF8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-on-surface, #F1F5F9);
  font-size: 13px;
  text-align: center;
  padding: 12px;
  border-radius: 4px;
}
.slide-image {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 4px;
}"""


def _render_slide_div(slide: Slide, *, enriched: bool = False) -> str:
    """Render a single slide as a 960×540 <div id="slide-N">."""
    bullets_html = "\n".join(
        f'          <li class="bullet">{b}</li>' for b in slide.bullets
    )

    # Backdrop: inline background-image style when enriched and asset present
    if enriched and slide.assets.backdrop:
        bg_style = (
            f' style="background-image: url(\'{slide.assets.backdrop}\'); '
            f'background-size: cover; background-position: center;"'
        )
    else:
        bg_style = ""

    # Image area: real <img> when enriched + asset present, otherwise placeholder
    if enriched and slide.assets.image:
        image_html = (
            f'<img class="slide-image" src="{slide.assets.image}" '
            f'alt="{slide.image_brief}" />'
        )
    else:
        image_html = f'<div class="image-placeholder">{slide.image_brief}</div>'

    return f"""\
<div class="slide" id="slide-{slide.id}"{bg_style}>
  <div class="slide-content">
    <h1 class="slide-title">{slide.title}</h1>
    <div class="slide-body">
      <div class="slide-text">
        <ul class="bullets">
{bullets_html}
        </ul>
      </div>
      <div class="slide-image-area">
        {image_html}
      </div>
    </div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Full HTML document
# ---------------------------------------------------------------------------

def render_deck_html(
    deck: SlideDeck,
    tokens: DesignTokens,
    *,
    enriched: bool = False,
) -> str:
    """
    Render all slides as a single HTML document (960px wide, one div per slide).

    Args:
        deck: Validated SlideDeck to render.
        tokens: Design tokens parsed from DESIGN.md.
        enriched: False = placeholder image areas; True = real <img> tags where assets set.

    Returns:
        Complete HTML document string.
    """
    css_vars = tokens_to_css_vars(tokens)
    slides_html = "\n".join(
        _render_slide_div(s, enriched=enriched) for s in deck.slides
    )
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=960">
  <title>{deck.meta.title}</title>
  <style>
{css_vars}
{_SLIDE_BASE_CSS}
  </style>
</head>
<body>
{slides_html}
</body>
</html>"""


def write_deck_html(
    deck: SlideDeck,
    tokens: DesignTokens,
    output_path: Path,
    *,
    enriched: bool = False,
) -> Path:
    """Write rendered HTML to disk. Creates parent directories as needed. Returns output_path."""
    html = render_deck_html(deck, tokens, enriched=enriched)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
```

- [ ] Run tests — all must pass:

```bash
pytest tests/test_html_renderer.py -v
# Expected: 24 passed
```

- [ ] Commit:

```bash
git add director_deck/html_renderer.py tests/test_html_renderer.py
git commit -m "feat: add html_renderer.py — DESIGN.md tokens to 960x540 slide HTML"
```

---

## Task 4 — PPTX Builder

**Goal:** Build a `.pptx` from a `SlideDeck` using python-pptx. Two modes: wireframe (gray placeholder rectangle) and enriched (embedded image if asset file exists). Slide size: 13.33×7.5 inches (16:9 widescreen).

### TDD — Write tests first

Create `tests/test_pptx_builder.py`:

```python
import pytest
from pathlib import Path
from pptx import Presentation
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.pptx_builder import build_pptx, SLIDE_WIDTH_IN, SLIDE_HEIGHT_IN

# 1 EMU = 1/914400 inch
_EMU_PER_INCH = 914400


@pytest.fixture
def tokens(sample_design_md):
    return DesignTokens.from_design_md(sample_design_md)


@pytest.fixture
def deck(sample_deck_data):
    return SlideDeck.model_validate(sample_deck_data)


@pytest.fixture
def minimal_png(tmp_path) -> Path:
    """A valid 1×1 white PNG (smallest possible valid PNG)."""
    png_bytes = (
        b'\x89PNG\r\n\x1a\n'                        # PNG signature
        b'\x00\x00\x00\rIHDR'                       # IHDR chunk length=13
        b'\x00\x00\x00\x01\x00\x00\x00\x01'        # width=1, height=1
        b'\x08\x02\x00\x00\x00'                     # bit depth=8, color=RGB, ...
        b'\x90wS\xde'                               # IHDR CRC
        b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    p = tmp_path / "tiny.png"
    p.write_bytes(png_bytes)
    return p


class TestBuildPptx:
    def test_creates_file_at_output_path(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        result = build_pptx(deck, tokens, out)
        assert result == out
        assert out.exists()

    def test_creates_parent_dirs(self, deck, tokens, tmp_path):
        out = tmp_path / "nested" / "deck.pptx"
        build_pptx(deck, tokens, out)
        assert out.exists()

    def test_slide_count_matches_deck(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        build_pptx(deck, tokens, out)
        prs = Presentation(str(out))
        assert len(prs.slides) == deck.meta.slide_count

    def test_slide_width_is_16_9(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        build_pptx(deck, tokens, out)
        prs = Presentation(str(out))
        actual_in = float(prs.slide_width) / _EMU_PER_INCH
        assert abs(actual_in - SLIDE_WIDTH_IN) < 0.02

    def test_slide_height_is_7_5_inches(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        build_pptx(deck, tokens, out)
        prs = Presentation(str(out))
        actual_in = float(prs.slide_height) / _EMU_PER_INCH
        assert abs(actual_in - SLIDE_HEIGHT_IN) < 0.02

    def test_each_slide_has_at_least_two_shapes(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        build_pptx(deck, tokens, out)
        prs = Presentation(str(out))
        for slide in prs.slides:
            assert len(slide.shapes) >= 2, "Every slide needs at least title + body shapes"

    def test_title_text_appears_in_slide_one(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.pptx"
        build_pptx(deck, tokens, out)
        prs = Presentation(str(out))
        first_slide = prs.slides[0]
        all_text = " ".join(
            shape.text_frame.text
            for shape in first_slide.shapes
            if shape.has_text_frame
        )
        assert "Slide One" in all_text

    def test_wireframe_mode_does_not_crash(self, deck, tokens, tmp_path):
        out = tmp_path / "wireframe.pptx"
        build_pptx(deck, tokens, out, enriched=False)
        assert out.exists()

    def test_enriched_mode_with_image_file(self, tokens, tmp_path, minimal_png, sample_deck_data):
        data = {
            **sample_deck_data,
            "meta": {**sample_deck_data["meta"], "slide_count": 1},
            "slides": [{
                **sample_deck_data["slides"][0],
                "assets": {"image": str(minimal_png), "backdrop": None},
            }],
        }
        enriched_deck = SlideDeck.model_validate(data)
        out = tmp_path / "enriched.pptx"
        build_pptx(enriched_deck, tokens, out, enriched=True)
        assert out.exists()
        prs = Presentation(str(out))
        assert len(prs.slides) == 1

    def test_enriched_mode_missing_asset_falls_back_to_placeholder(
        self, deck, tokens, tmp_path
    ):
        """When enriched=True but asset path doesn't exist, should not crash."""
        out = tmp_path / "enriched.pptx"
        build_pptx(deck, tokens, out, enriched=True)
        assert out.exists()
```

- [ ] Run tests — all must fail:

```bash
pytest tests/test_pptx_builder.py -v
# Expected: ModuleNotFoundError: No module named 'director_deck.pptx_builder'
```

### Implementation

Create `director_deck/pptx_builder.py`:

```python
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from director_deck.schema import DesignTokens, Slide, SlideDeck

# Slide dimensions: 13.33 × 7.5 inches (standard PowerPoint 16:9 widescreen)
SLIDE_WIDTH_IN: float = 13.33
SLIDE_HEIGHT_IN: float = 7.5


def _hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert a #RRGGBB hex string to python-pptx RGBColor."""
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _add_slide(
    prs: Presentation,
    slide: Slide,
    tokens: DesignTokens,
    *,
    enriched: bool = False,
) -> None:
    """Add one populated slide to the Presentation."""
    blank_layout = prs.slide_layouts[6]  # index 6 = blank layout
    sl = prs.slides.add_slide(blank_layout)

    primary_rgb = _hex_to_rgb(tokens.colors.primary)
    accent_rgb = _hex_to_rgb(tokens.colors.accent or "#38BDF8")
    on_surface_rgb = _hex_to_rgb(tokens.colors.on_surface or "#F1F5F9")
    surface_rgb = _hex_to_rgb(tokens.colors.surface or "#1E293B")

    # ── Background fill ──────────────────────────────────────────────────────
    bg_fill = sl.background.fill
    bg_fill.solid()
    bg_fill.fore_color.rgb = primary_rgb

    # ── Title text box — top strip, full width ───────────────────────────────
    title_box = sl.shapes.add_textbox(
        Inches(0.5),
        Inches(0.3),
        Inches(SLIDE_WIDTH_IN - 1.0),
        Inches(1.2),
    )
    tf = title_box.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    para.text = slide.title
    para.alignment = PP_ALIGN.LEFT
    run = para.runs[0]
    run.font.size = Pt(36)
    run.font.bold = True
    run.font.color.rgb = accent_rgb

    # ── Bullet text box — left 55% of slide, below title ────────────────────
    body_box = sl.shapes.add_textbox(
        Inches(0.5),
        Inches(1.7),
        Inches(SLIDE_WIDTH_IN * 0.55 - 0.5),
        Inches(SLIDE_HEIGHT_IN - 2.3),
    )
    tf_body = body_box.text_frame
    tf_body.word_wrap = True
    for i, bullet in enumerate(slide.bullets):
        para = tf_body.paragraphs[0] if i == 0 else tf_body.add_paragraph()
        para.text = f"\u2192 {bullet}"
        para.space_before = Pt(6)
        run = para.runs[0]
        run.font.size = Pt(16)
        run.font.color.rgb = on_surface_rgb

    # ── Image area — right ~40% of slide ────────────────────────────────────
    img_left = Inches(SLIDE_WIDTH_IN * 0.58)
    img_top = Inches(1.7)
    img_width = Inches(SLIDE_WIDTH_IN * 0.38)
    img_height = Inches(SLIDE_HEIGHT_IN - 2.5)

    if enriched and slide.assets.image:
        img_path = Path(slide.assets.image)
        if img_path.exists():
            sl.shapes.add_picture(str(img_path), img_left, img_top, img_width, img_height)
            return  # real picture added; skip placeholder

    # Placeholder rectangle (wireframe mode or asset file missing)
    ph = sl.shapes.add_shape(1, img_left, img_top, img_width, img_height)
    ph.fill.solid()
    ph.fill.fore_color.rgb = surface_rgb
    ph.line.color.rgb = accent_rgb
    tf_ph = ph.text_frame
    tf_ph.word_wrap = True
    para_ph = tf_ph.paragraphs[0]
    para_ph.text = slide.image_brief
    para_ph.alignment = PP_ALIGN.CENTER
    run_ph = para_ph.runs[0]
    run_ph.font.size = Pt(11)
    run_ph.font.color.rgb = on_surface_rgb


def build_pptx(
    deck: SlideDeck,
    tokens: DesignTokens,
    output_path: Path,
    *,
    enriched: bool = False,
) -> Path:
    """
    Build a PPTX from a SlideDeck.

    Args:
        deck: Validated SlideDeck.
        tokens: Design tokens parsed from DESIGN.md.
        output_path: Destination for the .pptx file.
        enriched: False = placeholder image areas. True = embed real images where available.

    Returns:
        The path the file was written to.
    """
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_IN)
    prs.slide_height = Inches(SLIDE_HEIGHT_IN)

    for slide in deck.slides:
        _add_slide(prs, slide, tokens, enriched=enriched)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return output_path
```

- [ ] Run tests — all must pass:

```bash
pytest tests/test_pptx_builder.py -v
# Expected: 10 passed
```

- [ ] Commit:

```bash
git add director_deck/pptx_builder.py tests/test_pptx_builder.py
git commit -m "feat: add pptx_builder.py — SlideDeck to python-pptx 16:9 PPTX"
```

---

## Task 5 — Screenshot Tool

**Goal:** Use Playwright headless Chromium to screenshot each `960×540` slide div from the rendered HTML file. Returns one PNG per slide. These are the keyframe inputs for Veo 3.1 interpolation.

Tests are marked `@pytest.mark.integration` — they require `playwright install chromium`.

### TDD — Write tests first

Create `tests/test_screenshot_tool.py`:

```python
import pytest
from pathlib import Path
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.html_renderer import write_deck_html
from director_deck.screenshot_tool import screenshot_deck


@pytest.fixture
def tokens(sample_design_md):
    return DesignTokens.from_design_md(sample_design_md)


@pytest.fixture
def deck(sample_deck_data):
    return SlideDeck.model_validate(sample_deck_data)


@pytest.fixture
def html_file(deck, tokens, tmp_path) -> tuple[Path, SlideDeck]:
    """Write the wireframe deck HTML and return (path, deck)."""
    out = tmp_path / "deck.html"
    write_deck_html(deck, tokens, out)
    return out, deck


@pytest.mark.integration
class TestScreenshotDeck:
    def test_returns_list_of_paths(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        assert isinstance(paths, list)
        assert len(paths) == deck.meta.slide_count

    def test_png_files_exist_on_disk(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        for p in paths:
            assert p.exists(), f"Expected PNG at {p}"
            assert p.suffix == ".png"

    def test_files_named_slide_n_png(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        for i, p in enumerate(paths, start=1):
            assert p.name == f"slide-{i}.png"

    def test_creates_output_dir_if_missing(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "new" / "deep" / "keyframes"
        assert not out_dir.exists()
        screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        assert out_dir.exists()

    def test_raises_runtime_error_on_missing_slide_element(self, tmp_path):
        bad_html = tmp_path / "bad.html"
        bad_html.write_text(
            "<html><body><p>No slide divs here</p></body></html>",
            encoding="utf-8",
        )
        out_dir = tmp_path / "keyframes"
        with pytest.raises(RuntimeError, match="slide-1"):
            screenshot_deck(bad_html, out_dir, slide_count=1)

    def test_returns_paths_in_slide_order(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        for i, p in enumerate(paths, start=1):
            assert p.stem == f"slide-{i}"
```

- [ ] Run tests — all must fail:

```bash
pytest tests/test_screenshot_tool.py -m integration -v
# Expected: ModuleNotFoundError: No module named 'director_deck.screenshot_tool'
```

### Implementation

Create `director_deck/screenshot_tool.py`:

```python
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
```

- [ ] Run integration tests — all must pass:

```bash
pytest tests/test_screenshot_tool.py -m integration -v
# Expected: 6 passed
```

- [ ] Commit:

```bash
git add director_deck/screenshot_tool.py tests/test_screenshot_tool.py
git commit -m "feat: add screenshot_tool.py — Playwright HTML-to-PNG keyframe capture"
```

---

## Task 6 — PPTX Stitcher

**Goal:** Embed MP4 clips as native PowerPoint slide transitions. Opens the PPTX as a zip, copies MP4 bytes into `ppt/media/`, injects a `<Relationship>` entry into each slide's `.rels` file, and inserts `<p:transition>` XML into each slide XML. Compatible with Office 2013+.

### TDD — Write tests first

Create `tests/test_pptx_stitcher.py`:

```python
import zipfile
import pytest
from pathlib import Path
from pptx import Presentation
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.pptx_builder import build_pptx
from director_deck.pptx_stitcher import (
    embed_transitions,
    _add_video_relationship,
    _inject_transition,
    REL_TYPE_VIDEO,
)


@pytest.fixture
def tokens(sample_design_md):
    return DesignTokens.from_design_md(sample_design_md)


@pytest.fixture
def deck(sample_deck_data):
    return SlideDeck.model_validate(sample_deck_data)


@pytest.fixture
def wireframe_pptx(deck, tokens, tmp_path) -> Path:
    out = tmp_path / "wireframe.pptx"
    build_pptx(deck, tokens, out)
    return out


@pytest.fixture
def fake_mp4(tmp_path) -> Path:
    """Minimal file standing in for an MP4 (content doesn't need to be valid video)."""
    p = tmp_path / "trans.mp4"
    p.write_bytes(b"FAKEVIDEO12345")
    return p


class TestHelperFunctions:
    def test_add_video_relationship_injects_rel_id(self):
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '</Relationships>'
        )
        result = _add_video_relationship(rels_xml, "rVid1", "../media/trans1.mp4")
        assert 'Id="rVid1"' in result

    def test_add_video_relationship_includes_rel_type(self):
        rels_xml = '<Relationships xmlns="...">\n</Relationships>'
        result = _add_video_relationship(rels_xml, "rVid1", "../media/trans1.mp4")
        assert REL_TYPE_VIDEO in result

    def test_add_video_relationship_includes_target(self):
        rels_xml = '<Relationships xmlns="...">\n</Relationships>'
        result = _add_video_relationship(rels_xml, "rVid1", "../media/trans1.mp4")
        assert 'Target="../media/trans1.mp4"' in result

    def test_add_video_relationship_preserves_existing_entries(self):
        rels_xml = (
            '<Relationships xmlns="...">\n'
            '  <Relationship Id="rId1" Type="slide" Target="slide1.xml"/>\n'
            '</Relationships>'
        )
        result = _add_video_relationship(rels_xml, "rVid1", "../media/trans1.mp4")
        assert 'Id="rId1"' in result
        assert 'Id="rVid1"' in result

    def test_inject_transition_adds_ptransition_element(self):
        slide_xml = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            'content'
            '</p:sld>'
        )
        result = _inject_transition(slide_xml, "rVid1")
        assert "<p:transition" in result

    def test_inject_transition_includes_rel_id(self):
        slide_xml = '<p:sld xmlns:p="...">content</p:sld>'
        result = _inject_transition(slide_xml, "rVid1")
        assert "rVid1" in result

    def test_inject_transition_placed_before_closing_tag(self):
        slide_xml = '<p:sld xmlns:p="...">content</p:sld>'
        result = _inject_transition(slide_xml, "rVid1")
        transition_pos = result.index("<p:transition")
        closing_pos = result.index("</p:sld>")
        assert transition_pos < closing_pos


class TestEmbedTransitions:
    def test_creates_output_file(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        result = embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        assert result == out
        assert out.exists()

    def test_mp4_added_to_ppt_media(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        with zipfile.ZipFile(out, "r") as zf:
            assert "ppt/media/trans1.mp4" in zf.namelist()

    def test_mp4_bytes_intact(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        with zipfile.ZipFile(out, "r") as zf:
            data = zf.read("ppt/media/trans1.mp4")
        assert data == b"FAKEVIDEO12345"

    def test_slide_rels_has_video_relationship(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        with zipfile.ZipFile(out, "r") as zf:
            rels_xml = zf.read("ppt/slides/_rels/slide1.xml.rels").decode()
        assert "rVid1" in rels_xml
        assert REL_TYPE_VIDEO in rels_xml

    def test_slide_xml_has_ptransition(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        with zipfile.ZipFile(out, "r") as zf:
            slide_xml = zf.read("ppt/slides/slide1.xml").decode()
        assert "<p:transition" in slide_xml

    def test_source_pptx_not_modified(self, wireframe_pptx, fake_mp4, tmp_path):
        original_size = wireframe_pptx.stat().st_size
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        assert wireframe_pptx.stat().st_size == original_size

    def test_multiple_transitions_all_added(self, wireframe_pptx, tmp_path):
        mp4_a = tmp_path / "t1.mp4"
        mp4_b = tmp_path / "t2.mp4"
        mp4_a.write_bytes(b"VIDEO1")
        mp4_b.write_bytes(b"VIDEO2")
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, mp4_a), (2, mp4_b)], out)
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        assert "ppt/media/trans1.mp4" in names
        assert "ppt/media/trans2.mp4" in names

    def test_empty_transitions_list_produces_valid_pptx(self, wireframe_pptx, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [], out)
        prs = Presentation(str(out))
        assert len(prs.slides) == 2  # unmodified slide count
```

- [ ] Run tests — all must fail:

```bash
pytest tests/test_pptx_stitcher.py -v
# Expected: ModuleNotFoundError: No module named 'director_deck.pptx_stitcher'
```

### Implementation

Create `director_deck/pptx_stitcher.py`:

```python
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

# Office Open XML relationship type for embedded video
REL_TYPE_VIDEO = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"
)

# Transition XML template — namespace declarations are included for safety since
# we are injecting via text replacement, not proper XML DOM manipulation.
_TRANSITION_TEMPLATE = (
    '  <p:transition'
    ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' advTm="0" spd="med">'
    '<p:video r:id="{rel_id}"/>'
    '</p:transition>'
)


def _add_video_relationship(rels_xml: str, rel_id: str, media_target: str) -> str:
    """
    Inject a video Relationship element into slide rels XML.

    Args:
        rels_xml: Content of the slide's ``.rels`` XML file as a string.
        rel_id: The rId string (e.g. ``"rVid1"``) for this relationship.
        media_target: Relative path to the media file (e.g. ``"../media/trans1.mp4"``).

    Returns:
        Updated rels XML string with the new Relationship injected before ``</Relationships>``.
    """
    new_rel = (
        f'  <Relationship Id="{rel_id}" '
        f'Type="{REL_TYPE_VIDEO}" '
        f'Target="{media_target}"/>\n'
    )
    return rels_xml.replace("</Relationships>", new_rel + "</Relationships>")


def _inject_transition(slide_xml: str, rel_id: str) -> str:
    """
    Inject a ``<p:transition>`` element into slide XML before the closing ``</p:sld>`` tag.

    Args:
        slide_xml: Content of the slide's ``.xml`` file as a string.
        rel_id: The relationship ID referencing the MP4 (e.g. ``"rVid1"``).

    Returns:
        Updated slide XML string with ``<p:transition>`` injected.
    """
    transition = _TRANSITION_TEMPLATE.format(rel_id=rel_id)
    return slide_xml.replace("</p:sld>", transition + "\n</p:sld>")


def embed_transitions(
    source_pptx: Path,
    transitions: list[tuple[int, Path]],
    output_path: Path,
) -> Path:
    """
    Embed MP4 transition clips into a PPTX file as native slide transitions.

    Each ``(slide_index, mp4_path)`` in ``transitions`` embeds the MP4 as the
    transition that plays when the user advances past that slide (1-based index).

    The source PPTX is never modified — all work is done on a copy.

    Args:
        source_pptx: Path to the existing ``.pptx`` to augment.
        transitions: List of (1-based slide index, Path to .mp4) tuples.
        output_path: Destination path for the stitched ``.pptx``.

    Returns:
        The path the stitched file was written to.
    """
    shutil.copy2(source_pptx, output_path)

    # Load entire zip into memory (PPTX files are small enough)
    with zipfile.ZipFile(output_path, "r") as zin:
        contents: dict[str, bytes] = {name: zin.read(name) for name in zin.namelist()}

    for slide_1based, mp4_path in transitions:
        media_name = f"trans{slide_1based}.mp4"
        rel_id = f"rVid{slide_1based}"

        # 1. Add MP4 bytes to the virtual zip archive
        contents[f"ppt/media/{media_name}"] = mp4_path.read_bytes()

        # 2. Inject video relationship into slide .rels file
        rels_key = f"ppt/slides/_rels/slide{slide_1based}.xml.rels"
        rels_xml = contents.get(rels_key, b"").decode("utf-8")
        if not rels_xml:
            rels_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/'
                'package/2006/relationships">\n'
                '</Relationships>'
            )
        rels_xml = _add_video_relationship(rels_xml, rel_id, f"../media/{media_name}")
        contents[rels_key] = rels_xml.encode("utf-8")

        # 3. Inject <p:transition> into slide XML
        slide_key = f"ppt/slides/slide{slide_1based}.xml"
        if slide_key in contents:
            slide_xml = contents[slide_key].decode("utf-8")
            slide_xml = _inject_transition(slide_xml, rel_id)
            contents[slide_key] = slide_xml.encode("utf-8")

    # Rewrite zip with all modifications applied
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in contents.items():
            zout.writestr(name, data)

    return output_path
```

- [ ] Run tests — all must pass:

```bash
pytest tests/test_pptx_stitcher.py -v
# Expected: 15 passed
```

- [ ] Commit:

```bash
git add director_deck/pptx_stitcher.py tests/test_pptx_stitcher.py
git commit -m "feat: add pptx_stitcher.py — embed MP4 transitions into PPTX zip"
```

---

## Task 7 — Ghost Deck Writer Agent

**Goal:** Agent markdown that instructs Amplifier to produce `slide_deck.json` + `DESIGN.md` from the user's prompt. Called at Stage 1 and optionally re-run if Gate 1 carries revision instructions.

### Steps

- [ ] Create `agents/ghost-deck-writer.md`:

```markdown
---
meta:
  name: ghost-deck-writer
  description: "Generates slide_deck.json and DESIGN.md from a user prompt"
  version: "0.1.0"
tools:
  - write_file
  - read_file
---

You are the Ghost Deck Writer for Director Deck. From a user's prompt you produce two files
that drive the entire pipeline:

1. **`{run_dir}/slide_deck.json`** — structured slide content
2. **`{run_dir}/DESIGN.md`** — visual identity in Google Stitch DESIGN.md format

## Context variables (injected by recipe)

| Variable | Description |
|---|---|
| `run_dir` | Absolute path to this run's working directory |
| `prompt` | User's original prompt describing the deck |
| `revision_instructions` | Optional string from Gate 1 approval message; empty string if first run |

## Output 1: slide_deck.json

Write a valid JSON file matching this schema exactly:

```json
{
  "meta": {
    "title": "<concise deck title derived from prompt>",
    "prompt": "<original prompt verbatim>",
    "slide_count": <N>
  },
  "slides": [
    {
      "id": 1,
      "title": "<slide title>",
      "bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"],
      "speaker_notes": "<1–3 sentences for the presenter>",
      "image_brief": "<vivid 1-sentence description of the content image>",
      "backdrop_brief": "<description of the background image/texture/gradient, no text, no people>",
      "assets": { "image": null, "backdrop": null },
      "transition_to_next": null
    }
  ]
}
```

**Rules:**
- Generate **8–12 slides** unless the prompt specifies a number
- `slide_count` in `meta` MUST equal the length of the `slides` array
- Bullets: 2–4 per slide, each under 12 words, no punctuation at end
- `image_brief`: specific, visually concrete, one sentence (e.g. "A lone developer staring at a wall of error logs, cinematic lighting")
- `backdrop_brief`: specifies texture/gradient/mood only — no text, no faces, no logos
- `assets` and `transition_to_next` are always `null` / `{ "image": null, "backdrop": null }` from this agent

## Output 2: DESIGN.md

Use the Google Stitch DESIGN.md spec format. The file MUST begin with a YAML frontmatter block.

**Required frontmatter keys:**

```yaml
---
name: <deck title>
colors:
  primary: "<hex>"          # slide background
  accent: "<hex>"           # headlines and callouts
  surface: "<hex>"          # card/panel backgrounds
  on-surface: "<hex>"       # body text (NOTE: hyphen, not underscore)
typography:
  h1:
    fontFamily: <font name>
    fontSize: <e.g. 48px>
    fontWeight: <e.g. 700>
  body-md:
    fontFamily: <font name>
    fontSize: <e.g. 18px>
    fontWeight: <e.g. 400>
spacing:
  slide-padding: <e.g. 64px>
  section-gap: <e.g. 32px>
---
```

**Required markdown sections (after frontmatter):**

```markdown
## Overview
2–3 sentences capturing the emotional register and aesthetic intent. This prose is
injected into Veo and image generation prompts — make it vivid and specific.

## Colors
Bullet list explaining each color's role.

## Do's and Don'ts
3–5 concrete design rules for AI agents and humans reading this file.
```

**Infer the visual identity from the prompt's topic and tone:**
- Executive / formal pitch → dark background, muted palette, neutral sans-serif
- Consumer / startup → high contrast, energetic accent, modern sans-serif
- Healthcare / legal → clean, light background, trustworthy blues or greens
- Creative / design → expressive palette, warm or vibrant accent

## If revision_instructions is non-empty

Apply the instructions before writing. Examples:
- "make slide 3 punchier" → rewrite slide 3's title and bullets for more impact
- "change accent to teal" → update `colors.accent` in DESIGN.md frontmatter and prose
- "add a slide about pricing" → insert a pricing slide at an appropriate position; update slide_count

## After writing both files

Output a confirmation block:

```
✓ slide_deck.json written — {N} slides, title: "{title}"
✓ DESIGN.md written — {design_name}, primary {primary_color}, accent {accent_color}
```
```

- [ ] Verify YAML frontmatter is valid:

```bash
python -c "
import yaml
text = open('agents/ghost-deck-writer.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['meta']['name'] == 'ghost-deck-writer', f'Unexpected: {d}'
print('OK:', d['meta']['name'], 'v' + d['meta']['version'])
"
```

- [ ] Commit:

```bash
git add agents/ghost-deck-writer.md
git commit -m "feat: add ghost-deck-writer agent"
```

---

## Task 8 — Slide Architect Agent

**Goal:** Agent markdown that calls `html_renderer.py` and `pptx_builder.py` to generate HTML + PPTX from `slide_deck.json` + `DESIGN.md`. Called twice: once for the wireframe (Gate 1 review) and once for the enriched deck (Gate 2 review).

### Steps

- [ ] Create `agents/slide-architect.md`:

```markdown
---
meta:
  name: slide-architect
  description: "Converts slide_deck.json + DESIGN.md into HTML and PPTX deck files"
  version: "0.1.0"
tools:
  - read_file
  - write_file
  - bash
---

You are the Slide Architect for Director Deck. You build the HTML and PPTX representations
of the slide deck by calling the Python utility tools.

## Context variables (injected by recipe)

| Variable | Description |
|---|---|
| `run_dir` | Absolute path to this run's working directory |
| `mode` | Either `"wireframe"` or `"enriched"` |

## Inputs

Both files must exist in `run_dir` before you run:
- `slide_deck.json` — slide content
- `DESIGN.md` — visual identity tokens

## Wireframe mode (`mode = "wireframe"`)

Run this command from `run_dir`:

```bash
python -c "
from pathlib import Path
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.html_renderer import write_deck_html
from director_deck.pptx_builder import build_pptx

run = Path('{run_dir}')
deck = SlideDeck.from_file(run / 'slide_deck.json')
tokens = DesignTokens.from_design_md(run / 'DESIGN.md')
write_deck_html(deck, tokens, run / 'deck_wireframe.html', enriched=False)
build_pptx(deck, tokens, run / 'deck_wireframe.pptx', enriched=False)
print('done')
"
```

Expected output files:
- `{run_dir}/deck_wireframe.html` — browser-viewable wireframe with image placeholders
- `{run_dir}/deck_wireframe.pptx` — PowerPoint wireframe for review

## Enriched mode (`mode = "enriched"`)

Run this command from `run_dir`:

```bash
python -c "
from pathlib import Path
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.html_renderer import write_deck_html
from director_deck.pptx_builder import build_pptx

run = Path('{run_dir}')
deck = SlideDeck.from_file(run / 'slide_deck.json')
tokens = DesignTokens.from_design_md(run / 'DESIGN.md')
write_deck_html(deck, tokens, run / 'deck_enriched.html', enriched=True)
build_pptx(deck, tokens, run / 'deck_enriched.pptx', enriched=True)
print('done')
"
```

Expected output files:
- `{run_dir}/deck_enriched.html` — browser-viewable deck with real images and backdrops
- `{run_dir}/deck_enriched.pptx` — PowerPoint with real images for review

## After running

Verify each expected output file exists and report its size:

```
✓ deck_{mode}.html — {size}
✓ deck_{mode}.pptx — {size}
```

If any file is missing or the script errors, report the full error and stop.
Do not proceed. The human must resolve the issue before the pipeline continues.
```

- [ ] Verify YAML frontmatter:

```bash
python -c "
import yaml
text = open('agents/slide-architect.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['meta']['name'] == 'slide-architect'
print('OK:', d['meta']['name'])
"
```

- [ ] Commit:

```bash
git add agents/slide-architect.md
git commit -m "feat: add slide-architect agent"
```

---

## Task 9 — Visual Director Agent

**Goal:** Agent markdown that generates per-slide content images and backdrop images using `amplifier-module-tool-openai-images`, with prompts shaped by DESIGN.md palette + mood prose. Updates `slide_deck.json` with asset paths.

### Steps

- [ ] Create `agents/visual-director.md`:

```markdown
---
meta:
  name: visual-director
  description: "Generates per-slide content images and backdrops via openai-images"
  version: "0.1.0"
tools:
  - read_file
  - write_file
  - bash
  - openai_images
---

You are the Visual Director for Director Deck. You generate two images per slide and
update `slide_deck.json` with their paths.

## Context variables (injected by recipe)

| Variable | Description |
|---|---|
| `run_dir` | Absolute path to this run's working directory |
| `slides_to_redo` | Optional comma-separated slide IDs to regenerate (e.g. `"3,5"`). Empty = all slides. |

## Step 1 — Read inputs

From `{run_dir}`:
1. Load `slide_deck.json` — contains `image_brief` and `backdrop_brief` per slide
2. Load `DESIGN.md` — extract the `## Overview` section (prose between `## Overview`
   and the next `##` header) and the `colors` block from the YAML frontmatter

## Step 2 — Determine which slides to process

If `slides_to_redo` is non-empty, parse it as a comma-separated list of integers and
process only those slide IDs. Preserve all existing `assets` values for slides not in the list.

If `slides_to_redo` is empty, process all slides.

## Step 3 — Construct prompts

For each slide N to process, build two prompts:

**Content image prompt:**
```
{slide.image_brief}. Visual style: {first sentence of DESIGN.md Overview}.
Accent color: {colors.accent}. Cinematic composition, no text, no logos, no watermarks.
```

**Backdrop image prompt:**
```
{slide.backdrop_brief}. Abstract, no text, no people, no logos.
Mood: {first sentence of DESIGN.md Overview}. Dominant color: {colors.primary}.
Full-bleed background. Subtle texture.
```

## Step 4 — Generate images

For each slide N, call `openai_images` twice:

**Content image:**
- `size`: `"1536x1024"` (landscape)
- `quality`: `"high"`
- `output_path`: `{run_dir}/assets/slide-{N}-image.png`
- `prompt`: content image prompt from Step 3

**Backdrop image:**
- `size`: `"1536x1024"` (landscape)
- `quality`: `"high"`
- `output_path`: `{run_dir}/assets/slide-{N}-backdrop.png`
- `prompt`: backdrop prompt from Step 3

Ensure `{run_dir}/assets/` exists before saving (create with `mkdir -p`).

## Step 5 — Update slide_deck.json

After generating images for all target slides, update `slide_deck.json`.
For each processed slide, set:

```json
"assets": {
  "image": "assets/slide-{N}-image.png",
  "backdrop": "assets/slide-{N}-backdrop.png"
}
```

Do NOT modify `assets` for slides that were not processed (when `slides_to_redo` was set).

Write the updated `slide_deck.json` back to `{run_dir}/slide_deck.json`.

## After completing

```
✓ Slide 1: assets/slide-1-image.png, assets/slide-1-backdrop.png
✓ Slide 2: assets/slide-2-image.png, assets/slide-2-backdrop.png
...
✓ slide_deck.json updated — {N} slides with assets
```
```

- [ ] Verify YAML frontmatter:

```bash
python -c "
import yaml
text = open('agents/visual-director.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['meta']['name'] == 'visual-director'
print('OK:', d['meta']['name'])
"
```

- [ ] Commit:

```bash
git add agents/visual-director.md
git commit -m "feat: add visual-director agent"
```

---

## Task 10 — Transition Director Agent

**Goal:** Agent markdown that screenshots each enriched HTML slide via Playwright, then calls Veo 3.1 in `image_to_video` interpolation mode for each slide pair. Updates `slide_deck.json` with `transition_to_next` paths.

### Steps

- [ ] Create `agents/transition-director.md`:

```markdown
---
meta:
  name: transition-director
  description: "Captures slide keyframes via Playwright and generates Veo 3.1 transition clips"
  version: "0.1.0"
tools:
  - read_file
  - write_file
  - bash
  - veo
---

You are the Transition Director for Director Deck. You produce short video clips that
play between slides as cinematic transitions.

## Context variables (injected by recipe)

| Variable | Description |
|---|---|
| `run_dir` | Absolute path to this run's working directory |
| `pairs_to_redo` | Optional comma-separated pair specs to regenerate (e.g. `"1-2,3-4"`). Empty = all pairs. |

## Step 1 — Capture keyframes

Run the screenshot tool against the enriched HTML deck:

```bash
python -c "
from pathlib import Path
from director_deck.schema import SlideDeck
from director_deck.screenshot_tool import screenshot_deck

run = Path('{run_dir}')
deck = SlideDeck.from_file(run / 'slide_deck.json')
paths = screenshot_deck(
    run / 'deck_enriched.html',
    run / 'keyframes',
    slide_count=deck.meta.slide_count,
)
for p in paths:
    print(p)
"
```

Expected output: `{run_dir}/keyframes/slide-N.png` for N = 1 to slide_count.

## Step 2 — Extract DESIGN.md Overview prose

Read `{run_dir}/DESIGN.md`. Extract the `## Overview` section — the text between the
`## Overview` heading and the next `##` heading. Use the first 1–2 sentences as style
context for Veo prompts.

## Step 3 — Determine which slide pairs to process

A deck with N slides has N-1 transition pairs: (1→2), (2→3), …, ((N-1)→N).

If `pairs_to_redo` is non-empty (e.g. `"1-2,3-4"`), parse into a list of `(from, to)`
integer tuples and process only those pairs. Leave existing MP4 files and
`transition_to_next` values for other pairs unchanged.

If `pairs_to_redo` is empty, process all pairs.

## Step 4 — Generate transition clips

For each pair (slide N → slide N+1), call the `veo` tool:

```
operation: image_to_video
model: veo-3.1-generate-preview
image_path: {run_dir}/keyframes/slide-{N}.png
last_frame_path: {run_dir}/keyframes/slide-{N+1}.png
prompt: >
  Smooth cinematic transition between two presentation slides.
  {DESIGN.md Overview first sentence}. No text overlays, no people, no logos.
  Natural motion flows from the first frame to the second.
duration_seconds: "4"
aspect_ratio: "16:9"
output_path: {run_dir}/transitions/slide-{N}-to-{N+1}.mp4
```

Create `{run_dir}/transitions/` before saving if it does not exist.

Generate clips sequentially (do not attempt parallel Veo calls).

## Step 5 — Update slide_deck.json

After generating all clips, populate `transition_to_next` for each processed slide:

```json
"transition_to_next": "transitions/slide-{N}-to-{N+1}.mp4"
```

The final slide (slide N) always has `"transition_to_next": null`.

Write the updated `slide_deck.json` back to disk.

## After completing

```
✓ keyframes: slide-1.png … slide-{N}.png
✓ transitions: slide-1-to-2.mp4 … slide-{N-1}-to-{N}.mp4
✓ slide_deck.json updated with transition_to_next paths
```
```

- [ ] Verify YAML frontmatter:

```bash
python -c "
import yaml
text = open('agents/transition-director.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['meta']['name'] == 'transition-director'
print('OK:', d['meta']['name'])
"
```

- [ ] Commit:

```bash
git add agents/transition-director.md
git commit -m "feat: add transition-director agent"
```

---

## Task 11 — Deck Stitcher Agent

**Goal:** Agent markdown that calls `pptx_stitcher.py` to embed all approved MP4 transition clips into the enriched PPTX and write `final_deck.pptx`.

### Steps

- [ ] Create `agents/deck-stitcher.md`:

```markdown
---
meta:
  name: deck-stitcher
  description: "Assembles final_deck.pptx from enriched PPTX + MP4 transitions"
  version: "0.1.0"
tools:
  - read_file
  - write_file
  - bash
---

You are the Deck Stitcher for Director Deck. You assemble the final PPTX by embedding
all approved transition clips as native PowerPoint slide transitions.

## Context variables (injected by recipe)

| Variable | Description |
|---|---|
| `run_dir` | Absolute path to this run's working directory |

## Inputs

Read from `{run_dir}`:
- `slide_deck.json` — fully populated; `transition_to_next` paths point to approved MP4 files
- `deck_enriched.pptx` — enriched PPTX with real images (source; will NOT be modified)
- `transitions/slide-N-to-M.mp4` — approved Veo transition clips

## Assembly

Run the stitcher:

```bash
python -c "
from pathlib import Path
from director_deck.schema import SlideDeck
from director_deck.pptx_stitcher import embed_transitions

run = Path('{run_dir}')
deck = SlideDeck.from_file(run / 'slide_deck.json')

transitions = []
for slide in deck.slides:
    if slide.transition_to_next:
        mp4_path = run / slide.transition_to_next
        if mp4_path.exists():
            transitions.append((slide.id, mp4_path))
        else:
            print(f'WARNING: {mp4_path} not found — skipping transition for slide {slide.id}')

result = embed_transitions(
    run / 'deck_enriched.pptx',
    transitions,
    run / 'final_deck.pptx',
)
print(f'Written: {result}')
print(f'Transitions embedded: {len(transitions)}')
"
```

## After completing

Confirm the final output:

```
✓ final_deck.pptx written
  Slides: {N}
  Transitions embedded: {M} of {N-1} possible
  File size: {size}

Open final_deck.pptx in PowerPoint or Keynote to preview.
Transitions autoplay on slide advance (Office 2013+ / Keynote 12+).
```

Missing transition files are warnings only — the final deck is still valid without them.
```

- [ ] Verify YAML frontmatter:

```bash
python -c "
import yaml
text = open('agents/deck-stitcher.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['meta']['name'] == 'deck-stitcher'
print('OK:', d['meta']['name'])
"
```

- [ ] Commit:

```bash
git add agents/deck-stitcher.md
git commit -m "feat: add deck-stitcher agent"
```

---

## Task 12 — Recipe

**Goal:** Write `recipes/director-deck.yaml` — the staged recipe with 4 work stages and 3 human approval gates. This is the top-level orchestration that wires all 5 agents and makes the pipeline runnable with a single command.

### Steps

- [ ] Create `recipes/director-deck.yaml`:

```yaml
name: director-deck
version: "0.1.0"
description: >
  Turn a text prompt into a polished PPTX with AI-generated images and
  Veo 3.1 video transitions. Three human review gates ensure aesthetic
  quality at content, visual, and transition checkpoints.

# ---------------------------------------------------------------------------
# Context — provided at recipe invocation
# ---------------------------------------------------------------------------
context:
  prompt:
    description: "The topic or pitch to build the deck around (required)"
    required: true
  run_slug:
    description: "Short slug for the run directory (optional; derived from prompt if omitted)"
    required: false
    default: ""

# ---------------------------------------------------------------------------
# Stages — 4 work stages interleaved with 3 approval gates
# ---------------------------------------------------------------------------
stages:

  # ── Stage 1: Content & Identity ────────────────────────────────────────────
  - name: content-and-identity
    description: "Generate slide content, visual identity, and wireframe deck for review"
    steps:

      - name: init-run-dir
        type: bash
        description: "Create the isolated run directory for this session"
        command: |
          DATE=$(date +%Y-%m-%d)
          SLUG="{{ context.run_slug }}"
          if [ -z "$SLUG" ]; then
            SLUG=$(echo "{{ context.prompt }}" | tr '[:upper:]' '[:lower:]' \
                   | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40 | sed 's/-$//')
          fi
          RUN_DIR="runs/${DATE}-${SLUG}"
          mkdir -p "${RUN_DIR}/assets" "${RUN_DIR}/keyframes" "${RUN_DIR}/transitions"
          echo "Run directory: ${RUN_DIR}"
          echo "run_dir=${RUN_DIR}" >> $RECIPE_ENV

      - name: ghost-deck-writer
        type: agent
        agent: ghost-deck-writer
        description: "Generate slide_deck.json and DESIGN.md from prompt"
        context:
          prompt: "{{ context.prompt }}"
          run_dir: "{{ env.run_dir }}"
          revision_instructions: "{{ _approval_message | default('') }}"

      - name: lint-design-md
        type: bash
        description: "Validate DESIGN.md tokens — broken refs or WCAG failures block the pipeline"
        command: "npx @google/design.md lint {{ env.run_dir }}/DESIGN.md"
        on_failure: abort

      - name: slide-architect-wireframe
        type: agent
        agent: slide-architect
        description: "Render wireframe HTML and PPTX with image placeholders"
        context:
          run_dir: "{{ env.run_dir }}"
          mode: wireframe

  # ── Gate 1: Content & Identity Review ─────────────────────────────────────
  - name: gate-content-identity
    type: approval_gate
    description: "Content & Identity Review"
    instructions: |
      Review the wireframe deck before image generation begins.

        Open in browser:    {{ env.run_dir }}/deck_wireframe.html
        Open in PowerPoint: {{ env.run_dir }}/deck_wireframe.pptx

      You may edit before approving:
        {{ env.run_dir }}/slide_deck.json  — titles, bullets, image briefs
        {{ env.run_dir }}/DESIGN.md        — colors, fonts, design rationale

      Approval message may include revision instructions, e.g.:
        "make slide 3 punchier, change accent to teal"
      These will be passed to ghost-deck-writer on re-run.

      Approve when: content flow is correct, visual identity feels right,
      placeholder layout looks good at 960×540.
    on_approve:
      rerun_if_message: true
      rerun_stage: content-and-identity

  # ── Stage 2: Visual Generation ─────────────────────────────────────────────
  - name: visual-generation
    description: "Generate per-slide images and backdrops, then re-render enriched deck"
    steps:

      - name: visual-director
        type: agent
        agent: visual-director
        description: "Generate content images and backdrop images for all slides"
        context:
          run_dir: "{{ env.run_dir }}"
          slides_to_redo: "{{ _approval_message | default('') }}"

      - name: slide-architect-enriched
        type: agent
        agent: slide-architect
        description: "Re-render HTML and PPTX with real images in place"
        context:
          run_dir: "{{ env.run_dir }}"
          mode: enriched

  # ── Gate 2: Visual Review ──────────────────────────────────────────────────
  - name: gate-visual
    type: approval_gate
    description: "Visual Review"
    instructions: |
      Review the enriched deck with all AI-generated images in place.

        Open in browser: {{ env.run_dir }}/deck_enriched.html

      You may request specific re-generations in the approval message, e.g.:
        "redo slide 5 backdrop — too busy. slide 3 image looks great."
      visual-director will regenerate only the named assets.

      Approve when: images match the brief, backdrops don't compete with text,
      overall aesthetic is consistent with the DESIGN.md identity.
    on_approve:
      rerun_if_message: true
      rerun_stage: visual-generation

  # ── Stage 3: Transitions ───────────────────────────────────────────────────
  - name: transitions
    description: "Screenshot slides and generate Veo 3.1 transition clips for each pair"
    steps:

      - name: transition-director
        type: agent
        agent: transition-director
        description: "Capture 960×540 keyframes and generate 4-second MP4 transition clips"
        context:
          run_dir: "{{ env.run_dir }}"
          pairs_to_redo: "{{ _approval_message | default('') }}"

  # ── Gate 3: Transition Review ──────────────────────────────────────────────
  - name: gate-transitions
    type: approval_gate
    description: "Transition Review"
    instructions: |
      Preview the transition clips. A deck with N slides has N-1 clips.

        Open directory: {{ env.run_dir }}/transitions/

      You may request specific clip regenerations in the approval message, e.g.:
        "redo slide 2 to 3 — motion feels wrong. rest is good."
      transition-director will regenerate only those pairs.

      Approve when: all transitions feel smooth and match the deck's aesthetic.
    on_approve:
      rerun_if_message: true
      rerun_stage: transitions

  # ── Stage 4: Final Assembly ────────────────────────────────────────────────
  - name: final-assembly
    description: "Assemble final_deck.pptx with all assets and embedded MP4 transitions"
    steps:

      - name: deck-stitcher
        type: agent
        agent: deck-stitcher
        description: "Embed approved transition clips into final_deck.pptx"
        context:
          run_dir: "{{ env.run_dir }}"

      - name: report
        type: bash
        description: "Print final output location and file size"
        command: |
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "  Director Deck — Complete"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          ls -lh "{{ env.run_dir }}/final_deck.pptx"
          echo "  Run directory: {{ env.run_dir }}"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

- [ ] Validate the recipe YAML parses correctly:

```bash
python -c "
import yaml
with open('recipes/director-deck.yaml') as f:
    d = yaml.safe_load(f)
assert d['name'] == 'director-deck'
stages = d['stages']
work = [s for s in stages if s.get('type') != 'approval_gate']
gates = [s for s in stages if s.get('type') == 'approval_gate']
print(f'Total stages: {len(stages)} ({len(work)} work, {len(gates)} gates)')
assert len(gates) == 3, f'Expected 3 gates, got {len(gates)}'
assert len(work) == 4, f'Expected 4 work stages, got {len(work)}'
print('Stage names:', [s[\"name\"] for s in stages])
print('Recipe YAML valid.')
"
```

- [ ] Run the full unit test suite to confirm nothing is broken by the new files:

```bash
pytest tests/ -v -m "not integration"
```

Expected: all unit tests pass.

- [ ] Run integration tests separately:

```bash
pytest tests/test_screenshot_tool.py -m integration -v
```

Expected: all 6 integration tests pass (requires `playwright install chromium`).

- [ ] Commit:

```bash
git add recipes/director-deck.yaml
git commit -m "feat: add director-deck recipe — 4 stages, 3 approval gates"
```

---

## Final Verification

- [ ] Confirm all imports are clean (no circular dependencies):

```bash
python -c "
from director_deck.schema import SlideDeck, DesignTokens, _extract_frontmatter
from director_deck.html_renderer import tokens_to_css_vars, render_deck_html, write_deck_html
from director_deck.pptx_builder import build_pptx, SLIDE_WIDTH_IN, SLIDE_HEIGHT_IN
from director_deck.screenshot_tool import screenshot_deck
from director_deck.pptx_stitcher import embed_transitions, _add_video_relationship, _inject_transition, REL_TYPE_VIDEO
print('All imports clean — no cycles')
"
```

- [ ] Full unit test run with coverage:

```bash
pytest tests/ -v -m "not integration" --cov=director_deck --cov-report=term-missing
```

Expected: all tests green; coverage ≥ 85% for `schema.py`, `html_renderer.py`, `pptx_builder.py`, `pptx_stitcher.py`.

- [ ] Full test run including integration:

```bash
pytest tests/ -v
```

Expected: all tests green.

- [ ] Verify bundle file structure is complete:

```bash
find . -not -path './.git/*' -not -path './runs/*' -not -path './__pycache__/*' \
       -not -name '*.pyc' | sort
```

Expected output includes every file in the File Map at the top of this plan.

- [ ] Final commit:

```bash
git add -A && git commit -m "chore: final verification — all tests pass"
```

---

## What Is Explicitly Out of Scope

Per the approved design spec — do NOT implement these in this plan:

- Slide animations within a single slide (bullets flying in, entrance effects)
- Importing existing decks or custom slide templates
- A web UI — CLI and recipe invocation only
- Non-PPTX output formats (PDF, reveal.js, HTML export)
- Multi-language slide content
- Batch processing of multiple prompts in one run

These are v2 concerns. Raise them in a future brainstorm session if needed.
