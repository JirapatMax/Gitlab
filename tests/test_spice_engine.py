"""Tests for the ngspice process adapter (Lab 04)."""

import math
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


FIXTURES = Path(__file__).parent / "fixtures"


def test_fixtures_come_from_real_ngspice_capture():
    """Regression: parser fixtures are trimmed real ngspice 47 output, not invented."""
    for name in ("op.raw", "ac.raw", "tran.raw"):
        text = (FIXTURES / name).read_text(encoding="utf-8")

        assert "Command: ngspice-47" in text
        assert "hand-checked fixture" not in text


def test_parse_op_reads_node_voltages():
    """Regression: DC values come from trimmed real ngspice raw vectors."""
    raw = (FIXTURES / "op.raw").read_text(encoding="utf-8")

    point = spice_engine.parse_op(raw, rc=2200.0)

    assert point["vb_v"] == pytest.approx(1.949112054780261)
    assert point["ve_v"] == pytest.approx(1.289453695545207)
    assert point["vc_v"] == pytest.approx(9.189410178900651)
    assert point["vce_v"] == pytest.approx(7.899956483355444)
    assert point["ic_a"] == pytest.approx(0.0012775408277724313)


def test_parse_ac_and_transient_units():
    """Regression: AC points carry Hz/dB/deg and transient points carry s/V."""
    ac = spice_engine.parse_ac((FIXTURES / "ac.raw").read_text(encoding="utf-8"))
    tran = spice_engine.parse_tran((FIXTURES / "tran.raw").read_text(encoding="utf-8"))

    assert len(ac["points"]) == 10
    assert ac["points"][0]["frequency_hz"] == pytest.approx(0.1)
    assert ac["points"][5]["frequency_hz"] == pytest.approx(9772.372209557949)
    assert ac["points"][5]["gain_db"] == pytest.approx(4.859794450887965)
    assert ac["points"][5]["phase_deg"] == pytest.approx(179.98704598947484)
    assert ac["peak_gain_db"] == pytest.approx(4.859794450887965)
    assert ac["f_low_hz"] == pytest.approx(4.053357996056244)

    assert len(tran["points"]) == 9
    assert tran["points"][0]["time_s"] == 0.0
    assert tran["points"][4]["time_s"] == pytest.approx(0.0007528000000000013)
    assert tran["points"][4]["vin_v"] == pytest.approx(-0.009998452485944885)
    assert tran["points"][4]["vout_v"] == pytest.approx(0.01751030854659952)
    assert tran["time_stop_s"] == pytest.approx(0.005)
    assert tran["vin_peak_v"] == pytest.approx(0.009998452485944912)
    assert tran["vout_peak_v"] == pytest.approx(0.01751030854659952)


NO_CROSS_RAW = """Title: fixture
Plotname: AC Analysis
Flags: complex
No. Variables: 3
No. Points: 2
Variables:
\t0\tfrequency\tfrequency\tgrid=3
\t1\tv(out)\tvoltage
\t2\tv(in)\tvoltage
Values:
0\t\t1.000000000000000e+01,0.000000000000000e+00
\t1.000000000000000e+02,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
1\t\t1.000000000000000e+03,0.000000000000000e+00
\t1.000000000000000e+02,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
"""


def test_parse_ac_without_crossing_reports_not_determined():
    """Regression: no fabricated cutoff frequency when the sweep has no -3 dB point."""
    result = spice_engine.parse_ac(NO_CROSS_RAW)

    assert result["f_low_hz"] == "not determined in sweep range"
    assert result["f_high_hz"] == "not determined in sweep range"


def test_simulate_error_paths(monkeypatch):
    """Regression: engine failure and invalid input never return a success result."""
    monkeypatch.setattr(
        spice_engine, "run_netlist",
        lambda netlist: spice_engine.RunResult(ok=False, error="engine unavailable"),
    )

    failed = spice_engine.simulate(FIXTURE, "dc")
    invalid = spice_engine.simulate({**FIXTURE, "re": "0"}, "dc")

    assert failed["status"] == "error"
    assert "engine unavailable" in failed["error"]
    assert "values" not in failed
    assert invalid["status"] == "error"
    assert "re" in invalid["field_errors"]


def test_simulate_reports_unexpected_parse_type_as_error(monkeypatch):
    """Regression: corrupt raw data cannot raise an uncaught TypeError to Flask."""
    monkeypatch.setattr(spice_engine, "parse_tran", lambda raw: (_ for _ in ()).throw(
        TypeError("bad complex vector")))

    result = spice_engine.simulate(FIXTURE, "tran")

    assert result["status"] == "error"
    assert "could not parse ngspice output" in result["error"]


def test_simulate_uses_real_ac_capture(monkeypatch):
    """Regression: simulate() handles the real ngspice AC raw format end to end."""
    ac_raw = (FIXTURES / "ac.raw").read_text(encoding="utf-8")
    monkeypatch.setattr(
        spice_engine, "run_netlist",
        lambda netlist: spice_engine.RunResult(ok=True, raw=ac_raw),
    )

    result = spice_engine.simulate(FIXTURE, "ac")

    assert result["status"] == "success"
    assert result["analysis"] == "ac"
    assert len(result["values"]["points"]) == 10
    assert result["values"]["peak_gain_db"] == pytest.approx(4.859794450887965)
    assert all(
        math.isfinite(point["frequency_hz"])
        and math.isfinite(point["gain_db"])
        and math.isfinite(point["phase_deg"])
        for point in result["values"]["points"]
    )


def test_simulate_changes_with_input():
    """Regression: changing RE or source frequency changes the real simulation output."""
    base_dc = spice_engine.simulate(FIXTURE, "dc")
    changed_dc = spice_engine.simulate({**FIXTURE, "re": "2000"}, "dc")
    base_tran = spice_engine.simulate(FIXTURE, "tran")
    fast_tran = spice_engine.simulate({**FIXTURE, "frequency": "2000"}, "tran")

    assert base_dc["status"] == changed_dc["status"] == "success"
    assert base_tran["status"] == fast_tran["status"] == "success"
    assert base_dc["values"]["ic_a"] != changed_dc["values"]["ic_a"]
    assert base_tran["values"]["time_stop_s"] != fast_tran["values"]["time_stop_s"]
