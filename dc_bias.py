"""DC operating-point equations for the three NPN common-emitter bias circuits.

Lab 03 extends the Lab 02 voltage-divider app with Fixed Bias and single-supply
Emitter Bias.  Every public ``solve_*`` function takes floats in base units
(volts and ohms) and returns a plain dict with the *same keys and units* so
Flask can render all three modes through one results table:

    vb_v, ve_v, vc_v, vce_v   volts
    ib_a, ic_a, ie_a          amperes
    ib_ua, ic_ma, ie_ma       microamps / milliamps (display convenience)
    region                    "active", "near-saturation", "saturation",
                              "cut-off"
    warnings                  tuple[str, ...]  (empty in the active region)
    rb_ohm                    physical base resistor, or None for divider
    vbb_v, rth_ohm            Thevenin source/resistance, divider only
    ic_sat_a, forced_beta     saturation reference, divider only

The divider function delegates to :func:`bjt_bias.solve` so the Lab 02 numbers
(and its region classification) cannot drift.  Fixed and Emitter implement the
equations from the lab sheet directly.  This module never imports Flask.
"""

import math
from dataclasses import asdict
from typing import Mapping

from bjt_bias import (
    MAX_BETA,
    MAX_RESISTANCE,
    MAX_VCC,
    MIN_RESISTANCE,
    VCE_NEAR_SAT_V,
    VCE_SAT_V,
    BiasInputs,
    parse_inputs,
    solve,
)
from formatting import si

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

LABELS = {
    MODE_DIVIDER: "Voltage Divider Bias",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias (single supply)",
}

SHARED_FIELDS = ("vcc", "rc", "beta", "vbe")
MODE_FIELDS = {
    MODE_DIVIDER: ("r1", "r2", "re"),
    MODE_FIXED: ("rb",),
    MODE_EMITTER: ("rb", "re"),
}

# Human-readable equation used by each mode, shown under the circuit card.
EQUATIONS = {
    MODE_DIVIDER: "IB = (VTH − VBE) / [RTH + (β + 1)·RE]",
    MODE_FIXED: "IB = (VCC − VBE) / RB",
    MODE_EMITTER: "IB = (VCC − VBE) / [RB + (β + 1)·RE]",
}


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


def _check_positive(value: float | None, name: str, errors: dict[str, str], *,
                    allow_zero: bool = False) -> None:
    if value is None:
        return
    if value > MAX_RESISTANCE:
        errors[name] = "is above the supported maximum"
    elif (value < 0 if allow_zero else value <= 0):
        errors[name] = "must be at least 0" if allow_zero else "must be greater than 0"
    elif 0 < value < MIN_RESISTANCE:
        errors[name] = "is below the supported minimum"


def parse_mode_inputs(mode: str, raw: Mapping[str, str]) -> tuple[dict[str, float] | None, dict[str, str]]:
    """Validate only the fields the selected circuit actually needs.

    Resistances are returned in ohms, voltages in volts.  The divider keeps
    the exact Lab 02 validation path; the two new modes use the same limits
    and error wording on their own field sets.
    """
    if mode not in MODES:
        return None, {"mode": "unknown bias circuit"}

    if mode == MODE_DIVIDER:
        inputs, errors = parse_inputs(raw)
        if inputs is None:
            return None, errors
        return asdict(inputs), {}

    errors: dict[str, str] = {}
    fields = SHARED_FIELDS + MODE_FIELDS[mode]
    values = {name: _read_number(raw, name, errors) for name in fields}

    vcc = values["vcc"]
    if vcc is not None:
        if vcc > MAX_VCC:
            errors["vcc"] = "is above the supported maximum"
        elif vcc <= 0:
            errors["vcc"] = "must be greater than 0"

    _check_positive(values["rc"], "rc", errors)

    for name in MODE_FIELDS[mode]:
        _check_positive(values[name], name, errors, allow_zero=(name == "re"))

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
    return values, {}


def _finish(mode: str, *, vcc: float, rc: float, beta: float, vbe: float,
            ib: float, re: float, rb_ohm: float | None = None,
            vbb_v: float | None = None, rth_ohm: float | None = None) -> dict:
    """Build the shared result dict from a solved base current."""
    ic = beta * ib
    ie = ib + ic
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if ib <= 0:
        region = "cut-off"
        warnings = ("Forward-active model may not apply: IB is not positive, "
                    "so the transistor is cut off.",)
    elif vce <= VCE_SAT_V:
        region = "saturation"
        warnings = (f"Forward-active model may not apply: VCE = {si(vce, 'V')} "
                    f"is not above VCE(sat) = 0.2 V.",)
    elif vce < VCE_NEAR_SAT_V:
        region = "near-saturation"
        warnings = (f"VCE = {si(vce, 'V')} is close to saturation; the Q-point "
                    "is sensitive to β and VBE.",)
    else:
        region = "active"
        warnings = ()

    return {
        "mode": mode,
        "vb_v": vb, "ve_v": ve, "vc_v": vc, "vce_v": vce,
        "ib_a": ib, "ic_a": ic, "ie_a": ie,
        "ib_ua": ib * 1e6, "ic_ma": ic * 1e3, "ie_ma": ie * 1e3,
        "region": region,
        "warnings": warnings,
        "rb_ohm": rb_ohm,
        "vbb_v": vbb_v,
        "rth_ohm": rth_ohm,
        "ic_sat_a": None,
        "forced_beta": None,
    }


def solve_fixed(*, vcc: float, rb: float, rc: float, beta: float, vbe: float) -> dict:
    """Fixed bias: RB from VCC to the base, emitter tied straight to ground.

        IB = (VCC − VBE) / RB
    """
    ib = (vcc - vbe) / rb
    return _finish(MODE_FIXED, vcc=vcc, rc=rc, beta=beta, vbe=vbe, ib=ib,
                   re=0.0, rb_ohm=rb)


def solve_emitter(*, vcc: float, rb: float, re: float, rc: float,
                  beta: float, vbe: float) -> dict:
    """Single-supply emitter bias: RB from VCC to base, RE from emitter to ground.

        IB = (VCC − VBE) / [RB + (β + 1)·RE]
    """
    ib = (vcc - vbe) / (rb + (beta + 1) * re)
    return _finish(MODE_EMITTER, vcc=vcc, rc=rc, beta=beta, vbe=vbe, ib=ib,
                   re=re, rb_ohm=rb)


def solve_divider(*, vcc: float, r1: float, r2: float, re: float, rc: float,
                  beta: float, vbe: float, solution=None) -> dict:
    """Voltage-divider bias, reusing the unchanged Lab 02 solver.

        VTH = VCC·R2/(R1+R2)   RTH = R1·R2/(R1+R2)
        IB  = (VTH − VBE) / [RTH + (β + 1)·RE]

    ``solution`` may be passed by the route so the comparison table does not
    have to solve the circuit twice.
    """
    if solution is None:
        solution = solve(BiasInputs(vcc=vcc, r1=r1, r2=r2, rc=rc, re=re,
                                    beta=beta, vbe=vbe))
    point = solution.exact
    result = _finish(MODE_DIVIDER, vcc=vcc, rc=rc, beta=beta, vbe=vbe,
                     ib=point.ib, re=re, vbb_v=point.vbb, rth_ohm=point.rb)
    # Keep the Lab 02 region, messages and saturation reference verbatim.
    result["region"] = solution.region
    result["warnings"] = tuple(message.text for message in solution.messages)
    result["ic_sat_a"] = solution.ic_sat
    result["forced_beta"] = solution.forced_beta
    return result
