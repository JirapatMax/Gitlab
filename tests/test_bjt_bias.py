from dataclasses import replace

import pytest
from bjt_bias import (VCE_NEAR_SAT_V, VCE_SAT_V, BiasInputs, classify,
                      clamp_cutoff, parse_inputs, saturation_reference,
                      solve_exact)

VALID = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
         "re": "1000", "beta": "150", "vbe": "0.7"}


def test_parses_valid_inputs():
    inputs, errors = parse_inputs(VALID)
    assert errors == {}
    assert inputs == BiasInputs(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0,
                                re=1000.0, beta=150.0, vbe=0.7)


@pytest.mark.parametrize("field,value,message", [
    ("vcc", "0", "must be greater than 0"),
    ("vcc", "-1", "must be greater than 0"),
    ("vcc", "1001", "is above the supported maximum"),
    ("r1", "0", "must be greater than 0"),
    ("r2", "-5", "must be greater than 0"),
    ("rc", "0", "must be greater than 0"),
    ("re", "-1", "must be at least 0"),
    ("re", "0", None),
    ("beta", "0.5", "must be at least 1"),
    ("beta", "100001", "is above the supported maximum"),
    ("vbe", "-0.1", "must be at least 0"),
    ("vbe", "12", "must be less than VCC"),
    ("rc", "abc", "must be a number"),
    ("rc", "nan", "must be a finite number"),
    ("rc", "inf", "must be a finite number"),
    ("rc", "", "required"),
])
def test_field_errors(field, value, message):
    inputs, errors = parse_inputs({**VALID, field: value})
    if message is None:
        assert inputs is not None and errors == {}
    else:
        assert inputs is None
        assert errors == {field: message}


def test_missing_field_is_required():
    raw = dict(VALID)
    del raw["vbe"]
    inputs, errors = parse_inputs(raw)
    assert inputs is None
    assert errors == {"vbe": "required"}


GOLDEN = BiasInputs(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0,
                    re=1000.0, beta=150.0, vbe=0.7)
REL = 1e-6


def test_exact_matches_hand_calculation():
    p = solve_exact(GOLDEN)
    assert p.vbb == pytest.approx(2.10526315789, rel=REL)
    assert p.rb == pytest.approx(8245.61403509, rel=REL)
    assert p.ib == pytest.approx(8.82450148728e-06, rel=REL)
    assert p.ic == pytest.approx(0.00132367522309, rel=REL)
    assert p.ie == pytest.approx(0.00133249972458, rel=REL)
    assert p.ve == pytest.approx(1.33249972458, rel=REL)
    assert p.vc == pytest.approx(9.0879145092, rel=REL)
    assert p.vce == pytest.approx(7.75541478462, rel=REL)
    assert p.p_transistor == pytest.approx(0.0102656503952, rel=REL)
    assert p.model == "exact"


def test_exact_without_emitter_resistor():
    p = solve_exact(replace(GOLDEN, re=0.0))
    assert p.ib == pytest.approx(0.000170425531915, rel=REL)
    assert p.ic == pytest.approx(0.0255638297872, rel=REL)
    assert p.ve == 0.0


ACTIVE_POINT = solve_exact(GOLDEN)


def test_active():
    region, messages = classify(GOLDEN, ACTIVE_POINT)
    assert region == "active"
    assert [m.severity for m in messages] == ["info"]
    assert "forward-active" in messages[0].text


def test_saturation_when_vce_below_threshold():
    region, messages = classify(GOLDEN, replace(ACTIVE_POINT, vce=0.19))
    assert region == "saturation"
    assert [m.severity for m in messages] == ["error"]


def test_boundary_at_vce_sat_is_near_saturation():
    region, _ = classify(GOLDEN, replace(ACTIVE_POINT, vce=VCE_SAT_V))
    assert region == "near-saturation"


def test_boundary_at_vce_near_sat_is_active():
    region, _ = classify(GOLDEN, replace(ACTIVE_POINT, vce=VCE_NEAR_SAT_V))
    assert region == "active"


def test_clamp_cutoff_zeroes_currents():
    clamped = clamp_cutoff(GOLDEN, replace(ACTIVE_POINT, ib=-1e-6, ic=-1e-4, ve=-0.5, vc=13.0, vce=13.5))
    assert (clamped.ib, clamped.ic, clamped.ie, clamped.ve, clamped.p_transistor) == (0.0, 0.0, 0.0, 0.0, 0.0)
    assert clamped.vc == GOLDEN.vcc
    assert clamped.vce == GOLDEN.vcc


def test_saturation_reference():
    point = replace(ACTIVE_POINT, vce=-2.56925195549)
    ic_sat, forced_beta = saturation_reference(replace(GOLDEN, rc=10000.0), point)
    assert ic_sat == pytest.approx(0.00107272727273, rel=REL)
    assert forced_beta == pytest.approx(121.562365225, rel=REL)
