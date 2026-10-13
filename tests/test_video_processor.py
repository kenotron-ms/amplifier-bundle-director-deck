"""
Tests for director_deck.video_processor.

Unit tests cover _build_filter_complex (pure function, no subprocess).
Integration tests (marked) require ffmpeg and a real synthetic video.
"""

import builtins
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from director_deck import video_processor
from director_deck.video_processor import (
    _build_filter_complex,
    get_video_duration,
    process_transition,
    suggest_transition_duration,
)


# ---------------------------------------------------------------------------
# Unit tests: _build_filter_complex
# ---------------------------------------------------------------------------

class TestBuildFilterComplex:
    def _call(self, *, input_dur=8.0, target_dur=2.5, easing="ease_in_out", hold_s=0.4):
        return _build_filter_complex(
            input_dur=input_dur,
            target_dur=target_dur,
            easing=easing,
            hold_s=hold_s,
        )

    # ── linear ──────────────────────────────────────────────────────────────

    def test_linear_produces_single_setpts(self):
        result = self._call(input_dur=8.0, target_dur=2.0, easing="linear")
        assert "setpts=" in result
        assert "concat" not in result
        assert "[out]" in result

    def test_linear_factor_correct(self):
        result = self._call(input_dur=8.0, target_dur=2.0, easing="linear")
        # factor = 2.0 / 8.0 = 0.25
        assert "0.250000*PTS" in result

    def test_linear_no_segments(self):
        result = self._call(input_dur=8.0, target_dur=2.0, easing="linear")
        assert "trim" not in result

    # ── ease_in_out ─────────────────────────────────────────────────────────

    def test_ease_in_out_three_segments(self):
        result = self._call(easing="ease_in_out")
        assert result.count("[v1]") >= 1
        assert result.count("[v2]") >= 1
        assert result.count("[v3]") >= 1
        assert "concat=n=3" in result

    def test_ease_in_out_hold_boundaries(self):
        result = self._call(input_dur=8.0, target_dur=2.5, easing="ease_in_out", hold_s=0.4)
        # s1=0.4, s2=8-0.4=7.6
        assert "end=0.400000" in result
        assert "start=7.600000" in result

    def test_ease_in_out_falls_back_to_linear_when_target_too_short(self):
        # target <= 2*hold: 0.5 <= 2*0.4 = 0.8 → should fall back
        result = self._call(input_dur=8.0, target_dur=0.5, easing="ease_in_out", hold_s=0.4)
        assert "concat" not in result
        assert "setpts=" in result

    def test_ease_in_out_mid_factor_correct(self):
        # input_dur=8, target=2.5, hold=0.4
        # mid_in = 7.6 - 0.4 = 7.2
        # mid_out = 2.5 - 0.8 = 1.7
        # mid_factor = 1.7 / 7.2 ≈ 0.236111
        result = self._call(input_dur=8.0, target_dur=2.5, easing="ease_in_out", hold_s=0.4)
        assert "0.236111" in result

    # ── ease_in ─────────────────────────────────────────────────────────────

    def test_ease_in_two_segments(self):
        result = self._call(easing="ease_in")
        assert "concat=n=2" in result
        assert "[v3]" not in result

    def test_ease_in_falls_back_to_linear(self):
        # target <= hold: 0.3 <= 0.4 → linear
        result = self._call(target_dur=0.3, easing="ease_in", hold_s=0.4)
        assert "concat" not in result

    # ── ease_out ────────────────────────────────────────────────────────────

    def test_ease_out_two_segments(self):
        result = self._call(easing="ease_out")
        assert "concat=n=2" in result

    # ── output always has [out] label ────────────────────────────────────────

    def test_all_easings_produce_out_label(self):
        for easing in ("linear", "ease_in", "ease_out", "ease_in_out"):
            result = self._call(easing=easing)
            assert result.endswith("[out]"), f"Missing [out] for easing={easing}"

    def test_no_scientific_notation(self):
        # setpts factors must not use 'e' notation (ffmpeg rejects it)
        for easing in ("linear", "ease_in", "ease_out", "ease_in_out"):
            result = self._call(easing=easing)
            # Simple check: no 'e+' or 'e-' in the expression
            import re
            assert not re.search(r"\d[eE][+-]\d", result), (
                f"Scientific notation found for easing={easing}: {result}"
            )


