"""Tests for the separate /simulator route (Lab 04)."""

import pytest

import app as app_module
import spice_engine
from app import app


FIXTURE = {
    "vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200", "re": "1000",
    "rl": "10000", "cin": "0.00001", "cout": "0.00001",
    "amplitude": "0.01", "frequency": "1000",
}


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_get_simulator_shows_defaults_without_chart(client):
    """Regression: the first page has real fixture defaults and no fake plot."""
    body = client.get("/simulator").get_data(as_text=True)

    assert "CE Amplifier Simulator" in body
    assert "QNPN_TEACH" in body
    for name in spice_engine.SIM_FIELDS:
        assert f'name="{name}"' in body
    assert '<svg class="chart' not in body
    assert "Not run yet" in body


def test_analysis_selector_form_carries_current_parameters(client):
    """Regression: selecting analysis alone must submit every current field."""
    body = client.get("/simulator").get_data(as_text=True)
    top_form = body.split("</form>", 1)[0]

    for name in spice_engine.SIM_FIELDS:
        assert f'type="hidden" name="{name}"' in top_form


def test_invalid_input_returns_400_without_chart(client):
    """Regression: RE=0 is rejected before ngspice starts and no chart survives."""
    response = client.post("/simulator", data={**FIXTURE, "analysis": "dc", "re": "0"})
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "must be greater than 0" in body
    assert 'value="0"' in body
    assert '<svg class="chart' not in body


def test_engine_error_shows_error_status(monkeypatch, client):
    """Regression: solver failure is visible and never shows a success plot."""
    def fake_simulate(raw, analysis):
        return {
            "status": "error", "engine": "ngspice", "model": spice_engine.MODEL_NAME,
            "analysis": analysis, "error": "engine unavailable",
        }

    monkeypatch.setattr(app_module.spice_engine, "simulate", fake_simulate)

    response = client.post("/simulator", data={**FIXTURE, "analysis": "dc"})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Error" in body
    assert "engine unavailable" in body
    assert '<svg class="chart' not in body


def test_dc_success_separates_spice_from_analytical(client):
    """Regression: real SPICE numbers and Lab 3 analytical numbers are labelled."""
    response = client.post("/simulator", data={**FIXTURE, "analysis": "dc"})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Success" in body
    assert "ngspice" in body
    assert "Analytical (Lab 3)" in body
    assert "IC" in body


def test_lab3_routes_unchanged(client):
    """Regression: the original A1-A5 DC route still renders its known values."""
    valid = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
             "re": "1000", "beta": "150", "vbe": "0.7"}
    response = client.post("/", data=valid)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for expected in ("1.32 mA", "7.76 V", "Active region approximation OK",
                     "81.6 µA"):
        assert expected in body
