import pytest
from bjt_bias import BiasInputs, parse_inputs

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
