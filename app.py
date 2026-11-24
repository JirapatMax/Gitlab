from flask import Flask, render_template, request

import spice_engine
from bjt_bias import BiasInputs, solve as solve_reference
from dc_bias import (
    EQUATIONS,
    LABELS,
    MODES,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIXED,
    parse_mode_inputs,
    solve_divider,
    solve_emitter,
    solve_fixed,
)
from charts import bode_svg, wave_svg
from formatting import si

app = Flask(__name__)

DEFAULT_MODE = MODE_DIVIDER

# Resistances are entered in ohms.  MΩ → Ω is just a extra zeros on the form,
# so the single conversion point is the float() in the input parser.
DEFAULTS = {
    "vcc": "12", "r1": "100000", "r2": "22000", "rb": "1000000",
    "re": "1000", "rc": "2200", "beta": "100", "vbe": "0.7",
}

SCHEMATIC_FIELDS = (("vcc", "V"), ("r1", "Ω"), ("r2", "Ω"), ("rb", "Ω"),
                    ("rc", "Ω"), ("re", "Ω"), ("beta", ""))

# Lab 04 reference circuit: values are base units (V, Ω, F, s, Hz).
SIM_DEFAULTS = {
    "vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200", "re": "1000",
    "rl": "10000", "cin": "0.00001", "cout": "0.00001",
    "amplitude": "0.01", "frequency": "1000",
}
SIM_ANALYSES = spice_engine.ANALYSES
SIM_ANALYSIS_LABELS = {"dc": "DC operating point", "ac": "AC sweep",
                       "tran": "Transient waveform"}
SIM_FIELD_INFO = (
    ("vcc", "VCC", "V", "Supply"),
    ("r1", "R1", "Ω", "Upper divider"),
    ("r2", "R2", "Ω", "Lower divider"),
    ("rc", "RC", "Ω", "Collector resistor"),
    ("re", "RE", "Ω", "Emitter resistor"),
    ("rl", "RL", "Ω", "AC load"),
    ("cin", "Cin", "F", "Input coupling"),
    ("cout", "Cout", "F", "Output coupling"),
    ("amplitude", "Source amplitude", "V peak", "SIN source"),
    ("frequency", "Source frequency", "Hz", "SIN source"),
)


@app.template_filter("si")
def si_filter(value: float, unit: str) -> str:
    return si(value, unit)


def _schematic(raw: dict[str, str]) -> dict[str, str]:
    labels = {}
    for name, unit in SCHEMATIC_FIELDS:
        text = (raw.get(name) or "").strip()
        try:
            value = float(text)
        except ValueError:
            labels[name] = ""
            continue
        labels[name] = f"{value:g}" if not unit else si(value, unit)
    return labels


def _render(raw, errors, result, solution, mode):
    return render_template(
        "index.html",
        raw=raw,
        errors=errors,
        result=result,
        solution=solution,
        schematic=_schematic(raw),
        mode=mode,
        mode_label=LABELS.get(mode, "Unknown circuit"),
        equations=EQUATIONS,
        modes=MODES,
    )


@app.get("/")
def index():
    mode = request.args.get("mode", DEFAULT_MODE)
    if mode not in MODES:
        mode = DEFAULT_MODE
    return _render(DEFAULTS, {}, None, None, mode)


@app.post("/")
def analyze():
    raw = {name: request.form.get(name, "") for name in DEFAULTS}
    mode = request.form.get("mode", DEFAULT_MODE)
    values, errors = parse_mode_inputs(mode, raw)
    if values is None:
        return _render(raw, errors, None, None, mode), 400

    # Select the model from the form value.  Unknown modes are rejected by the
    # parser above; never guess that an unrecognised circuit is a divider.
    if mode == MODE_DIVIDER:
        solution = solve_reference(BiasInputs(**values))
        result = solve_divider(**values, solution=solution)
    elif mode == MODE_FIXED:
        solution = None
        result = solve_fixed(**values)
    elif mode == MODE_EMITTER:
        solution = None
        result = solve_emitter(**values)
    else:  # defensive: parse_mode_inputs should already have caught this
        return _render(raw, {"mode": "unknown bias circuit"}, None, None, mode), 400

    return _render(raw, {}, result, solution, mode)


def _analytical_reference(raw: dict[str, str]) -> dict | None:
    """Lab 3 DC approximation, kept separate from the SPICE model result.

    BF=100 and VBE=0.7 V are the documented assumptions of this comparison;
    they are not parameters claimed for the ngspice teaching model.
    """
    values, errors = spice_engine.validate_sim_inputs(raw)
    if errors:
        return None
    return solve_divider(
        vcc=values.vcc, r1=values.r1, r2=values.r2,
        re=values.re, rc=values.rc, beta=100.0, vbe=0.7,
    )


def _render_simulator(raw, errors, result, analysis):
    """Render the simulator page; charts stay empty unless a run succeeded."""
    status = result.get("status", "idle") if result else "idle"
    status_label = {"success": "Success", "error": "Error"}.get(status, "Not run yet")
    tone = {"success": "active", "error": "saturation"}.get(status, "idle")
    values = result.get("values", {}) if result else {}
    engine = result.get("engine", "ngspice") if result else "ngspice"
    model = result.get("model", spice_engine.MODEL_NAME) if result else spice_engine.MODEL_NAME
    return render_template(
        "simulator.html",
        raw=raw,
        errors=errors,
        result=result,
        analysis=analysis,
        analyses=SIM_ANALYSES,
        analysis_labels=SIM_ANALYSIS_LABELS,
        fields=SIM_FIELD_INFO,
        sim_values=values,
        analytical=_analytical_reference(raw),
        bode_chart=bode_svg(result) if result else "",
        wave_chart=wave_svg(result) if result else "",
        status_label=status_label,
        status_tone=tone,
        error_text=result.get("error", "") if result else "",
        engine=engine,
        engine_version=result.get("engine_version", "") if result else "",
        model=model,
        model_card=spice_engine.MODEL_CARD,
    )


@app.get("/simulator")
def simulator():
    analysis = request.args.get("analysis", "dc")
    if analysis not in SIM_ANALYSES:
        analysis = "dc"
    return _render_simulator(SIM_DEFAULTS, {}, None, analysis)


@app.post("/simulator")
def simulator_run():
    raw = {name: request.form.get(name, "") for name in spice_engine.SIM_FIELDS}
    analysis = request.form.get("analysis", "dc")
    if analysis not in SIM_ANALYSES:
        return _render_simulator(raw, {"analysis": "unknown analysis"}, None, analysis), 400

    _, errors = spice_engine.validate_sim_inputs(raw)
    if errors:
        return _render_simulator(raw, errors, None, analysis), 400

    result = spice_engine.simulate(raw, analysis)
    if result.get("field_errors"):
        errors = {**errors, **result["field_errors"]}
    return _render_simulator(raw, errors, result, analysis)


if __name__ == "__main__":
    app.run(debug=True)
