"""
video_processor.py — Post-process Veo 3.1 transition clips.

Veo 3.1 interpolation always emits 8.0s clips with AI-generated audio.
For slide-deck transitions we need:
  • no audio  (Veo's audio is off-brand)
  • variable length (1.5s–3.5s typical)
  • easing that matches human expectation: slow start, fast middle, slow end

WHY SEGMENT-BASED EASING:

  Veo's first frame = current slide, last frame = next slide.
  The interesting visual change is concentrated in the middle of the clip.
  By holding the first/last 0.4s at natural speed and compressing the middle,
  we get genuine ease-in-out: the slide changes gently at the start, drives
  through the transformation, and lands gently on the next slide.
  No minterpolate needed — we're keeping real Veo frames, just selecting
  them non-uniformly.

OUTPUT CONTRACT:
  H.264 / yuv420p / CFR / +faststart — required for PowerPoint scrubbing
  and HTML5 <video> streaming without seeking delays.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

Easing = Literal["linear", "ease_in", "ease_out", "ease_in_out"]
Layout = Literal[
    "hero", "statement", "stat_callout", "quote",
    "comparison", "full_bleed", "bullets", "process_flow", "timeline",
]

__all__ = [
    "Easing",
    "Layout",
    "VideoProcessingError",
    "get_video_duration",
    "process_transition",
    "suggest_transition_duration",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class VideoProcessingError(RuntimeError):
    """Raised when ffmpeg/ffprobe fails or produces an unusable result."""


# ---------------------------------------------------------------------------
# ffprobe
# ---------------------------------------------------------------------------

def get_video_duration(path: Path) -> float:
    """Return the duration of *path* in seconds using ffprobe.

    Raises
    ------
    FileNotFoundError      — if *path* does not exist.
    VideoProcessingError   — if ffprobe is missing or returns a bad result.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    if shutil.which("ffprobe") is None:
        raise VideoProcessingError("ffprobe not found on PATH. Install ffmpeg.")

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise VideoProcessingError(
            f"ffprobe failed for {path}:\n{result.stderr.strip()}"
        )
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise VideoProcessingError(
            f"ffprobe returned non-numeric duration for {path}: {result.stdout!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Filter graph construction  (private, fully deterministic)
# ---------------------------------------------------------------------------

def _build_filter_complex(
    *,
    input_dur: float,
    target_dur: float,
    easing: Easing,
    hold_s: float,
) -> str:
    """Build the ffmpeg -filter_complex string for the requested retime.

    Segment logic
    -------------
    For ease_in_out:  [hold][fast middle][hold]
    For ease_in:      [hold][compressed tail]
    For ease_out:     [compressed head][hold]
    For linear:       single setpts multiplier

    setpts multiplier = (output_length / input_length) per segment.
    Held segments use PTS-STARTPTS (1×). Falls back to linear when
    the hold geometry can't fit in the requested target.

    Returns a filter_complex string whose final label is [out].
    """
    # Graceful fall-backs ──────────────────────────────────────────────────
    if easing == "ease_in_out" and target_dur <= 2 * hold_s:
        easing = "linear"
    if easing in ("ease_in", "ease_out") and target_dur <= hold_s:
        easing = "linear"

    if easing == "linear":
        factor = target_dur / input_dur
        return f"[0:v]setpts={factor:.6f}*PTS[out]"

    if easing == "ease_in":
        # first hold_s held, remainder compressed
        s1 = hold_s
        mid_factor = (target_dur - hold_s) / (input_dur - hold_s)
        return (
            f"[0:v]trim=start=0:end={s1:.6f},setpts=PTS-STARTPTS[v1];"
            f"[0:v]trim=start={s1:.6f}:end={input_dur:.6f},"
            f"setpts={mid_factor:.6f}*(PTS-STARTPTS)[v2];"
            f"[v1][v2]concat=n=2:v=1:a=0[out]"
        )

    if easing == "ease_out":
        # head compressed, last hold_s held
        s1 = input_dur - hold_s
        mid_factor = (target_dur - hold_s) / s1
        return (
            f"[0:v]trim=start=0:end={s1:.6f},"
            f"setpts={mid_factor:.6f}*(PTS-STARTPTS)[v1];"
            f"[0:v]trim=start={s1:.6f}:end={input_dur:.6f},"
            f"setpts=PTS-STARTPTS[v2];"
            f"[v1][v2]concat=n=2:v=1:a=0[out]"
        )

    # ease_in_out ────────────────────────────────────────────────────────────
    s1 = hold_s
    s2 = input_dur - hold_s
    mid_factor = (target_dur - 2 * hold_s) / (s2 - s1)
    return (
        f"[0:v]trim=start=0:end={s1:.6f},setpts=PTS-STARTPTS[v1];"
        f"[0:v]trim=start={s1:.6f}:end={s2:.6f},"
        f"setpts={mid_factor:.6f}*(PTS-STARTPTS)[v2];"
        f"[0:v]trim=start={s2:.6f}:end={input_dur:.6f},setpts=PTS-STARTPTS[v3];"
        f"[v1][v2][v3]concat=n=3:v=1:a=0[out]"
    )


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def process_transition(
    input_mp4: Path,
    output_mp4: Path,
    *,
    target_duration_s: float,
    input_duration_s: float | None = None,
    easing: Easing = "ease_in_out",
    hold_s: float = 0.4,
    fps: int = 30,
) -> Path:
    """Process a Veo 3.1 transition clip: remove audio, retime, apply easing.

    Parameters
    ----------
    input_mp4          : Path to the raw Veo-generated MP4.
    output_mp4         : Destination path. Parent directory created if needed.
    target_duration_s  : Desired output duration in seconds.
    input_duration_s   : Actual input length. Probed with ffprobe if None.
    easing             : Easing curve — linear | ease_in | ease_out | ease_in_out.
    hold_s             : How many input seconds to keep at ~1× at each eased end.
                         Falls back to linear if hold cannot fit target_duration_s.
    fps                : Output frame rate (CFR). 30 is standard for presentations.

    Returns
    -------
    output_mp4 Path (same object, confirmed non-empty file on disk).

    Raises
    ------
    FileNotFoundError, ValueError, VideoProcessingError
    """
    input_mp4  = Path(input_mp4)
    output_mp4 = Path(output_mp4)

    if not input_mp4.is_file():
        raise FileNotFoundError(f"Input video not found: {input_mp4}")
    if shutil.which("ffmpeg") is None:
        raise VideoProcessingError("ffmpeg not found on PATH.")
    if target_duration_s <= 0:
        raise ValueError(f"target_duration_s must be > 0, got {target_duration_s}")
    if hold_s < 0:
        raise ValueError(f"hold_s must be >= 0, got {hold_s}")
    if easing not in ("linear", "ease_in", "ease_out", "ease_in_out"):
        raise ValueError(f"Unknown easing: {easing!r}")

    input_dur = (
        input_duration_s
        if input_duration_s is not None
        else get_video_duration(input_mp4)
    )
    if input_dur <= 0:
        raise VideoProcessingError(f"Invalid input duration: {input_dur}")

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = _build_filter_complex(
        input_dur=input_dur,
        target_dur=target_duration_s,
        easing=easing,
        hold_s=hold_s,
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(input_mp4),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-an",                      # strip Veo's AI-generated audio
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",               # visually lossless quality
        "-pix_fmt", "yuv420p",      # REQUIRED: PPTX + QuickTime compatibility
        "-r", str(fps),             # CFR — required for PPTX timeline scrubbing
        "-movflags", "+faststart",  # HTML5 <video> streaming (moov before mdat)
        str(output_mp4),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise VideoProcessingError(
            f"ffmpeg failed.\n  cmd: {' '.join(cmd)}\n"
            f"  stderr:\n{result.stderr.strip()}"
        )
    if not output_mp4.is_file() or output_mp4.stat().st_size == 0:
        raise VideoProcessingError(f"ffmpeg produced no output at {output_mp4}")

    return output_mp4


# ---------------------------------------------------------------------------
# Duration heuristic
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Duration heuristics
# ---------------------------------------------------------------------------
#
# WHY LAYOUT ALONE IS NOT ENOUGH
#
# Layout gives structure; slide CONTENT and deck MOOD give weight.
# "30 cha chaan tengs lost per year" needs more time to land than "94% uptime".
# A full-bleed silk-stocking filter in a contemplative tea deck needs more time
# than a product screenshot in a pitch deck.
#
# PACING PHILOSOPHY:
#   Contemplative / cultural (food, ritual, memory, craft):
#     Default 4.0–6.0s. Never rush a feeling.
#   Business / pitch (decisions, data, urgency):
#     Default 2.0–3.5s. Keep momentum, respect the audience's time.
#   After emotional-weight slides (loss, revelation, gut-punch stats):
#     Add 1.5–2.0s to whatever the layout default would be.
#   Approaching statement or closing hero:
#     Slow down. These are meditative arrivals.
#
# The ghost-deck-writer prompt instructs the agent to set Slide.transition_duration_s
# explicitly per slide using this reasoning. These rules are the fallback.

# Ordered rules: first match wins. None = "any".
# Defaults lean generous — Veo gives us 8s of source material and it is
# always easier to justify breathing room than to justify rushing a feeling.
_DURATION_RULES: tuple[
    tuple[frozenset[str] | None, frozenset[str] | None, float], ...
] = (
    # Hero slides: dramatic opens/closes deserve time to land
    (frozenset({"hero"}),         None,                      5.0),
    (None,                         frozenset({"hero"}),       5.0),
    # Statement: meditative beats — approach and exit slowly
    (frozenset({"statement"}),    None,                      4.0),
    (None,                         frozenset({"statement"}),  4.0),
    # Full bleed: cinematic images deserve a slow reveal
    (None,                         frozenset({"full_bleed"}), 4.5),
    (frozenset({"full_bleed"}),   None,                      4.0),
    # Stat callout: the punch needs an approach and the landing needs space
    (None,                         frozenset({"stat_callout"}), 4.0),
    (frozenset({"stat_callout"}), None,                      4.0),
    # Comparison: argument slides — steady but not leisurely
    (frozenset({"comparison"}),   None,                      3.5),
    (None,                         frozenset({"comparison"}), 3.5),
)

_DEFAULT_DURATION_S: float = 4.0   # raised: a thoughtful deck deserves time


def suggest_transition_duration(
    from_layout: str,
    to_layout: str,
) -> float:
    """Return a suggested transition duration (seconds) given slide layout types.

    Rule-based, first match wins. These are editorial defaults — authors should
    override per-slide via ``Slide.transition_duration_s`` when content weight
    demands more or less time. See module docstring for pacing philosophy.
    """
    for from_set, to_set, seconds in _DURATION_RULES:
        if (from_set is None or from_layout in from_set) and \
           (to_set   is None or to_layout   in to_set):
            return seconds
    return _DEFAULT_DURATION_S