# BJT Common-Emitter DC Bias Web App — Design

**Course:** ENG29 2121 (short lab) · **Date:** 2026-11-10 · **Repo:** `github.com/JirapatMax/Gitlab`

## 1. Intent and why

The lab asks for a small, real Flask application that computes the DC operating point
(Q-point) of an NPN BJT in a **common-emitter, voltage-divider bias** circuit, shows the
result with units, validates the input, warns when the transistor is not in the forward-active
region, and **cross-checks the result against an independent engineering calculation**.

Why it matters to the student: the Q-point is the thing the lab report is about, and the
voltage-divider bias is the standard illustration of *why* emitter degeneration plus a stiff
divider makes the operating point insensitive to β. The app therefore has to show two numbers,
not one: the exact (Thevenin) solution and the textbook approximation that ignores base current.

## 2. Goals

- One page, one form, seven inputs → a full Q-point with units.
- Calculation logic is pure Python, importable and testable without Flask.
- Input validation with per-field messages; no tracebacks on bad input.
- Region classification: cut-off, active, near-saturation, saturation — with an actionable warning.
- Exact-vs-approximate comparison table with the percentage difference per quantity, plus a
  short plain-language explanation of the difference.
- Tests cover the formulas against hand-computed golden values, every region, and the routes.
- Runs on Windows localhost with two commands; committed and pushed to GitHub the same day.

## 3. Non-goals

- No AC / small-signal analysis, no gain, no frequency response.
- No transient, no temperature sweep, no Ebers–Moll, no iterative nonlinear solver.
- No FET, no op-amp, no other bias topologies (fixed bias, collector feedback, emitter bias).
- No circuit editor, no netlist, no schematic capture.
- No database, no authentication, no deployment, no JS framework, no JSON API.
- No user accounts, no saved calculations, no PDF export.

## 4. Anti-goals (this would count as a failure even if it "works")

- Engineering math hidden inside a route or a template — it must live in `bjt_bias.py`.
- A result that silently reports a saturated/cut-off point as if it were a valid Q-point.
- A UI that requires JavaScript or a build step to show a number.
- Tests that only assert the route returns 200 and never check a numeric value.
- The repository still containing the committed merge-conflict markers or the stray diff dumps.

## 5. Constraints

- Python available as **`py`** (3.14.2); the `python` command on this machine is the Microsoft
  Store stub and fails. Use `py` everywhere, including `.venv` creation.
- Flask and pytest are not installed yet; PyPI is reachable. Python 3.12+ is acceptable if a
  3.14 wheel is ever missing.
- Windows console: write files as UTF-8, no BOM. Avoid non-ASCII in filenames and commit
  subjects (non-ASCII commit subjects previously produced mangled filenames in this repo).
- Single contributor, `main` branch, no PR review available. Deadline is today.

## 6. Approaches considered

### 6.1 Axis A — what "independent engineering calculation" means

| Option | What it is | Trade-off |
|---|---|---|
| **A1 — Two models: exact vs approximate** *(chosen)* | Solve with the Thevenin base loop including `IB`, and separately with the textbook approximation that sets `IB ≈ 0`. Show both and the delta. | Adds ~20 lines. The delta is physically meaningful (base-current loading), so it reads as engineering, not as a unit test. |
| A2 — Two algebraically identical formulations | Exact two ways (substitution vs 2×2 matrix solve); difference is round-off only. | Proves the algebra, but the numbers always match, so the "comparison" teaches nothing in the report. |
| A3 — Golden numbers only | One model, compare against a hard-coded reference. | Smallest, but the comparison lives in the tests, invisible in the demo. |

**Chosen: A1**, plus A3 as a free by-product — the golden hand-computed values go into the test
suite regardless, so the report can cite both the in-app comparison and the verified reference.

The exact solution is the **reported** Q-point. The approximate one is the comparison column.

### 6.2 Axis B — app shape

