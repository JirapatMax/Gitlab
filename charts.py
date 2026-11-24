"""Server-rendered SVG charts drawn only from parsed ngspice vectors.

No plot data is invented here: every point comes from ``spice_engine.parse_*``,
and a failed or empty result renders no SVG at all.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from formatting import si

WIDTH = 640
HEIGHT = 320
LEFT = 58
RIGHT = 58
TOP = 18
BOTTOM = 44
PLOT_W = WIDTH - LEFT - RIGHT
PLOT_H = HEIGHT - TOP - BOTTOM


def _usable_points(result: Mapping) -> list[dict] | None:
    if result.get("status") != "success":
        return None
    values = result.get("values")
    if not isinstance(values, Mapping):
        return None
    points = values.get("points")
    if not points:
        return None
    return points


def _svg_open(css_class: str, label: str, count: int) -> list[str]:
    return [
        f'<svg class="chart {css_class}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'role="img" aria-label="{label}" data-points="{count}">',
        f'<title>{label}</title>',
    ]


def _frame() -> list[str]:
    return [
        f'<rect class="chart-bg" x="{LEFT}" y="{TOP}" width="{PLOT_W}" '
        f'height="{PLOT_H}" rx="4"/>',
        *(f'<line class="grid-line" x1="{LEFT}" y1="{TOP + i * PLOT_H / 4:.2f}" '
          f'x2="{LEFT + PLOT_W}" y2="{TOP + i * PLOT_H / 4:.2f}"/>'
          for i in range(5)),
        f'<line class="axis" x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{TOP + PLOT_H}"/>',
        f'<line class="axis" x1="{LEFT}" y1="{TOP + PLOT_H}" '
        f'x2="{LEFT + PLOT_W}" y2="{TOP + PLOT_H}"/>',
    ]


def _polyline(points: list[tuple[float, float]], css_class: str) -> str:
    coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline class="series {css_class}" points="{coords}"/>'


def bode_svg(result: Mapping) -> str:
    """Render gain (dB) and phase (deg) against log frequency (Hz)."""
    parsed = _usable_points(result)
    if parsed is None:
        return ""
    triples: list[tuple[float, float, float]] = []
    for point in parsed:
        try:
            frequency = float(point["frequency_hz"])
            gain = float(point["gain_db"])
            phase = float(point["phase_deg"])
        except (KeyError, TypeError, ValueError):
            return ""
        if frequency <= 0 or not all(map(math.isfinite, (frequency, gain, phase))):
            return ""
        triples.append((frequency, gain, phase))
    if len(triples) < 2:
        return ""

    log_min = math.log10(triples[0][0])
    log_max = math.log10(triples[0][0])
    for frequency, _, _ in triples:
        log_min = min(log_min, math.log10(frequency))
        log_max = max(log_max, math.log10(frequency))
    if log_max <= log_min:
        return ""

    gains = [gain for _, gain, _ in triples]
    gain_min, gain_max = min(gains), max(gains)
    if gain_max - gain_min < 1.0:
        middle = (gain_max + gain_min) / 2.0
        gain_min, gain_max = middle - 0.5, middle + 0.5
    gain_pad = (gain_max - gain_min) * 0.08
    gain_min -= gain_pad
    gain_max += gain_pad

    def x(frequency: float) -> float:
        return LEFT + (math.log10(frequency) - log_min) / (log_max - log_min) * PLOT_W

    def y_gain(gain: float) -> float:
        return TOP + (gain_max - gain) / (gain_max - gain_min) * PLOT_H

    def y_phase(phase: float) -> float:
        return TOP + (180.0 - max(-180.0, min(180.0, phase))) / 360.0 * PLOT_H

    parts = _svg_open(
        "bode", "Bode plot: gain in dB and phase in deg versus frequency in Hz",
        len(triples),
    )
    parts.extend(_frame())
    parts.append(
        f'<text class="axis-title" x="{LEFT}" y="{TOP - 6}">Gain (dB)</text>'
    )
    parts.append(
        f'<text class="axis-title right" x="{LEFT + PLOT_W}" y="{TOP - 6}" '
        f'text-anchor="end">Phase (deg)</text>'
    )
    parts.append(
        f'<text class="axis-title" x="{LEFT + PLOT_W / 2:.2f}" y="{HEIGHT - 8}" '
        f'text-anchor="middle">Frequency (Hz)</text>'
    )
    for i in range(4):
        frequency = 10 ** (log_min + i * (log_max - log_min) / 3.0)
        parts.append(
            f'<text class="tick" x="{x(frequency):.2f}" y="{TOP + PLOT_H + 16}" '
            f'text-anchor="middle">{si(frequency, "Hz")}</text>'
        )
        value = gain_max - i * (gain_max - gain_min) / 4.0
        parts.append(
            f'<text class="tick" x="{LEFT - 7}" y="{TOP + i * PLOT_H / 4 + 4:.2f}" '
            f'text-anchor="end">{value:.1f}</text>'
        )
        parts.append(
            f'<text class="tick phase" x="{LEFT + PLOT_W + 7}" '
            f'y="{TOP + i * PLOT_H / 4 + 4:.2f}">{180 - i * 90}°</text>'
        )
    parts.append(_polyline([(x(f), y_gain(g)) for f, g, _ in triples], "gain"))
    parts.append(_polyline([(x(f), y_phase(p)) for f, _, p in triples], "phase"))
    parts.append(
        f'<text class="legend gain" x="{LEFT + 12}" y="{TOP + 16}">Gain (dB)</text>'
        f'<text class="legend phase" x="{LEFT + 105}" y="{TOP + 16}">Phase (deg)</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def wave_svg(result: Mapping) -> str:
    """Render Vin and Vout (V) against time (s) from transient vectors."""
    parsed = _usable_points(result)
    if parsed is None:
        return ""
    triples: list[tuple[float, float, float]] = []
    for point in parsed:
        try:
            time = float(point["time_s"])
            vin = float(point["vin_v"])
            vout = float(point["vout_v"])
        except (KeyError, TypeError, ValueError):
            return ""
        if not all(map(math.isfinite, (time, vin, vout))):
            return ""
        triples.append((time, vin, vout))
    if len(triples) < 2:
        return ""

    time_min, time_max = triples[0][0], triples[0][0]
    volts = [value for _, vin, vout in triples for value in (vin, vout)]
    volt_min, volt_max = min(volts), max(volts)
    for time, _, _ in triples:
        time_min = min(time_min, time)
        time_max = max(time_max, time)
    if time_max <= time_min:
        return ""
    if volt_max - volt_min < 1e-9:
        volt_min -= 1e-3
        volt_max += 1e-3
    volt_pad = (volt_max - volt_min) * 0.08
    volt_min -= volt_pad
    volt_max += volt_pad

    def x(time: float) -> float:
        return LEFT + (time - time_min) / (time_max - time_min) * PLOT_W

    def y(voltage: float) -> float:
        return TOP + (volt_max - voltage) / (volt_max - volt_min) * PLOT_H

    parts = _svg_open(
        "wave", "Transient waveform: Vin and Vout in volts versus time in seconds",
        len(triples),
    )
    parts.extend(_frame())
    parts.append(
        f'<text class="axis-title" x="{LEFT}" y="{TOP - 6}">Voltage (V)</text>'
    )
    parts.append(
        f'<text class="axis-title" x="{LEFT + PLOT_W / 2:.2f}" y="{HEIGHT - 8}" '
        f'text-anchor="middle">Time (s)</text>'
    )
    for i in range(4):
        time = time_min + i * (time_max - time_min) / 3.0
        parts.append(
            f'<text class="tick" x="{x(time):.2f}" y="{TOP + PLOT_H + 16}" '
            f'text-anchor="middle">{si(time, "s")}</text>'
        )
        voltage = volt_max - i * (volt_max - volt_min) / 4.0
        parts.append(
            f'<text class="tick" x="{LEFT - 7}" y="{TOP + i * PLOT_H / 4 + 4:.2f}" '
            f'text-anchor="end">{si(voltage, "V")}</text>'
        )
    parts.append(_polyline([(x(t), y(v)) for t, v, _ in triples], "vin"))
    parts.append(_polyline([(x(t), y(v)) for t, _, v in triples], "vout"))
    parts.append(
        f'<text class="legend vin" x="{LEFT + 12}" y="{TOP + 16}">Vin</text>'
        f'<text class="legend vout" x="{LEFT + 62}" y="{TOP + 16}">Vout</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
