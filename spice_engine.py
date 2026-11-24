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