| Option | What it is | Trade-off |
|---|---|---|
| **B1 — Two layers, server-rendered** *(chosen)* | `bjt_bias.py` (pure) + `app.py` (routes) + Jinja templates + one CSS file. `POST /` re-renders. No JS. | Fewest moving parts, matches every requirement, trivially testable with the Flask test client. |
| B2 — App factory + blueprints + WTForms | `create_app()`, `routes/` package, form classes, CSRF. | Standard for a real product; for a seven-field one-page lab it triples the file count and adds a dependency. |
| B3 — Client-side calculator, Flask as a shell | JS computes, Flask only serves the page. | Smallest server, but violates "separate Python engineering logic" and makes the math untestable in Python. |

**Chosen: B1.** Form parsing is a ~30-line explicit parser returning `{field: message}`, not a
forms library; one page does not justify WTForms.

### 6.3 Axis C — calculation model depth

Iterative Ebers–Moll (exponential junction, self-consistent `VBE`) was rejected: it is the right
model for a device-physics course, but this lab is explicitly DC bias with a constant `VBE` and
no temperature, and iteration would obscure the bias-design lesson.

## 7. Engineering specification

### 7.1 Circuit

NPN, common emitter, voltage-divider bias: `R1` from `VCC` to base, `R2` from base to ground,
`RC` from `VCC` to collector, `RE` from emitter to ground. Constant `VBE` (default 0.7 V).

### 7.2 Inputs

| Field | Symbol | Unit | Valid range |
|---|---|---|---|
| Supply voltage | `VCC` | V | `0 < VCC ≤ 1000` |
| Upper base resistor | `R1` | Ω | `0 < R1 ≤ 1e9` |
| Lower base resistor | `R2` | Ω | `0 < R2 ≤ 1e9` |
| Collector resistor | `RC` | Ω | `0 < RC ≤ 1e9` |
| Emitter resistor | `RE` | Ω | `0 ≤ RE ≤ 1e9` |
| Current gain | `β` | — | `1 ≤ β ≤ 1e5` |
| Base-emitter drop | `VBE` | V | `0 ≤ VBE < VCC` |

All values must parse as finite floats. `RE = 0` is legal for the exact model (the approximate
model is then not applicable, see 7.4). Non-numeric, `NaN`, `inf`, and out-of-range values
produce a per-field error message and re-render the form; nothing is computed.

### 7.3 Exact model (Thevenin) — the reported Q-point

```
VBB = VCC · R2 / (R1 + R2)              (V)
RB  = R1 · R2 / (R1 + R2)               (Ω)
IB  = (VBB − VBE) / (RB + (β+1)·RE)     (A)
IC  = β · IB                            (A)
IE  = (β+1) · IB = IB + IC              (A)
VE  = IE · RE                           (V)
VC  = VCC − IC · RC                     (V)
VCE = VC − VE                           (V)
P   = VCE · IC                          (W)   transistor dissipation
```

### 7.4 Independent calculation (approximate model)

The textbook approximation neglects base current, so the divider is assumed unloaded:

```
VBB = VCC · R2 / (R1 + R2)              (V)
VB  ≈ VBB                               (V)
IE  = (VBB − VBE) / RE                  (A)   undefined when RE = 0
IC  ≈ IE                                (A)
IB  = IE / β                            (A)   reported for comparison only
VE  = IE · RE                           (V)
VC  = VCC − IC · RC                     (V)
VCE = VC − VE                           (V)
```

When `RE = 0` the approximate model is skipped and the UI says why, instead of dividing by zero.

### 7.5 Comparison

The comparison table has exactly **six** rows: `IB, IC, IE, VE, VC, VCE`. `VBB` and `RB` are
identical in both models by construction, so a Δ of 0 for them is noise; `P` is derived and is
reported for the exact model only. Both `OperatingPoint`s still populate every field.

For each row show exact, approximate, absolute delta and
`Δ% = (approx − exact) / exact · 100`. The headline number is `max |Δ%|` over the rows.

