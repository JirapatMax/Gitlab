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
