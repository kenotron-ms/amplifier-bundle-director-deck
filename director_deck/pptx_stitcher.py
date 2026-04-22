from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

# Office Open XML relationship type for embedded video
REL_TYPE_VIDEO = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"
)

# Transition XML template — namespace declarations included since we inject via
# text replacement, not proper XML DOM manipulation.
_TRANSITION_TEMPLATE = (
    "  <p:transition"
    ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' advTm="0" spd="med">'
    '<p:video r:id="{rel_id}"/>'
    "</p:transition>"
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
                "</Relationships>"
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
