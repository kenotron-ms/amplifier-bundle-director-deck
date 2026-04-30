"""
pptx_fixer.py — Post-process PPTX to make video slides play seamlessly in PowerPoint.

  Bug 1: hlinkClick r:id="" — PowerPoint can't link click-to-play.
  Bug 2: delay="indefinite" — video shows icon, doesn't autoplay.
  Bug 3: ALL video slides share ONE poster frame image (1px transparent PNG).
         python-pptx reuses image2.png for every add_movie() call.
         Replacing it only fixes the first video slide.
         Fix: create a unique poster frame file per video slide and update rels.
  Bug 4: No auto-advance — presenter must click after each video.
"""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

from lxml import etree  # type: ignore[import-untyped]

P_NS       = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS       = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS       = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MEDIA_REL  = "http://schemas.microsoft.com/office/2007/relationships/media"
IMG_REL    = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def fix_video_slides(
    pptx_path: Path,
    *,
    keyframe_dir: Path | None = None,
    slide_durations_s: list[float] | None = None,
) -> int:
    """Fix all video slides for seamless PowerPoint playback.

    keyframe_dir      — directory of slide-{N}.png (1-indexed); each video slide
                        gets its own unique poster frame so the correct source slide
                        appears before playback begins.
    slide_durations_s — seconds per video slide; adds advTm for auto-advance.
    """
    pptx_path = Path(pptx_path)
    tmp_path  = pptx_path.with_suffix(".fixing.pptx")

    # ── Read all data upfront ─────────────────────────────────────────────────
    with zipfile.ZipFile(pptx_path, "r") as zin:
        all_items = zin.infolist()

        slide_names = sorted(
            [i.filename for i in all_items
             if i.filename.startswith("ppt/slides/slide")
             and i.filename.endswith(".xml")
             and "_rels" not in i.filename],
            key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),  # type: ignore[union-attr]
        )

        rels_raw: dict[str, bytes] = {
            i.filename: zin.read(i.filename)
            for i in all_items
            if "_rels/" in i.filename and i.filename.endswith(".rels")
        }

    # ── Build per-video-slide fix plan ────────────────────────────────────────
    # Each video slide needs:
    #   media_rId    — for hlinkClick fix
    #   new_img_zip  — unique path in ppt/media/ for THIS slide's poster frame
    #   new_img_data — the keyframe PNG bytes
    #   new_rels_xml — updated rels pointing rId_img → new_img_zip
    #   dur_ms       — auto-advance in ms
    fixes: dict[str, dict] = {}   # slide_path → fix dict
    content_count = 0
    video_idx     = 0

    for slide_path in slide_names:
        sname    = slide_path.split("/")[-1]
        rels_key = f"ppt/slides/_rels/{sname}.rels"
        rdata    = rels_raw.get(rels_key, b"<Relationships/>")
        rroot    = etree.fromstring(rdata)

        media_rId   = None
        old_img_rId = None

        for rel in rroot:
            t = rel.get("Type", "")
            if t == MEDIA_REL:
                media_rId = rel.get("Id")
            if t == IMG_REL:
                old_img_rId = rel.get("Id")

        if media_rId is None:
            content_count += 1
            continue

        # ── This is a video slide ────────────────────────────────────────────
        fix: dict = {
            "media_rId":    media_rId,
            "old_img_rId":  old_img_rId,
            "new_img_zip":  None,
            "new_img_data": None,
            "new_rels_xml": None,
            "dur_ms":       None,
        }

        # Poster frame: unique file per video slide, named kf_poster_{N}.png
        if keyframe_dir:
            kf = Path(keyframe_dir) / f"slide-{content_count}.png"
            if kf.exists():
                new_img_name    = f"kf_poster_{video_idx + 1}.png"
                fix["new_img_zip"]  = f"ppt/media/{new_img_name}"
                fix["new_img_data"] = kf.read_bytes()

                # Rewrite rels: update existing image rel OR add a new one
                new_rroot = etree.fromstring(rdata)
                if old_img_rId:
                    # Change the target of the existing image relationship
                    for rel in new_rroot:
                        if rel.get("Id") == old_img_rId and rel.get("Type") == IMG_REL:
                            rel.set("Target", f"../media/{new_img_name}")
                else:
                    # Add a brand-new image relationship
                    existing_ids = {r.get("Id", "") for r in new_rroot}
                    nums = [int(i[3:]) for i in existing_ids
                            if i.startswith("rId") and i[3:].isdigit()]
                    new_rid = f"rId{max(nums, default=0) + 1}"
                    etree.SubElement(
                        new_rroot,
                        f"{{{PKG_REL_NS}}}Relationship",
                        Id=new_rid,
                        Type=IMG_REL,
                        Target=f"../media/{new_img_name}",
                    )
                    fix["new_blip_rid"] = new_rid   # update blipFill in slide XML

                fix["new_rels_xml"] = etree.tostring(
                    new_rroot,
                    xml_declaration=True,
                    encoding="UTF-8",
                    standalone=True,
                )

        # Auto-advance
        if slide_durations_s and video_idx < len(slide_durations_s):
            fix["dur_ms"] = int(slide_durations_s[video_idx] * 1000)

        fixes[slide_path] = fix
        video_idx += 1

    # ── Rewrite PPTX ─────────────────────────────────────────────────────────
    fixed_count   = 0
    written_names: set[str] = set()

    with zipfile.ZipFile(pptx_path, "r") as zin:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:

            for item in zin.infolist():
                data = zin.read(item.filename)

                # Fix video slide XML
                if item.filename in fixes:
                    fix  = fixes[item.filename]
                    root = etree.fromstring(data)

                    _fix_hlinkclick(root, fix["media_rId"])
                    _fix_timing(root)

                    # If we added a brand-new img rId, update blipFill embed
                    if fix.get("new_blip_rid"):
                        for blip in root.iter(f"{{{A_NS}}}blip"):
                            blip.set(f"{{{R_NS}}}embed", fix["new_blip_rid"])

                    if fix["dur_ms"] is not None:
                        _fix_auto_advance(root, fix["dur_ms"])

                    data = etree.tostring(root, xml_declaration=True,
                                          encoding="UTF-8", standalone=True)
                    fixed_count += 1

                # Update rels for video slides
                elif item.filename.endswith(".rels"):
                    slide_xml = item.filename.replace("/_rels/", "/").replace(".rels", "")
                    if slide_xml in fixes and fixes[slide_xml]["new_rels_xml"]:
                        data = fixes[slide_xml]["new_rels_xml"]

                zout.writestr(item, data)
                written_names.add(item.filename)

            # Write new unique poster frame images
            for fix in fixes.values():
                if fix["new_img_zip"] and fix["new_img_data"]:
                    if fix["new_img_zip"] not in written_names:
                        zout.writestr(fix["new_img_zip"], fix["new_img_data"])
                        written_names.add(fix["new_img_zip"])

    os.replace(tmp_path, pptx_path)
    return fixed_count


