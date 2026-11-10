import pytest

from app import app

VALID = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
         "re": "1000", "beta": "150", "vbe": "0.7"}


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_get_renders_lab_dashboard(client):
    body = client.get("/").get_data(as_text=True)
    for name in VALID:
        assert f'name="{name}"' in body
    assert "Lab 02: BJT DC Bias Web App" in body
    assert "ENG29 2121" in body
    assert "Computer programming for Electrical Engineers" in body
    assert "Input Parameters" in body
    assert "Circuit: Common-Emitter Amplifier" in body
    assert "DC Bias Results" in body
    assert "Calculate DC Bias" in body
    assert "Week 2 Goal" in body
    assert "common-emitter amplifier with voltage-divider bias" in body


def test_schematic_shows_si_formatted_component_values(client):
    body = client.get("/").get_data(as_text=True)
    assert "100 kΩ" in body
    assert "22 kΩ" in body
    assert "2.2 kΩ" in body
    assert "1 kΩ" in body
    assert "β = 100" in body


def test_valid_post_shows_qpoint_with_units(client):
    response = client.post("/", data=VALID)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "1.32 mA" in body
    assert "7.76 V" in body
    assert "Active region approximation OK" in body
    assert "transistor in active region" in body
    assert "6.16" in body
    assert "81.6 µA" in body


def test_saturation_flags_approximation_inapplicable(client):
    body = client.post("/", data={**VALID, "rc": "10000"}).get_data(as_text=True)
    assert "not applicable" in body
    assert "lightly loaded" not in body
    assert "1.07 mA" in body


def test_near_saturation_flags_approximation_inapplicable(client):
    body = client.post("/", data={**VALID, "rc": "7600"}).get_data(as_text=True)
    assert "not applicable" in body
    assert "lightly loaded" not in body


def test_invalid_post_returns_400_and_keeps_input(client):
    response = client.post("/", data={**VALID, "r1": "-5"})
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "must be greater than 0" in body
    assert 'value="-5"' in body


def test_cutoff_post_warns(client):
    response = client.post("/", data={**VALID, "r1": "100000", "r2": "1000"})
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "cut off" in body