# ---------------------------------------------------------------------------
# Unit tests: suggest_transition_duration
# ---------------------------------------------------------------------------

class TestSuggestTransitionDuration:
    def test_hero_from(self):
        assert suggest_transition_duration("hero", "bullets") == 5.0

    def test_hero_to(self):
        assert suggest_transition_duration("bullets", "hero") == 5.0

    def test_statement_from(self):
        assert suggest_transition_duration("statement", "bullets") == 4.0

    def test_statement_to(self):
        assert suggest_transition_duration("bullets", "statement") == 4.0

    def test_stat_callout_from(self):
        assert suggest_transition_duration("stat_callout", "bullets") == 4.0

    def test_stat_callout_to(self):
        assert suggest_transition_duration("bullets", "stat_callout") == 4.0

    def test_bullets_default(self):
        assert suggest_transition_duration("bullets", "bullets") == 4.0

    def test_process_flow_default(self):
        assert suggest_transition_duration("process_flow", "timeline") == 4.0

    def test_hero_wins_over_statement_from(self):
        # hero rule comes first — should be 5.0 not 4.0
        assert suggest_transition_duration("hero", "statement") == 5.0


# ---------------------------------------------------------------------------
# Unit tests: lazy ffmpeg provisioning
# ---------------------------------------------------------------------------

