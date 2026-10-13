import pytest
from director_deck.schema import SlideDeck, DesignTokens
from director_deck.html_renderer import (
    tokens_to_css_vars,
    render_deck_html,
    write_deck_html,
)


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
        "slides": [
            {
                **sample_deck_data["slides"][0],
                "assets": {
                    "image": "assets/slide-1-image.png",
                    "backdrop": "assets/slide-1-backdrop.png",
                },
            }
        ],
    }
    return SlideDeck.model_validate(data)


class TestTokensToCssVars:
    def test_primary_color_present(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--color-primary: #0F172A;" in css

    def test_on_surface_color_present(self, tokens):
        """The on_surface field must render as --color-on-surface (hyphen, not underscore)."""
        css = tokens_to_css_vars(tokens)
        assert "--color-on-surface: #F1F5F9;" in css

    def test_h1_size_var(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--font-h1-size: 48px;" in css

    def test_spacing_slide_padding(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert "--spacing-slide-padding: 64px;" in css

    def test_wrapped_in_root_block(self, tokens):
        css = tokens_to_css_vars(tokens)
        assert css.startswith(":root {")
        assert css.strip().endswith("}")


class TestRenderDeckHtml:
    def test_wireframe_mode_has_placeholder_not_img(self, deck, tokens):
        html = render_deck_html(deck, tokens, enriched=False)
        assert 'class="image-placeholder"' in html
        assert "<img " not in html

    def test_enriched_uses_backdrop_without_competing_image_panel(self, enriched_deck, tokens):
        html = render_deck_html(enriched_deck, tokens, enriched=True)
        assert "assets/slide-1-backdrop.png" in html
        assert "assets/slide-1-image.png" not in html
        assert "<img " not in html
        assert 'class="image-placeholder"' not in html
        assert "Point A" in html

    def test_enriched_with_backdrop_has_background_image_style(
        self, enriched_deck, tokens
    ):
        html = render_deck_html(enriched_deck, tokens, enriched=True)
        assert "background-image" in html
        assert "assets/slide-1-backdrop.png" in html

    def test_all_slide_divs_present_with_correct_ids(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert 'id="slide-1"' in html
        assert 'id="slide-2"' in html

    def test_css_vars_injected_in_style_block(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert "--color-primary" in html

    def test_html_doctype_present(self, deck, tokens):
        html = render_deck_html(deck, tokens)
        assert html.startswith("<!DOCTYPE html>")

    def test_enriched_no_assets_preserves_text_without_placeholder(self, deck, tokens):
        """Placeholders belong to wireframe review, not the enriched deck."""
        html = render_deck_html(deck, tokens, enriched=True)
        assert 'class="image-placeholder"' not in html
        assert "Slide One" in html
        assert "Point A" in html
        assert "Point B" in html
        assert "Point C" in html

    def test_quote_preserves_supporting_paragraphs(self, deck, tokens):
        slide = deck.slides[0].model_copy(update={
            "layout_type": "quote",
            "hero_statement": "A memorable quote",
            "bullets": ["Example Author", "Context", "Citation"],
        })
        quote_deck = deck.model_copy(update={"slides": [slide]})
        html = render_deck_html(quote_deck, tokens)
        assert '<blockquote class="quote-text">A memorable quote</blockquote>' in html
        assert "Example Author" in html
        assert '<p class="quote-extra">Context</p>' in html
        assert '<p class="quote-extra">Citation</p>' in html

    def test_quote_without_hero_preserves_legacy_bullet_mapping(self, deck, tokens):
        slide = deck.slides[0].model_copy(update={
            "layout_type": "quote",
            "hero_statement": "",
            "bullets": ["A memorable quote", "Example Author", "Context"],
        })
        quote_deck = deck.model_copy(update={"slides": [slide]})
        html = render_deck_html(quote_deck, tokens)
        assert '<blockquote class="quote-text">A memorable quote</blockquote>' in html
        assert '<div class="quote-attribution">— Example Author</div>' in html
        assert '<p class="quote-extra">Context</p>' in html

    def test_comparison_respects_explicit_uneven_column_split(self, deck, tokens):
        slide = deck.slides[0].model_copy(update={
            "layout_type": "comparison",
            "title": "Before / After",
            "bullets": ["Left A", "Left B", "Left C", "", "Right A"],
        })
        comparison_deck = deck.model_copy(update={"slides": [slide]})
        html = render_deck_html(comparison_deck, tokens)
        boundary = html.index('class="comparison-col-title">After')
        assert "Left A" in html[:boundary]
        assert "Left B" in html[:boundary]
        assert "Left C" in html[:boundary]
        assert "Right A" not in html[:boundary]
        assert "Right A" in html[boundary:]
        assert '<li class="bullet"></li>' not in html


class TestWriteDeckHtml:
    def test_writes_file_and_creates_parent_dirs(self, deck, tokens, tmp_path):
        out = tmp_path / "nested" / "deck.html"
        result = write_deck_html(deck, tokens, out)
        assert result == out
        assert out.exists()

    def test_file_content_matches_render(self, deck, tokens, tmp_path):
        out = tmp_path / "deck.html"
        write_deck_html(deck, tokens, out)
        written = out.read_text(encoding="utf-8")
        assert written == render_deck_html(deck, tokens)
