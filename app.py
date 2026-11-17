from flask import Flask, render_template, request

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


if __name__ == "__main__":
    app.run(debug=True)