class TestEnsureFfmpegOnPath:
    def test_system_binaries_skip_static_ffmpeg(self, monkeypatch):
        add_paths = Mock()
        monkeypatch.setattr(
            video_processor.shutil,
            "which",
            lambda executable: f"/system/bin/{executable}",
        )
        monkeypatch.setitem(
            sys.modules,
            "static_ffmpeg",
            types.SimpleNamespace(add_paths=add_paths),
        )

        video_processor._ensure_ffmpeg_on_path()

        add_paths.assert_not_called()

    def test_incomplete_system_pair_selects_matching_static_pair(
        self, monkeypatch, tmp_path
    ):
        from static_ffmpeg import _add_paths

        system_dir = tmp_path / "system"
        static_dir = tmp_path / "static"
        system_dir.mkdir()
        static_dir.mkdir()
        for executable in (
            system_dir / "ffmpeg", static_dir / "ffmpeg", static_dir / "ffprobe"
        ):
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        monkeypatch.setenv("PATH", str(system_dir))
        monkeypatch.setattr(
            _add_paths,
            "get_or_fetch_platform_executables_else_raise",
            lambda **kwargs: (str(static_dir / "ffmpeg"), str(static_dir / "ffprobe")),
        )
        assert shutil.which("ffmpeg") == str(system_dir / "ffmpeg")
        assert shutil.which("ffprobe") is None

        video_processor._ensure_ffmpeg_on_path()

        # Exercise the dependency's real add_paths implementation, not a mock
        # pretending that weak=True appends to PATH.
        assert shutil.which("ffmpeg") == str(static_dir / "ffmpeg")
        assert shutil.which("ffprobe") == str(static_dir / "ffprobe")

    def test_repeated_calls_do_not_reprovision_after_binaries_are_available(
        self, monkeypatch
    ):
        paths = {"ffmpeg": None, "ffprobe": None}

        def add_paths(*, weak):
            assert weak is True
            paths.update(
                ffmpeg="/static/bin/ffmpeg",
                ffprobe="/static/bin/ffprobe",
            )

        static_ffmpeg = types.SimpleNamespace(add_paths=Mock(side_effect=add_paths))
        monkeypatch.setattr(
            video_processor.shutil,
            "which",
            lambda executable: paths[executable],
        )
        monkeypatch.setitem(sys.modules, "static_ffmpeg", static_ffmpeg)

        video_processor._ensure_ffmpeg_on_path()
        video_processor._ensure_ffmpeg_on_path()

        static_ffmpeg.add_paths.assert_called_once_with(weak=True)

    def test_missing_static_ffmpeg_has_system_install_remediation(self, monkeypatch):
        monkeypatch.setattr(video_processor.shutil, "which", lambda _: None)
        original_import = builtins.__import__

        def reject_static_ffmpeg(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "static_ffmpeg":
                raise ModuleNotFoundError("static-ffmpeg is unavailable")
            return original_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", reject_static_ffmpeg)

        with pytest.raises(video_processor.VideoProcessingError) as exc_info:
            video_processor._ensure_ffmpeg_on_path()

        assert "Install system ffmpeg" in str(exc_info.value)
        assert "static-ffmpeg>=3.0" in str(exc_info.value)

    def test_static_ffmpeg_download_failure_is_not_cached(self, monkeypatch):
        add_paths = Mock(side_effect=RuntimeError("unsupported platform"))
        monkeypatch.setattr(video_processor.shutil, "which", lambda _: None)
        monkeypatch.setitem(
            sys.modules,
            "static_ffmpeg",
            types.SimpleNamespace(add_paths=add_paths),
        )

        for _ in range(2):
            with pytest.raises(video_processor.VideoProcessingError) as exc_info:
                video_processor._ensure_ffmpeg_on_path()
            assert "unsupported platform" in str(exc_info.value)

        assert add_paths.call_count == 2

    def test_missing_binary_after_static_setup_has_remediation(self, monkeypatch):
        monkeypatch.setattr(video_processor.shutil, "which", lambda _: None)
        monkeypatch.setitem(
            sys.modules,
            "static_ffmpeg",
            types.SimpleNamespace(add_paths=Mock()),
        )

        with pytest.raises(video_processor.VideoProcessingError) as exc_info:
            video_processor._ensure_ffmpeg_on_path()

        assert "ffmpeg, ffprobe not found" in str(exc_info.value)
        assert "Install system ffmpeg" in str(exc_info.value)


class TestPublicFfmpegCalls:
    def test_get_video_duration_ensures_binaries_before_running_ffprobe(
        self, tmp_path, monkeypatch
    ):
        source = tmp_path / "source.mp4"
        source.write_bytes(b"input")
        ensure = Mock()
        monkeypatch.setattr(video_processor, "_ensure_ffmpeg_on_path", ensure)
        monkeypatch.setattr(
            video_processor.subprocess,
            "run",
            Mock(return_value=SimpleNamespace(returncode=0, stdout="8.0\n", stderr="")),
        )

        assert get_video_duration(source) == 8.0

        ensure.assert_called_once_with()

    def test_process_transition_ensures_binaries_before_running_ffmpeg(
        self, tmp_path, monkeypatch
    ):
        source = tmp_path / "source.mp4"
        output = tmp_path / "output.mp4"
        source.write_bytes(b"input")
        ensure = Mock()

        def run_ffmpeg(command, **_):
            Path(command[-1]).write_bytes(b"output")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(video_processor, "_ensure_ffmpeg_on_path", ensure)
        monkeypatch.setattr(video_processor.subprocess, "run", run_ffmpeg)

        assert process_transition(
            source,
            output,
            target_duration_s=2.0,
            input_duration_s=8.0,
        ) == output

        ensure.assert_called_once_with()


# ---------------------------------------------------------------------------
# Integration test: real ffmpeg retiming
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="requires system ffmpeg and ffprobe",
)
def test_process_transition_retimes_h264_video_without_audio(tmp_path):
    source = tmp_path / "source.mp4"
    output = tmp_path / "retimed.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=160x90:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    process_transition(source, output, target_duration_s=1.2, easing="linear")

    assert get_video_duration(output) == pytest.approx(1.2, abs=0.15)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,pix_fmt",
            "-of",
            "json",
            str(output),
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    video_streams = [stream for stream in streams if stream["codec_type"] == "video"]
    assert video_streams == [
        {
            "codec_name": "h264",
            "codec_type": "video",
            "pix_fmt": "yuv420p",
        }
    ]
    assert not any(stream["codec_type"] == "audio" for stream in streams)