def _fix_hlinkclick(slide_root: etree._Element, media_rId: str) -> None:
    for elem in slide_root.iter(f"{{{A_NS}}}hlinkClick"):
        if elem.get("action") == "ppaction://media":
            if not elem.get(f"{{{R_NS}}}id", ""):
                elem.set(f"{{{R_NS}}}id", media_rId)


def _fix_timing(slide_root: etree._Element) -> None:
    for video_elem in slide_root.iter(f"{{{P_NS}}}video"):
        for cond in video_elem.iter(f"{{{P_NS}}}cond"):
            if cond.get("delay") == "indefinite":
                cond.set("delay", "0")


def _fix_auto_advance(slide_root: etree._Element, dur_ms: int) -> None:
    """Rewrite timing so the slide auto-advances exactly when the video ends.

    Three things must be true simultaneously:

    1. root cTn dur="{ms}" fill="hold"
       PowerPoint needs a finite duration to know when the animation ends.
       fill="hold" keeps the last frame visible (default "remove" snaps back
       to frame 0 just before the slide advances — the visible glitch).

    2. media cTn dur="{ms}" fill="hold"
       The inner media timing must also carry an explicit duration so
       PowerPoint syncs its internal clock to the video length.

    3. <p:transition advTm="{ms}"/> inserted BEFORE <p:timing>
       OOXML requires transition to precede timing in <p:sld>.
       When placed after timing, PowerPoint ignores it entirely.
       advTm (no advOnTm — not a real attribute) fires the advance.
    """
    dur_s = str(dur_ms)

    # ── Fix root cTn ─────────────────────────────────────────────────────────
    for ctn in slide_root.iter(f"{{{P_NS}}}cTn"):
        if ctn.get("nodeType") == "tmRoot":
            ctn.set("dur",  dur_s)
            ctn.set("fill", "hold")
            break

    # ── Fix media cTn (inner) ─────────────────────────────────────────────────
    for video in slide_root.iter(f"{{{P_NS}}}video"):
        for ctn in video.iter(f"{{{P_NS}}}cTn"):
            ctn.set("dur",  dur_s)
            ctn.set("fill", "hold")

    # ── Insert <p:transition advTm="{ms}"/> BEFORE <p:timing> ────────────────
    # Remove any existing transition first (might be in wrong position)
    existing = slide_root.find(f"{{{P_NS}}}transition")
    if existing is not None:
        slide_root.remove(existing)

    transition = etree.Element(f"{{{P_NS}}}transition")
    transition.set("advTm", dur_s)

    # Find <p:timing> and insert transition immediately before it
    timing = slide_root.find(f"{{{P_NS}}}timing")
    if timing is not None:
        idx = list(slide_root).index(timing)
    else:
        # Fall back: after <p:clrMapOvr> or <p:cSld>
        for tag in [f"{{{P_NS}}}clrMapOvr", f"{{{P_NS}}}cSld"]:
            elem = slide_root.find(tag)
            if elem is not None:
                idx = list(slide_root).index(elem) + 1
                break
        else:
            idx = len(slide_root)

    slide_root.insert(idx, transition)
