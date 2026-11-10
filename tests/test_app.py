import pytest

from app import app

VALID = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
         "re": "1000", "beta": "150", "vbe": "0.7"}


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_get_renders_all_seven_inputs(client):
    body = client.get("/").get_data(as_text=True)
    for name in VALID:
        assert f'name="{name}"' in body


def test_valid_post_shows_qpoint_with_units(client):
    response = client.post("/", data=VALID)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "1.32 mA" in body
    assert "7.76 V" in body
    assert "Active" in body


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
