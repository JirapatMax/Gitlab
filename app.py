from flask import Flask, render_template, request

from bjt_bias import parse_inputs, solve
from formatting import si

app = Flask(__name__)

DEFAULTS = {"vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200",
            "re": "1000", "beta": "100", "vbe": "0.7"}

SCHEMATIC_FIELDS = (("vcc", "V"), ("r1", "Ω"), ("r2", "Ω"), ("rc", "Ω"),
                    ("re", "Ω"), ("beta", ""))


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


def _render(raw, errors, solution):
    return render_template(
        "index.html",
        raw=raw,
        errors=errors,
        solution=solution,
        schematic=_schematic(raw),
    )


@app.get("/")
def index():
    return _render(DEFAULTS, {}, None)


@app.post("/")
def analyze():
    raw = {name: request.form.get(name, "") for name in DEFAULTS}
    inputs, errors = parse_inputs(raw)
    if inputs is None:
        return _render(raw, errors, None), 400
    return _render(raw, {}, solve(inputs))


if __name__ == "__main__":
    app.run(debug=True)
