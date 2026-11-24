"""Adapter for running the external ngspice solver (Lab 04).

Flask only hands validated numbers to this module.  It creates one isolated
working directory per run, invokes ngspice with a list of arguments (never a
shell command), and returns the solver's log/raw text or an explicit error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
INSTALL_DIR = Path(LOCAL_APP_DATA) / "ngspice-47" / "Spice64" / "bin"


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