The comparison is computed **only when `exact.ic > 0`** (a conductive Q-point). In cut-off the
approximate model would return negative currents and every denominator is zero, so it is
suppressed: `approximate = None`, `rows = ()`, `max_delta_pct = None`, `verdict = None`, and an
info message explains that the two methods are not comparable with the device off. In addition,
`delta_pct` is `None` (rendered `n/a`) whenever that row's exact value is 0. That is a
defensive guard — with the shipped ranges it cannot happen, because every zero-denominator case
also suppresses the comparison.

Verdict thresholds on `max |Δ%|`:

| `max |Δ%|` | Label | Meaning shown to the user |
|---|---|---|
| ≤ 2 % | negligible | Base current loading is small; the approximation is fine here. |
| 2 – 10 % | small | Base current shifts the Q-point by *x* %; this is exactly what the exact solution corrects. |
| > 10 % | large | The divider is too lightly loaded for the approximation; use the exact value. |

Constants: `DELTA_NEGLIGIBLE_PCT = 2.0`, `DELTA_ACCEPTABLE_PCT = 10.0`.

### 7.6 Region classification

Evaluated on the exact model, in this order:

1. **Cut-off** — if `VBB ≤ VBE`. The formula would return negative currents, so clamp:
   `IB = IC = IE = 0`, `VE = 0`, `VC = VCC`, `VCE = VCC`, `P = 0`.
   Severity `warning`: base divider voltage does not reach `VBE`; raise `R2` or `VCC`.
2. **Saturation** — if `VCE < VCE_SAT_V` (0.2 V). Keep the linear numbers but mark them
   **not valid**, and report two reference values:
   `IC_sat = (VCC − VCE_SAT_V) / (RC + RE)` and `forced β = IC_sat / IB`.
   Severity `error`.
3. **Near saturation** — if `VCE_SAT_V ≤ VCE < VCE_NEAR_SAT_V` (1.0 V). Valid, but the Q-point is
   β-sensitive. Severity `warning`.
4. **Active** — otherwise. Severity `info`.

The approximate model is displayed whenever the exact model is conductive (`IC > 0`) and
`RE > 0`; in cut-off the whole comparison is suppressed (7.5), and outside the active region the
approximate column is flagged as inapplicable.

### 7.7 Worked reference (golden values for tests)

`VCC=12 V, R1=47 kΩ, R2=10 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=150, VBE=0.7 V`

| Quantity | Exact | Approximate | Δ% |
|---|---|---|---|
| VBB | 2.105263 V | 2.105263 V | — |
| RB | 8245.614 Ω | 8245.614 Ω | — |
| IB | 8.824501 µA | 9.368421 µA | +6.164 |
| IC | 1.323675 mA | 1.405263 mA | +6.164 |
| IE | 1.332500 mA | 1.405263 mA | +5.461 |
| VE | 1.332500 V | 1.405263 V | +5.461 |
| VC | 9.087915 V | 8.908421 V | −1.975 |
| VCE | 7.755415 V | 7.503158 V | −3.253 |
| P | 10.26565 mW | 10.54391 mW | — |

`—` means the row is not part of the six-row comparison. Region: **active** (VCE 7.76 V).
This is the default form state.

Other reference cases for tests:

- **Saturation:** same but `RC = 10 kΩ` → `VCE = −2.569 V`, `IC_sat = 1.0727 mA`, forced β ≈ 121.6.
- **Cut-off:** same but `R1 = 100 kΩ, R2 = 1 kΩ` → `VBB = 0.1188 V` ≤ `VBE` → `IC = 0`, `VC = 12 V`.
- **`RE = 0`:** same but `RE = 0` → exact `IB = 170 µA`, `IC = 25.56 mA`, `VE = 0`; approximate skipped.

## 8. Structure

