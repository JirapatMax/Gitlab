"""Tests for the ngspice process adapter (Lab 04)."""

import subprocess
from pathlib import Path

import pytest

import spice_engine


def _fake_run_factory(captured):
    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        cwd = Path(kwargs["cwd"])
        (cwd / "run.log").write_text("log text", encoding="utf-8")
        (cwd / "run.raw").write_text("raw text", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="out", stderr="")
    return fake_run


def test_run_netlist_passes_batch_arguments(monkeypatch):
    """Regression: adapter must use list args, no shell, timeout, and a temp cwd."""
    captured = {}
    monkeypatch.setattr(spice_engine.subprocess, "run", _fake_run_factory(captured))

    result = spice_engine.run_netlist("* test\n.end\n", timeout=5)

    assert result.ok is True
    assert result.log == "log text"
    assert result.raw == "raw text"
    args = captured["args"]
    assert args[0] == str(spice_engine.find_ngspice())
    assert "-b" in args and "-o" in args and "-r" in args
    assert args[-1].endswith("circuit.cir")
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 5
    assert Path(captured["kwargs"]["cwd"]).exists() is False  # temp dir cleaned up


def test_run_netlist_reports_nonzero_exit(monkeypatch):
    """Regression: a failed run must never look successful."""
    def fake_run(args, **kwargs):
        cwd = Path(kwargs["cwd"])
        (cwd / "run.log").write_text("partial", encoding="utf-8")
        (cwd / "run.raw").write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="ngspice failed")

    monkeypatch.setattr(spice_engine.subprocess, "run", fake_run)

    result = spice_engine.run_netlist("* test\n.end\n")

    assert result.ok is False
    assert result.returncode == 1
    assert "ngspice failed" in result.error
    assert result.raw == ""


def test_run_netlist_reports_timeout(monkeypatch):
    """Regression: timeout becomes an error result instead of an exception."""
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(spice_engine.subprocess, "run", fake_run)

    result = spice_engine.run_netlist("* test\n.end\n", timeout=1)

    assert result.ok is False
    assert "timed out" in result.error.lower()
    assert result.raw == ""


def test_find_ngspice_honours_env_override(monkeypatch, tmp_path):
    """Regression: NGSPICE_EXE is the documented reproducibility escape hatch."""
    fake = tmp_path / "my-ngspice.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("NGSPICE_EXE", str(fake))

    assert spice_engine.find_ngspice() == fake


def test_find_ngspice_raises_when_unavailable(monkeypatch):
    """Regression: a missing engine must be reported, not guessed."""
    monkeypatch.delenv("NGSPICE_EXE", raising=False)
    monkeypatch.setattr(spice_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(spice_engine, "INSTALL_DIR", Path("C:/does-not-exist"))

    with pytest.raises(spice_engine.SpiceUnavailable):
        spice_engine.find_ngspice()


FIXTURE = {
    "vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200", "re": "1000",
    "rl": "10000", "cin": "0.00001", "cout": "0.00001",
    "amplitude": "0.01", "frequency": "1000",
}


@pytest.mark.parametrize("field,bad", [
    ("re", "0"), ("frequency", "-1"), ("amplitude", "abc"), ("vcc", "12;op"),
])
def test_validate_rejects_invalid_values(field, bad):
    """Regression: invalid form text must never reach the netlist."""
    raw = dict(FIXTURE)
    raw[field] = bad

    values, errors = spice_engine.validate_sim_inputs(raw)

    assert values is None
    assert field in errors


def test_validate_accepts_fixture():
    """Regression: the handout fixture parses into base units."""
    values, errors = spice_engine.validate_sim_inputs(FIXTURE)

    assert errors == {}
    assert values.vcc == 12.0
    assert values.r1 == 100000.0
    assert values.re == 1000.0
    assert values.cin == 0.00001
    assert values.amplitude == 0.01
    assert values.frequency == 1000.0


def test_build_netlist_includes_model_and_analysis():
    """Regression: every analysis uses the named model and a complete CE netlist."""
    values, _ = spice_engine.validate_sim_inputs(FIXTURE)

    dc = spice_engine.build_netlist(values, "dc")
    ac = spice_engine.build_netlist(values, "ac")
    tran = spice_engine.build_netlist(values, "tran")

    for netlist in (dc, ac, tran):
        assert ".model QNPN_TEACH NPN(" in netlist
        assert "Q1 collector base emitter QNPN_TEACH" in netlist
        assert "VIN in 0 DC 0 AC 1 SIN(0 0.01 1000)" in netlist
        assert "RL out 0 10k" in netlist
        assert "CIN in base 10u" in netlist
        assert "COUT collector out 10u" in netlist
    assert ".op" in dc
    assert ".ac dec 100 0.1 10Meg" in ac
    assert ".tran" in tran


def test_tran_tstop_shrinks_with_frequency():
    """Regression: transient stop time is derived from the entered frequency."""
    values, _ = spice_engine.validate_sim_inputs(FIXTURE)

    low = spice_engine.build_netlist(values, "tran")
    higher = spice_engine.build_netlist(
        spice_engine.SimInputs(**{**vars(values), "frequency": 2000.0}), "tran")

    assert ".tran 1e-05 0.005" in low
    assert ".tran 5e-06 0.0025" in higher
