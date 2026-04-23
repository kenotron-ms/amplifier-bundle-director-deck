from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# SlideDeck schema — content contract shared by all agents
# ---------------------------------------------------------------------------


LayoutType = Literal[
    "bullets",        # title + bullets + image (default, current layout)
    "hero",           # full-bleed backdrop + one punchy centered statement
    "statement",      # section divider — large centered text, no image
    "stat_callout",   # big number/stat + brief context
    "comparison",     # two-column side-by-side
    "quote",          # blockquote + attribution
    "process_flow",   # numbered steps/workflow
    "timeline",       # sequential horizontal/vertical progression
    "full_bleed",     # full-bleed image with minimal text overlay
]


class SlideAssets(BaseModel):
    """Paths to generated image assets for a slide (relative to run_dir)."""

    image: Optional[str] = None
    backdrop: Optional[str] = None


class Slide(BaseModel):
    id: int
    title: str
    layout_type: LayoutType = "bullets"
    hero_statement: Optional[str] = None  # For hero/statement layouts: the "so what?" conclusion (replaces bullets)
    bullets: list[str]
    speaker_notes: str
    image_brief: str
    backdrop_brief: str
    assets: SlideAssets = SlideAssets()
    transition_to_next: Optional[str] = None
    # ── Transition timing ────────────────────────────────────────────────────
    # Target duration (seconds) for the outgoing Veo clip AFTER ffmpeg retiming.
    # None = derive from video_processor.suggest_transition_duration(prev, this).
    transition_duration_s: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=6.0,
        description=(
            "Desired length of the outgoing transition video after ffmpeg retiming. "
            "None → derived from suggest_transition_duration(prev_layout, self.layout_type)."
        ),
    )
    # Easing applied by ffmpeg when retiming the Veo clip.
    transition_easing: Literal["linear", "ease_in", "ease_out", "ease_in_out"] = Field(
        default="ease_in_out",
        description=(
            "ease_in_out (default): natural Veo frames held at both ends, "
            "visual change compressed through the middle. "
            "linear: simple speed multiplier."
        ),
    )


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
