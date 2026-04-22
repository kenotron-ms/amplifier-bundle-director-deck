import pytest
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
def html_file(deck, tokens, tmp_path):
    """Write the wireframe deck HTML and return (path, deck)."""
    out = tmp_path / "deck.html"
    write_deck_html(deck, tokens, out)
    return out, deck


@pytest.mark.integration
class TestScreenshotDeck:
    def test_returns_correct_number_of_pngs(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        assert len(paths) == deck.meta.slide_count

    def test_png_files_exist_named_slide_n(self, html_file, tmp_path):
        html_path, deck = html_file
        out_dir = tmp_path / "keyframes"
        paths = screenshot_deck(html_path, out_dir, slide_count=deck.meta.slide_count)
        for i, p in enumerate(paths, start=1):
            assert p.exists()
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
