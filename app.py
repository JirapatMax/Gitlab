from flask import Flask, render_template, request

from bjt_bias import parse_inputs, solve
from formatting import si

app = Flask(__name__)

DEFAULTS = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
            "re": "1000", "beta": "150", "vbe": "0.7"}


@app.template_filter("si")
def si_filter(value: float, unit: str) -> str:
    return si(value, unit)


@app.get("/")
def index():
    return render_template("index.html", raw=DEFAULTS, errors={}, solution=None)


@app.post("/")
def analyze():
    raw = {name: request.form.get(name, "") for name in DEFAULTS}
    inputs, errors = parse_inputs(raw)
    if inputs is None:
        return render_template("index.html", raw=raw, errors=errors, solution=None), 400
    return render_template("index.html", raw=raw, errors={}, solution=solve(inputs))


if __name__ == "__main__":
    app.run(debug=True)
