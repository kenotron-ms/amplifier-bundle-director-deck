"""
Tests for director_deck.video_processor.

Unit tests cover _build_filter_complex (pure function, no subprocess).
Integration tests (marked) require ffmpeg and a real synthetic video.
"""

import pytest
from director_deck.video_processor import (
    _build_filter_complex,
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
        assert suggest_transition_duration("hero", "bullets") == 3.0

    def test_hero_to(self):
        assert suggest_transition_duration("bullets", "hero") == 3.0

    def test_statement_from(self):
        assert suggest_transition_duration("statement", "bullets") == 1.5

    def test_statement_to(self):
        assert suggest_transition_duration("bullets", "statement") == 1.5

    def test_stat_callout_from(self):
        assert suggest_transition_duration("stat_callout", "bullets") == 2.0

    def test_stat_callout_to(self):
        assert suggest_transition_duration("bullets", "stat_callout") == 2.0

    def test_bullets_default(self):
        assert suggest_transition_duration("bullets", "bullets") == 2.5

    def test_process_flow_default(self):
        assert suggest_transition_duration("process_flow", "timeline") == 2.5

    def test_hero_wins_over_statement_from(self):
        # hero rule comes first — should be 3.0 not 1.5
        assert suggest_transition_duration("hero", "statement") == 3.0