```
app.py                      Flask app, one route, Jinja filters, DEFAULTS
bjt_bias.py                 pure engineering logic — no Flask import
formatting.py               SI-prefix number formatting (pure)
templates/base.html         page shell, <head>, CSS link
templates/index.html        form + results + comparison + inline SVG schematic
static/style.css            the only stylesheet
tests/test_bjt_bias.py      formulas, regions, validation, comparison
tests/test_formatting.py    SI formatting edge cases
tests/test_app.py           GET, valid POST, invalid POST, cut-off POST
requirements.txt            Flask + pytest, version ranges
README.md                   rewritten: purpose, formulas, run steps, example, limits
docs/superpowers/specs/     this document
docs/superpowers/plans/     the implementation plan (next step)
```

Removed in this work: `electrical.py`, `test_electrical.py` (unrelated V=IR exercise; history
keeps them), and the two stray files whose names are mangled commit subjects containing raw
`git diff` output with ANSI escapes. `README.md` conflict markers removed and the file rewritten.

### 8.1 `bjt_bias.py` public API

```python
VCE_SAT_V = 0.2
VCE_NEAR_SAT_V = 1.0
DELTA_NEGLIGIBLE_PCT = 2.0
DELTA_ACCEPTABLE_PCT = 10.0

@dataclass(frozen=True) class BiasInputs:
    vcc: float; r1: float; r2: float; rc: float; re: float; beta: float; vbe: float

@dataclass(frozen=True) class OperatingPoint:
    vbb: float; rb: float; ib: float; ic: float; ie: float
    ve: float; vc: float; vce: float; p_transistor: float
    model: str                      # "exact" | "approximate"

@dataclass(frozen=True) class ComparisonRow:
    key: str; label: str; unit: str
    exact: float; approximate: float; delta: float; delta_pct: float | None

@dataclass(frozen=True) class Message:
    severity: str                   # "info" | "warning" | "error"
    text: str

@dataclass(frozen=True) class BiasSolution:
    inputs: BiasInputs
    exact: OperatingPoint
    approximate: OperatingPoint | None
    rows: tuple[ComparisonRow, ...]
    max_delta_pct: float | None
    verdict: str | None             # "negligible" | "small" | "large" | None
    region: str                     # "cut-off" | "saturation" | "near-saturation" | "active"
    messages: tuple[Message, ...]
    ic_sat: float | None            # saturation reference, None unless saturated
    forced_beta: float | None       # IC_sat / IB, None unless saturated

def parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]
def solve(inputs: BiasInputs) -> BiasSolution
def comparison_verdict(max_delta_pct: float | None) -> str | None
```

`parse_inputs` returns `(inputs, {})` or `(None, {"r1": "must be greater than 0", ...})`.
`comparison_verdict` is a public pure function applying the 7.5 thresholds, so the 2 % and 10 %
boundaries are testable directly instead of having to reverse-engineer inputs that land exactly
on a boundary.
`solve` never raises for valid inputs. No Flask, no I/O, no globals.

### 8.2 Route contract

| Method | Path | Behaviour |
|---|---|---|
| `GET` | `/` | 200, form pre-filled with the 7.7 default values, no results |
| `POST` | `/` | valid → 200 with results; invalid → **400** with the same form re-rendered, raw values preserved, field errors shown |

No other routes. No JSON endpoint. `app.py` exposes `app` for `flask --app app run` and has a
`__main__` block running `app.run(debug=True)` on `127.0.0.1:5000` (port 5001 documented as a
fallback if 5000 is taken).

### 8.3 UI

Single page, no JavaScript, works with keyboard only.

1. Title + one-line description.
2. Inline SVG schematic (decorative but labelled `role="img"` with an `aria-label` describing
   the divider, `RC`, `RE`, and the transistor) so the demo looks like a circuit, not a form.
3. Input card: seven labelled number inputs in a grid, units in the labels, a reset link back
   to `GET /`, and a submit button. Errors appear under the offending field with a red border.
