import math

PREFIXES = (
    (1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""),
    (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"),
)


def si(value: float, unit: str) -> str:
    if not math.isfinite(value):
        return "n/a"
    if value == 0:
        return f"0 {unit}"
    magnitude = abs(value)
    factor, prefix = 1.0, ""
    for factor_candidate, prefix_candidate in PREFIXES:
        if magnitude >= factor_candidate:
            factor, prefix = factor_candidate, prefix_candidate
            break
    return f"{value / factor:.3g} {prefix}{unit}"
