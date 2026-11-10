import math
from dataclasses import dataclass
from typing import Mapping

MAX_VCC = 1000.0
MAX_RESISTANCE = 1e9
MAX_BETA = 1e5

VCE_SAT_V = 0.2
VCE_NEAR_SAT_V = 1.0

DELTA_NEGLIGIBLE_PCT = 2.0
DELTA_ACCEPTABLE_PCT = 10.0

FIELD_NAMES = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def _read_number(raw: Mapping[str, str], name: str, errors: dict[str, str]) -> float | None:
    text = (raw.get(name) or "").strip()
    if not text:
        errors[name] = "required"
        return None
    try:
        value = float(text)
    except ValueError:
        errors[name] = "must be a number"
        return None
    if not math.isfinite(value):
        errors[name] = "must be a finite number"
        return None
    return value


def parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    errors: dict[str, str] = {}
    values = {name: _read_number(raw, name, errors) for name in FIELD_NAMES}

    vcc = values["vcc"]
    if vcc is not None:
        if vcc > MAX_VCC:
            errors["vcc"] = "is above the supported maximum"
        elif vcc <= 0:
            errors["vcc"] = "must be greater than 0"

    for name in ("r1", "r2", "rc"):
        value = values[name]
        if value is None:
            continue
        if value > MAX_RESISTANCE:
            errors[name] = "is above the supported maximum"
        elif value <= 0:
            errors[name] = "must be greater than 0"

    re = values["re"]
    if re is not None:
        if re > MAX_RESISTANCE:
            errors["re"] = "is above the supported maximum"
        elif re < 0:
            errors["re"] = "must be at least 0"

    beta = values["beta"]
    if beta is not None:
        if beta > MAX_BETA:
            errors["beta"] = "is above the supported maximum"
        elif beta < 1:
            errors["beta"] = "must be at least 1"

    vbe = values["vbe"]
    if vbe is not None:
        if vbe < 0:
            errors["vbe"] = "must be at least 0"
        elif vcc is not None and "vcc" not in errors and vbe >= vcc:
            errors["vbe"] = "must be less than VCC"

    if errors:
        return None, errors
    return BiasInputs(**values), {}


@dataclass(frozen=True)
class OperatingPoint:
    vbb: float
    rb: float
    ib: float
    ic: float
    ie: float
    ve: float
    vc: float
    vce: float
    p_transistor: float
    model: str


def solve_exact(inputs: BiasInputs) -> OperatingPoint:
    vbb = inputs.vcc * inputs.r2 / (inputs.r1 + inputs.r2)
    rb = inputs.r1 * inputs.r2 / (inputs.r1 + inputs.r2)
    ib = (vbb - inputs.vbe) / (rb + (inputs.beta + 1) * inputs.re)
    ic = inputs.beta * ib
    ie = ib + ic
    ve = ie * inputs.re
    vc = inputs.vcc - ic * inputs.rc
    vce = vc - ve
    return OperatingPoint(
        vbb=vbb,
        rb=rb,
        ib=ib,
        ic=ic,
        ie=ie,
        ve=ve,
        vc=vc,
        vce=vce,
        p_transistor=vce * ic,
        model="exact",
    )


@dataclass(frozen=True)
class Message:
    severity: str
    text: str


def clamp_cutoff(inputs: BiasInputs, point: OperatingPoint) -> OperatingPoint:
    return OperatingPoint(
        vbb=point.vbb,
        rb=point.rb,
        ib=0.0,
        ic=0.0,
        ie=0.0,
        ve=0.0,
        vc=inputs.vcc,
        vce=inputs.vcc,
        p_transistor=0.0,
        model=point.model,
    )


def classify(inputs: BiasInputs, point: OperatingPoint) -> tuple[str, tuple[Message, ...]]:
    if point.vce < VCE_SAT_V:
        return "saturation", (Message(
            "error",
            "Transistor is in saturation: VCE is below VCE(sat) = 0.2 V, "
            "so the linear-region values are not valid.",
        ),)
    if point.vce < VCE_NEAR_SAT_V:
        return "near-saturation", (Message(
            "warning",
            "VCE is close to saturation; the Q-point is sensitive to beta and VBE.",
        ),)
    return "active", (Message("info", "Transistor is in the forward-active region."),)


def saturation_reference(inputs: BiasInputs, point: OperatingPoint) -> tuple[float, float]:
    ic_sat = (inputs.vcc - VCE_SAT_V) / (inputs.rc + inputs.re)
    return ic_sat, ic_sat / point.ib


COMPARISON_ROWS = (
    ("ib", "IB", "A"),
    ("ic", "IC", "A"),
    ("ie", "IE", "A"),
    ("ve", "VE", "V"),
    ("vc", "VC", "V"),
    ("vce", "VCE", "V"),
)


@dataclass(frozen=True)
class ComparisonRow:
    key: str
    label: str
    unit: str
    exact: float
    approximate: float
    delta: float
    delta_pct: float | None


def solve_approximate(inputs: BiasInputs) -> OperatingPoint | None:
    if inputs.re == 0:
        return None
    vbb = inputs.vcc * inputs.r2 / (inputs.r1 + inputs.r2)
    rb = inputs.r1 * inputs.r2 / (inputs.r1 + inputs.r2)
    ie = (vbb - inputs.vbe) / inputs.re
    ic = ie
    ib = ie / inputs.beta
    ve = ie * inputs.re
    vc = inputs.vcc - ic * inputs.rc
    vce = vc - ve
    return OperatingPoint(
        vbb=vbb,
        rb=rb,
        ib=ib,
        ic=ic,
        ie=ie,
        ve=ve,
        vc=vc,
        vce=vce,
        p_transistor=vce * ic,
        model="approximate",
    )


def comparison_verdict(max_delta_pct: float | None) -> str | None:
    if max_delta_pct is None:
        return None
    if max_delta_pct <= DELTA_NEGLIGIBLE_PCT:
        return "negligible"
    if max_delta_pct <= DELTA_ACCEPTABLE_PCT:
        return "small"
    return "large"


def compare(
    exact: OperatingPoint,
    approximate: OperatingPoint,
) -> tuple[tuple[ComparisonRow, ...], float | None, str | None]:
    rows = []
    for key, label, unit in COMPARISON_ROWS:
        exact_value = getattr(exact, key)
        approximate_value = getattr(approximate, key)
        delta = approximate_value - exact_value
        delta_pct = None if exact_value == 0 else delta / exact_value * 100
        rows.append(ComparisonRow(key, label, unit, exact_value, approximate_value, delta, delta_pct))
    magnitudes = [abs(row.delta_pct) for row in rows if row.delta_pct is not None]
    max_delta_pct = max(magnitudes) if magnitudes else None
    return tuple(rows), max_delta_pct, comparison_verdict(max_delta_pct)