4. Result card (only after a successful POST):
   - Region pill: green **Active**, amber **Near saturation** / **Cut-off**, red **Saturation**.
   - Q-point table: `VBB, RB, IB, IC, IE, VE, VC, VCE, P`, each with an SI-formatted value and unit.
   - Messages list, styled by severity.
5. Comparison card: the exact-vs-approximate table with Δ%, the `max |Δ%|` headline, and the
   verdict sentence from 7.5. When `RE = 0`, a note replaces the table.

`formatting.py` provides `si(value, unit)` → e.g. `8.82 µA`, `1.32 mA`, `8.25 kΩ`, `2.11 V`,
`7.76 V`, `10.3 mW`. **Three** significant figures (`%.3g` with an SI prefix), `µ` (U+00B5) for
micro. Three, not four: it is readable on a projector and matches every example above.

### 8.4 β-sensitivity (stretch, cut first)

If the plan has room: also report `IC` for `β × 2` and the resulting `ΔIC%` (golden case:
+2.99 %), as a one-line proof that divider bias is β-stable. Display-only, never used for region
classification. This is the first item to drop if anything slips.

## 9. Test strategy

- Formulas: assert every golden value in 7.7 with `pytest.approx(rel=1e-6)`.
- Approximate model: golden values and deltas.
- Regions: saturation case, cut-off clamping (`IC == 0`, `VC == VCC`), near-saturation boundary,
  active case, exactly at `VCE_SAT_V`.
- Cut-off suppresses the comparison (`approximate is None`, `rows == ()`, `verdict is None`).
- `RE = 0`: exact works, approximate is `None`, comparison suppressed (`rows == ()`), no
  `ZeroDivisionError`.
- Validation: table-driven — one case per rule, plus non-numeric, `NaN`, `inf`, missing field.
- Comparison: delta percentages for the golden case, `n/a` rows, and `comparison_verdict()`
  boundaries at 1.99 / 2.0 / 10.0 / 10.01 % plus `None`.
- Formatting: 0, sub-micro, kilo, mega, negative, and the µ character.
- Routes: `GET /` 200 and contains all seven input names; valid `POST` 200 contains a formatted
  current and "Active"; invalid `POST` 400 contains the field message and preserves input;
  cut-off `POST` shows the cut-off warning.

## 10. Commands

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m pytest -q
py app.py            # http://127.0.0.1:5000
```

## 11. Git

Single contributor, `main`, deadline today. Sequence: clean-up commit, solver commit, UI commit,
docs commit; push to `origin main` at the end. Commit subjects stay ASCII and never end with `:`.

## 12. Calls made after builder review

A fresh reviewer read the document and raised four ambiguities. All four are settled here; none
needs a decision from the student.

1. **Δ% in cut-off** — the comparison is suppressed entirely when `exact.ic == 0`, instead of
   dividing by zero or showing physically meaningless negative currents. Costs one `if`.
2. **Row set** — six rows only. `VBB`/`RB` are identical by construction and `P` is exact-only.
   The golden table marks these `—` so tests know what to assert.
3. **Significant figures** — three, matching every example in the document.
4. **Boundary tests** — `comparison_verdict()` becomes part of the public API so the 2 %/10 %
   thresholds are tested directly rather than through contrived inputs.

## 13. Left to the builder

Exact CSS spacing/colour values, warning wording, test file organisation, fixture style, whether
to add a `run.cmd` convenience script, and the commit split inside each work item.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Flask/pytest wheel missing for Python 3.14 | Both are pure Python; if installation fails, use any 3.12+ interpreter. |
| Port 5000 occupied on Windows | Run on 5001; documented in README. |
| Thai text mangled in README (happened before) | Write UTF-8 without BOM, verify by reading the file back after writing. |
| Conflict markers or stray files survive | Explicit task in the plan: delete and verify with `git grep '<<<<<<<'`. |
| Scope creep into AC analysis | Non-goals list in section 3 is the contract. |
