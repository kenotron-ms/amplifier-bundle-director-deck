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
    p = tmp_path / "trans.mp4"
    p.write_bytes(b"FAKEVIDEO12345")
    return p


class TestHelperFunctions:
    def test_add_video_relationship_injects_rel_id(self):
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            "</Relationships>"
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
            "</Relationships>"
        )
        result = _add_video_relationship(rels_xml, "rVid1", "../media/trans1.mp4")
        assert 'Id="rId1"' in result
        assert 'Id="rVid1"' in result

    def test_inject_transition_adds_ptransition_element(self):
        slide_xml = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            "content"
            "</p:sld>"
        )
        result = _inject_transition(slide_xml, "rVid1")
        assert "<p:transition" in result

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

    def test_mp4_bytes_intact_in_zip(self, wireframe_pptx, fake_mp4, tmp_path):
        out = tmp_path / "final.pptx"
        embed_transitions(wireframe_pptx, [(1, fake_mp4)], out)
        with zipfile.ZipFile(out, "r") as zf:
            assert "ppt/media/trans1.mp4" in zf.namelist()
            data = zf.read("ppt/media/trans1.mp4")
        assert data == b"FAKEVIDEO12345"

    def test_slide_rels_has_video_relationship(
        self, wireframe_pptx, fake_mp4, tmp_path
    ):
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

    def test_multiple_transitions_all_embedded(self, wireframe_pptx, tmp_path):
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
        assert len(prs.slides) == 2
