import pytest
from formatting import si


@pytest.mark.parametrize("value,unit,expected", [
    (8.824501e-6, "A", "8.82 µA"),
    (1.323675e-3, "A", "1.32 mA"),
    (8245.614, "Ω", "8.25 kΩ"),
    (2.105263, "V", "2.11 V"),
    (0.0102656, "W", "10.3 mW"),
    (0.0, "A", "0 A"),
    (-0.0025, "A", "-2.5 mA"),
    (1000.0, "Ω", "1 kΩ"),
    (999.4, "Ω", "999 Ω"),
    (999.9999, "Ω", "1 kΩ"),
    (999.999e-6, "A", "1 mA"),
    (1e6, "Ω", "1 MΩ"),
    (1e-9, "A", "1 nA"),
    (1e-10, "A", "0.1 nA"),
    (float("inf"), "A", "n/a"),
    (float("nan"), "A", "n/a"),
])
def test_si(value, unit, expected):
    assert si(value, unit) == expected
