import pytest
from director_deck.schema import (
    SlideDeck,
    DesignTokens,
    _extract_frontmatter,
)


class TestSlideDeck:
    def test_slide_count_mismatch_raises(self, sample_deck_data):
        bad = {
            **sample_deck_data,
            "meta": {**sample_deck_data["meta"], "slide_count": 99},
        }
        with pytest.raises(ValueError, match="slide_count"):
            SlideDeck.model_validate(bad)

    def test_round_trip_file(self, sample_deck_data, tmp_path):
        deck = SlideDeck.model_validate(sample_deck_data)
        p = tmp_path / "slide_deck.json"
        deck.to_file(p)
        loaded = SlideDeck.from_file(p)
        assert loaded.meta.title == "Test Deck"
        assert len(loaded.slides) == 2
        assert loaded.slides[1].title == "Slide Two"

    def test_from_file_preserves_assets_and_transition(
        self, tmp_path, sample_deck_data
    ):
        data = {
            **sample_deck_data,
            "meta": {**sample_deck_data["meta"], "slide_count": 1},
            "slides": [
                {
                    **sample_deck_data["slides"][0],
                    "assets": {
                        "image": "assets/slide-1-image.png",
                        "backdrop": "assets/slide-1-backdrop.png",
                    },
                    "transition_to_next": "transitions/slide-1-to-2.mp4",
                }
            ],
        }
        deck = SlideDeck.model_validate(data)
        p = tmp_path / "slide_deck.json"
        deck.to_file(p)
        loaded = SlideDeck.from_file(p)
        assert loaded.slides[0].assets.image == "assets/slide-1-image.png"
        assert loaded.slides[0].transition_to_next == "transitions/slide-1-to-2.mp4"


class TestDesignTokens:
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

    def test_spacing_parsed(self, sample_design_md):
        tokens = DesignTokens.from_design_md(sample_design_md)
        assert tokens.spacing is not None
        assert tokens.spacing["slide-padding"] == "64px"

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
