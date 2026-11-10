import math
from dataclasses import dataclass
from typing import Mapping

MAX_VCC = 1000.0
MAX_RESISTANCE = 1e9
MAX_BETA = 1e5

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
