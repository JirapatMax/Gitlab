"""Tests for server-rendered SVG charts (Lab 04)."""

from pathlib import Path

import pytest

import spice_engine
from charts import bode_svg, wave_svg


FIXTURES = Path(__file__).parent / "fixtures"


def test_charts_have_labeled_axes():
    """Regression: plots come from parsed vectors and label every unit."""
    ac = spice_engine.parse_ac((FIXTURES / "ac.raw").read_text(encoding="utf-8"))
    tran = spice_engine.parse_tran((FIXTURES / "tran.raw").read_text(encoding="utf-8"))

    bode = bode_svg({"status": "success", "values": ac})
    wave = wave_svg({"status": "success", "values": tran})

    assert 'data-points="3"' in bode
    for unit in ("Hz", "dB", "deg"):
        assert unit in bode
    assert bode.count("<polyline") == 2  # gain and phase

    assert 'data-points="3"' in wave
    for label in ("s", "V", "Vin", "Vout"):
        assert label in wave
    assert wave.count("<polyline") == 2  # input and output


@pytest.mark.parametrize("chart", [bode_svg, wave_svg])
def test_charts_are_empty_on_failure(chart):
    """Regression: a failed run must never leave a stale or partial plot."""
    assert chart({"status": "error", "error": "engine unavailable"}) == ""
    assert chart({"status": "success", "values": {}}) == ""
