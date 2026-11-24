"""Adapter for running the external ngspice solver (Lab 04).

Flask only hands validated numbers to this module.  It creates one isolated
working directory per run, invokes ngspice with a list of arguments (never a
shell command), and returns the solver's log/raw text or an explicit error.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
INSTALL_DIR = Path(LOCAL_APP_DATA) / "ngspice-47" / "Spice64" / "bin"

ANALYSES = ("dc", "ac", "tran")
MODEL_NAME = "QNPN_TEACH"
# A documented teaching model, not a claim about any specific transistor.
MODEL_CARD = (".model QNPN_TEACH NPN(IS=1E-14 BF=100 BR=0.1 VAF=100 "
              "CJE=25p CJC=5p TF=0.3n)")
SIM_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout",
              "amplitude", "frequency")
MIN_VALUE = 1e-6
MAX_RESISTANCE = 1e9
MAX_VCC = 1000.0
MAX_AMPLITUDE = 1.0
MAX_FREQUENCY = 1e6


@dataclass
class SimInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    amplitude: float
    frequency: float


def validate_sim_inputs(raw: Mapping[str, str]) -> tuple[SimInputs | None, dict[str, str]]:
    """Parse and bound every simulator field before a netlist is built."""
    errors: dict[str, str] = {}
    values: dict[str, float] = {}
    for name in SIM_FIELDS:
        text = (raw.get(name) or "").strip()
        if not text:
            errors[name] = "required"
            continue
        try:
            number = float(text)
        except ValueError:
            errors[name] = "must be a number"
            continue
        if not math.isfinite(number):
            errors[name] = "must be a finite number"
        elif number <= 0:
            errors[name] = "must be greater than 0"
        elif name in ("vcc", "amplitude", "frequency"):
            limit = {"vcc": MAX_VCC, "amplitude": MAX_AMPLITUDE,
                     "frequency": MAX_FREQUENCY}[name]
            if number > limit:
                errors[name] = f"must be at most {limit:g}"
            else:
                values[name] = number
        elif number < MIN_VALUE or number > MAX_RESISTANCE:
            errors[name] = "is outside the supported range"
        else:
            values[name] = number
    if errors:
        return None, errors
    return SimInputs(**values), {}


def build_netlist(inputs: SimInputs, analysis: str) -> str:
    """Render one CE voltage-divider circuit with a single analysis directive."""
    if analysis not in ANALYSES:
        raise ValueError(f"unknown analysis: {analysis}")

    def number(value: float) -> str:
        return f"{value:.6g}"

    def component(value: float) -> str:
        for factor, suffix in ((1e9, "g"), (1e6, "meg"), (1e3, "k"), (1.0, ""),
                               (1e-3, "m"), (1e-6, "u"), (1e-9, "n"), (1e-12, "p")):
            if abs(value) >= factor:
                return f"{value / factor:.6g}{suffix}"
        return number(value)

    lines = [
        "* CE voltage-divider amplifier - ngspice teaching model",
        MODEL_CARD,
        f"VCC vcc 0 DC {number(inputs.vcc)}",
        f"R1 vcc base {component(inputs.r1)}",
        f"R2 base 0 {component(inputs.r2)}",
        f"RC vcc collector {component(inputs.rc)}",
        f"RE emitter 0 {component(inputs.re)}",
        f"RL out 0 {component(inputs.rl)}",
        f"Q1 collector base emitter {MODEL_NAME}",
        f"CIN in base {component(inputs.cin)}",
        f"COUT collector out {component(inputs.cout)}",
        f"VIN in 0 DC 0 AC 1 SIN(0 {number(inputs.amplitude)} {number(inputs.frequency)})",
    ]
    if analysis == "dc":
        lines.append(".op")
    elif analysis == "ac":
        lines.append(".ac dec 100 0.1 10Meg")
    else:
        period = 1.0 / inputs.frequency
        lines.append(f".tran {number(period / 100)} {number(period * 5)}")
    lines.append(".end")
    return "\n".join(lines) + "\n"


class SpiceUnavailable(Exception):
    """No usable ngspice executable was found."""


class SpiceRunError(Exception):
    """ngspice ran but its output could not be used."""


@dataclass
class RunResult:
    ok: bool
    log: str = ""
    raw: str = ""
    error: str = ""
    returncode: int | None = None
    log_path: Path | None = None
    raw_path: Path | None = None


def find_ngspice() -> Path:
    """Resolve the engine from NGSPICE_EXE, PATH, or the documented install dir."""
    override = os.environ.get("NGSPICE_EXE")
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
        raise SpiceUnavailable(f"NGSPICE_EXE does not exist: {override}")

    on_path = shutil.which("ngspice")
    if on_path:
        return Path(on_path)

    candidate = INSTALL_DIR / "ngspice.exe"
    if candidate.is_file():
        return candidate
    raise SpiceUnavailable("ngspice not found; install ngspice 47 or set NGSPICE_EXE")


def run_netlist(netlist: str, *, timeout: float = 20.0) -> RunResult:
    """Run one netlist in a fresh temporary directory and read its outputs."""
    try:
        executable = find_ngspice()
    except SpiceUnavailable as exc:
        return RunResult(ok=False, error=str(exc))

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        circuit = work / "circuit.cir"
        log = work / "run.log"
        raw = work / "run.raw"
        circuit.write_text(netlist, encoding="utf-8")
        args = [str(executable), "-b", "-o", str(log), "-r", str(raw), str(circuit)]
        try:
            process = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout,
                cwd=work, shell=False,
            )
        except subprocess.TimeoutExpired:
            return RunResult(ok=False, error=f"ngspice timed out after {timeout:g}s")
        except OSError as exc:
            return RunResult(ok=False, error=f"could not start ngspice: {exc}")

        log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        raw_text = raw.read_text(encoding="utf-8", errors="replace") if raw.exists() else ""
        common = dict(log=log_text, raw=raw_text, returncode=process.returncode,
                      log_path=log, raw_path=raw)
        if process.returncode != 0:
            detail = (process.stderr or process.stdout or "").strip()
            return RunResult(ok=False, error=detail or f"ngspice exited with {process.returncode}", **common)
        return RunResult(ok=True, **common)


def _header(lines: list[str], key: str) -> str:
    """Read one `Key: value` line from an ASCII raw header."""
    for line in lines:
        name, separator, value = line.partition(":")
        if separator and name.strip().lower() == key.lower():
            return value.strip()
    raise SpiceRunError(f"raw file has no {key!r} header")


def parse_raw(raw: str) -> dict:
    """Decode the ASCII raw vector format written by ngspice 47."""
    lines = raw.splitlines()
    if not lines:
        raise SpiceRunError("raw output is empty")
    plotname = _header(lines, "Plotname")
    complex_plot = "complex" in _header(lines, "Flags").lower()
    try:
        count = int(_header(lines, "No. Points").split()[0])
        variable_count = int(_header(lines, "No. Variables").split()[0])
    except (ValueError, IndexError) as exc:
        raise SpiceRunError("raw file has invalid point counts") from exc
    if count <= 0 or variable_count <= 0:
        raise SpiceRunError("raw file contains no vectors")

    try:
        variables_start = next(i for i, line in enumerate(lines)
                               if line.strip().lower() == "variables:")
        values_start = next(i for i, line in enumerate(lines)
                            if line.strip().lower() == "values:")
    except StopIteration as exc:
        raise SpiceRunError("raw file is missing Variables or Values") from exc

    variables: list[str] = []
    for line in lines[variables_start + 1:values_start]:
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit():
            variables.append(parts[1])

    tokens: list[str] = []
    for line in lines[values_start + 1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0].isdigit():
            parts = parts[1:]
        tokens.extend(parts)

    expected = count * variable_count
    if len(variables) != variable_count or len(tokens) < expected:
        raise SpiceRunError("raw file is truncated or has inconsistent vector counts")

    points: list[list[float | complex]] = []
    cursor = 0
    for _ in range(count):
        row: list[float | complex] = []
        for _ in range(variable_count):
            token = tokens[cursor]
            cursor += 1
            try:
                if complex_plot:
                    if "," in token:
                        real_text, imag_text = token.split(",", 1)
                        number: float | complex = complex(float(real_text), float(imag_text))
                    else:  # tolerate split real/imag tokens from other raw variants
                        real_text, imag_text = token, tokens[cursor]
                        cursor += 1
                        number = complex(float(real_text), float(imag_text))
                else:
                    number = float(token)
            except ValueError as exc:
                raise SpiceRunError(f"raw file has a non-numeric value: {token!r}") from exc
            values = (number.real, number.imag) if isinstance(number, complex) else (number,)
            if not all(math.isfinite(value) for value in values):
                raise SpiceRunError("raw file contains a non-finite value")
            row.append(number)
        points.append(row)

    command = ""
    for line in lines:
        if line.lower().startswith("command:"):
            command = line.partition(":")[2].strip()
            break
    return {
        "plotname": plotname,
        "variables": variables,
        "points": points,
        "count": count,
        "command": command,
    }


def _vector(parsed: dict, name: str) -> list[float | complex]:
    """Return one named raw vector, preserving point order."""
    target = name.lower()
    for index, variable in enumerate(parsed["variables"]):
        if variable.lower() == target:
            return [point[index] for point in parsed["points"]]
    raise SpiceRunError(f"raw file is missing vector {name}")


def parse_op(raw: str, *, rc: float) -> dict:
    """Decode the operating point into volts and amps with explicit units."""
    if rc <= 0:
        raise SpiceRunError("RC must be positive for IC derivation")
    parsed = parse_raw(raw)
    vcc = float(_vector(parsed, "v(vcc)")[0])
    vb = float(_vector(parsed, "v(base)")[0])
    ve = float(_vector(parsed, "v(emitter)")[0])
    vc = float(_vector(parsed, "v(collector)")[0])
    return {
        "vcc_v": vcc,
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vbe_v": vb - ve,
        "vce_v": vc - ve,
        "ic_a": (vcc - vc) / rc,
    }


def _wrapped_degrees(value: float) -> float:
    """Wrap a phase difference into (-180, 180]."""
    wrapped = (value + 180.0) % 360.0 - 180.0
    return wrapped + 360.0 if wrapped <= -180.0 else wrapped


def _crossing_between(first: dict, second: dict, threshold: float) -> float | None:
    """Log-interpolate one adjacent pair crossing the gain threshold."""
    a, b = first["gain_db"], second["gain_db"]
    if a == b or (a - threshold) * (b - threshold) > 0:
        return None
    f1, f2 = first["frequency_hz"], second["frequency_hz"]
    if f1 <= 0 or f2 <= 0:
        return None
    fraction = (threshold - a) / (b - a)
    return 10 ** (math.log10(f1) + fraction * (math.log10(f2) - math.log10(f1)))


def parse_ac(raw: str) -> dict:
    """Decode AC vectors into Hz/dB/deg and report only real -3 dB crossings."""
    parsed = parse_raw(raw)
    frequencies = _vector(parsed, "frequency")
    vin = _vector(parsed, "v(in)")
    vout = _vector(parsed, "v(out)")
    points: list[dict] = []
    for f, source, output in zip(frequencies, vin, vout, strict=True):
        source = complex(source)
        output = complex(output)
        if abs(source) == 0:
            raise SpiceRunError("AC input vector is zero; gain is undefined")
        gain_db = 20.0 * math.log10(abs(output) / abs(source))
        phase = math.degrees(math.atan2(output.imag, output.real)
                             - math.atan2(source.imag, source.real))
        points.append({
            "frequency_hz": float(f.real) if isinstance(f, complex) else float(f),
            "gain_db": gain_db,
            "phase_deg": _wrapped_degrees(phase),
        })
    if not points:
        raise SpiceRunError("AC analysis returned no points")

    peak_index = max(range(len(points)), key=lambda i: points[i]["gain_db"])
    threshold = points[peak_index]["gain_db"] - 3.0
    lower = "not determined in sweep range"
    for i in range(peak_index - 1, -1, -1):
        candidate = _crossing_between(points[i], points[i + 1], threshold)
        if candidate is not None:
            lower = candidate
            break
    upper = "not determined in sweep range"
    for i in range(peak_index, len(points) - 1):
        candidate = _crossing_between(points[i], points[i + 1], threshold)
        if candidate is not None:
            upper = candidate
            break
    return {
        "points": points,
        "peak_gain_db": points[peak_index]["gain_db"],
        "reference_gain_db": points[peak_index]["gain_db"],
        "f_low_hz": lower,
        "f_high_hz": upper,
    }


def parse_tran(raw: str) -> dict:
    """Decode transient vectors into seconds and volts."""
    parsed = parse_raw(raw)
    times = _vector(parsed, "time")
    vin = _vector(parsed, "v(in)")
    vout = _vector(parsed, "v(out)")
    points = [
        {
            "time_s": float(t),
            "vin_v": float(source),
            "vout_v": float(output),
        }
        for t, source, output in zip(times, vin, vout, strict=True)
    ]
    if not points:
        raise SpiceRunError("transient analysis returned no points")
    return {
        "points": points,
        "time_stop_s": points[-1]["time_s"],
        "vin_peak_v": max(abs(point["vin_v"]) for point in points),
        "vout_peak_v": max(abs(point["vout_v"]) for point in points),
    }


def simulate(raw: Mapping[str, str], analysis: str) -> dict:
    """Validate, run ngspice, and parse one analysis into unit-bearing data."""
    base = {"engine": "ngspice", "model": MODEL_NAME, "analysis": analysis}
    values, errors = validate_sim_inputs(raw)
    if errors:
        return {**base, "status": "error", "error": "invalid simulator input",
                "field_errors": errors}
    if analysis not in ANALYSES:
        return {**base, "status": "error", "error": f"unknown analysis: {analysis}",
                "field_errors": {}}

    netlist = build_netlist(values, analysis)
    run = run_netlist(netlist)
    if not run.ok:
        return {**base, "status": "error", "error": run.error or "ngspice run failed"}
    if not run.raw.strip():
        return {**base, "status": "error", "error": "ngspice produced no raw output"}

    try:
        if analysis == "dc":
            parsed_values: dict = parse_op(run.raw, rc=values.rc)
        elif analysis == "ac":
            parsed_values = parse_ac(run.raw)
        else:
            parsed_values = parse_tran(run.raw)
    except (SpiceRunError, ValueError, TypeError, KeyError, IndexError,
            ZeroDivisionError, OverflowError) as exc:
        return {**base, "status": "error", "error": f"could not parse ngspice output: {exc}"}

    version = ""
    for line in run.raw.splitlines():
        if line.lower().startswith("command:"):
            version = line.partition(":")[2].strip()
            break
    return {
        **base,
        "status": "success",
        "engine_version": version or "ngspice (version unknown)",
        "values": parsed_values,
    }
