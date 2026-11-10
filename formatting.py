import math

PREFIXES = (
    (1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""),
    (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"),
)


def _prefix(magnitude: float) -> tuple[float, str]:
    for factor, prefix in PREFIXES:
        if magnitude >= factor:
            return factor, prefix
    return 1e-9, "n"


def si(value: float, unit: str) -> str:
    if not math.isfinite(value):
        return "n/a"
    if value == 0:
        return f"0 {unit}"

    factor, prefix = _prefix(abs(value))
    scaled = value / factor
    # A value like 999.999 Ω would round to "1e+03 Ω"; move up one prefix
    # instead so it reads "1 kΩ".
    if abs(scaled) >= 999.5:
        for candidate, candidate_prefix in reversed(PREFIXES):
            if candidate > factor:
                factor, prefix = candidate, candidate_prefix
                scaled = value / factor
                break
    return f"{scaled:.3g} {prefix}{unit}"
