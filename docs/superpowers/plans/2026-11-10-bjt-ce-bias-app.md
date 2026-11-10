# BJT Common-Emitter DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Flask app that computes and displays the DC operating point of an NPN common-emitter voltage-divider-biased circuit, validates input, warns on cut-off/saturation, and cross-checks the exact Thevenin solution against the textbook approximation.

**Architecture:** Pure engineering logic in `bjt_bias.py` (dataclasses + functions, no Flask), SI formatting in `formatting.py`, and a single-route Flask app in `app.py` rendering two Jinja templates with one stylesheet. No JavaScript, no database, no JSON API.

**Tech Stack:** Python 3.14 (via `py`), Flask 3.x, pytest 8+, Jinja2, plain CSS.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-app-design.md`

## Global Constraints

- Interpreter: always `.venv\Scripts\python.exe` — never bare `python` (Store stub) and never rely on `Activate.ps1` persisting between shell commands.
- Test command is always `.venv\Scripts\python.exe -m pytest` (the `-m` form puts the repo root on `sys.path`).
- No dependency beyond Flask and pytest. No JavaScript. No JSON endpoint.
- UI text is English. Numbers use **three** significant figures via `formatting.si()`; micro prefix is `µ` (U+00B5).
- All files are UTF-8 without BOM. Commit subjects are ASCII and never end with `:`.
- `bjt_bias.py` and `formatting.py` must not import Flask or perform I/O.
- Exact model is the reported Q-point; the approximate model appears only in the comparison.
- `POST /` returns **400** on validation failure, 200 on success.
- Region labels are exactly: `cut-off`, `saturation`, `near-saturation`, `active`. Verdicts are exactly: `negligible`, `small`, `large`, or `None`.
- Validation messages are exactly: `required`, `must be a number`, `must be a finite number`, `must be greater than 0`, `must be at least 0`, `must be at least 1`, `is above the supported maximum`, `must be less than VCC`.

## Review Focus

Failure modes the spec implies but no single formula test covers — each has a test in the owning task:

1. **Blank or non-numeric field** (user presses Enter in an input) → must render a field message, never a 500 or traceback. Tasks 3 and 8.
2. **`RE = 0`** (legitimate design) → the approximate model must not divide by zero and `solve()` must still return. Tasks 6 and 7.
3. **Cut-off design (`VBB ≤ VBE`)** → must not display negative currents as a working Q-point. Tasks 5, 7 and 8.
4. **Saturated design** → must not look like a normal Q-point; must show the error, `IC(sat)` and forced β. Tasks 5, 7 and 8.
5. **Resistance entered in Ω vs kΩ (1000× error)** → every output number must carry an explicit SI unit so the mistake is visible. Tasks 2 and 8.

## File Structure

| File | Responsibility |
|---|---|
| `formatting.py` | `si(value, unit)` — SI prefix + 3 significant figures. Pure. |
| `bjt_bias.py` | Input dataclass + validation, exact solver, approximate solver, region classification, comparison, `solve()` assembly. Pure. |
| `app.py` | Flask app, `DEFAULTS`, `GET /`, `POST /`, `si` Jinja filter. |
| `templates/base.html` | Page shell, `<head>`, stylesheet link, block for content. |
| `templates/index.html` | Form, inline SVG schematic, Q-point table, messages, comparison table. |
| `static/style.css` | All styling. |
| `tests/test_formatting.py` | `si()` cases. |
| `tests/test_bjt_bias.py` | Parsing, formulas, regions, comparison, end-to-end `solve()`. |
| `tests/test_app.py` | GET, valid POST, invalid POST, cut-off POST. |
| `requirements.txt` | `Flask>=3.1,<4`, `pytest>=8,<10`. |
| `README.md` | Purpose, formulas, run steps, example, limits. |

Deleted in Task 1: `electrical.py`, `test_electrical.py`, `README.md`, and the two stray files matching `DC circuit` (mangled commit subjects containing raw `git diff` output).

**Deliberately dropped:** the β-sensitivity stretch item (spec §8.4). The exact-vs-approximate comparison already demonstrates β stability, and the deadline does not pay for a second feature.

---

### Task 1: Clean repository and set up the toolchain

**Files:**
- Delete: `electrical.py`, `test_electrical.py`, `README.md`, both files matching `DC circuit`
- Create: `requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: a working `.venv` with Flask and pytest, and a repo with no conflict markers or stray files.

- [ ] **Step 1: Remove the stray and obsolete files**

```powershell
Get-ChildItem -File | Where-Object { $_.Name -match 'DC circuit' } | Remove-Item -Force
Remove-Item electrical.py, test_electrical.py, README.md
```

The `Get-ChildItem` form is deliberate: the two stray filenames contain private-use Unicode characters and cannot be typed reliably.

- [ ] **Step 2: Replace `requirements.txt`**

```
Flask>=3.1,<4
pytest>=8,<10
```

- [ ] **Step 3: Append the pytest cache to `.gitignore`**

```
.pytest_cache/
```

- [ ] **Step 4: Create the virtualenv and install**

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- [ ] **Step 5: Verify the toolchain**

```powershell
.venv\Scripts\python.exe -c "import flask, pytest; print(flask.__version__, pytest.__version__)"
git grep -n "<<<<<<<"
```

Expected: two version numbers printed; `git grep` prints nothing (exit code 1).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: clean repo and set up toolchain"
```

---

### Task 2: SI number formatting

**Files:**
- Create: `formatting.py`
- Test: `tests/test_formatting.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `si(value: float, unit: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from formatting import si


@pytest.mark.parametrize("value,unit,expected", [
    (8.824501e-6, "A", "8.82 µA"),
    (1.323675e-3, "A", "1.32 mA"),
    (8245.614, "Ω", "8.25 kΩ"),
    (2.105263, "V", "2.11 V"),
    (0.0102656, "W", "10.3 mW"),
    (0.0, "A", "0 A"),
    (-0.0025, "A", "-2.5 mA"),
    (1000.0, "Ω", "1 kΩ"),
    (float("inf"), "A", "n/a"),
    (float("nan"), "A", "n/a"),
])
def test_si(value, unit, expected):
    assert si(value, unit) == expected
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_formatting.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'formatting'`.

- [ ] **Step 3: Implement `formatting.py`**

```python
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
```

- [ ] **Step 4: Run it and watch it pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_formatting.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add formatting.py tests/test_formatting.py
git commit -m "feat: add si formatting helper"
```

---

### Task 3: Input parsing and validation

**Files:**
- Create: `bjt_bias.py`
- Test: `tests/test_bjt_bias.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BiasInputs` frozen dataclass: `vcc, r1, r2, rc, re, beta, vbe` (all `float`).
  - `parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]`.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from bjt_bias import BiasInputs, parse_inputs

VALID = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
         "re": "1000", "beta": "150", "vbe": "0.7"}


def test_parses_valid_inputs():
    inputs, errors = parse_inputs(VALID)
    assert errors == {}
    assert inputs == BiasInputs(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0,
                                re=1000.0, beta=150.0, vbe=0.7)


@pytest.mark.parametrize("field,value,message", [
    ("vcc", "0", "must be greater than 0"),
    ("vcc", "-1", "must be greater than 0"),
    ("vcc", "1001", "is above the supported maximum"),
    ("r1", "0", "must be greater than 0"),
    ("r2", "-5", "must be greater than 0"),
    ("rc", "0", "must be greater than 0"),
    ("re", "-1", "must be at least 0"),
    ("re", "0", None),
    ("beta", "0.5", "must be at least 1"),
    ("beta", "100001", "is above the supported maximum"),
    ("vbe", "-0.1", "must be at least 0"),
    ("vbe", "12", "must be less than VCC"),
    ("rc", "abc", "must be a number"),
    ("rc", "nan", "must be a finite number"),
    ("rc", "inf", "must be a finite number"),
    ("rc", "", "required"),
])
def test_field_errors(field, value, message):
    inputs, errors = parse_inputs({**VALID, field: value})
    if message is None:
        assert inputs is not None and errors == {}
    else:
        assert inputs is None
        assert errors == {field: message}


def test_missing_field_is_required():
    raw = dict(VALID)
    del raw["vbe"]
    inputs, errors = parse_inputs(raw)
    assert inputs is None
    assert errors == {"vbe": "required"}
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q`
Expected: FAIL — `ImportError: cannot import name 'BiasInputs'`.

- [ ] **Step 3: Implement `BiasInputs` and `parse_inputs` in `bjt_bias.py`**

```python
import math
from dataclasses import dataclass
from typing import Mapping

MAX_VCC = 1000.0
MAX_RESISTANCE = 1e9
MAX_BETA = 1e5


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    ...
```

Body rules, in this order per field: missing/blank → `required`; not a float → `must be a number`;
non-finite → `must be a finite number`; then the range checks below. Range messages:
`vcc` `0 < vcc ≤ 1000`, `r1/r2/rc` `0 < r ≤ 1e9`, `re` `0 ≤ re ≤ 1e9`, `beta` `1 ≤ beta ≤ 1e5`,
`vbe` `0 ≤ vbe < vcc`. The `vbe < vcc` check is skipped when `vcc` itself failed.
Return `(None, errors)` when any field failed, otherwise `(BiasInputs(...), {})`.

- [ ] **Step 4: Run and watch them pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias.py tests/test_bjt_bias.py
git commit -m "feat: add bias input parsing and validation"
```

---

### Task 4: Exact (Thevenin) solver

**Files:**
- Modify: `bjt_bias.py`
- Test: `tests/test_bjt_bias.py`

**Interfaces:**
- Consumes: `BiasInputs`.
- Produces:
  - `OperatingPoint` frozen dataclass: `vbb, rb, ib, ic, ie, ve, vc, vce, p_transistor` (`float`), `model: str`.
  - `solve_exact(inputs: BiasInputs) -> OperatingPoint` with `model="exact"`. May return negative currents for a cut-off design; clamping is Task 5's job.

- [ ] **Step 1: Write the failing tests**

```python
from dataclasses import replace

import pytest

from bjt_bias import BiasInputs, solve_exact

GOLDEN = BiasInputs(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0,
                    re=1000.0, beta=150.0, vbe=0.7)
REL = 1e-6


def test_exact_matches_hand_calculation():
    p = solve_exact(GOLDEN)
    assert p.vbb == pytest.approx(2.10526315789, rel=REL)
    assert p.rb == pytest.approx(8245.61403509, rel=REL)
    assert p.ib == pytest.approx(8.82450148728e-06, rel=REL)
    assert p.ic == pytest.approx(0.00132367522309, rel=REL)
    assert p.ie == pytest.approx(0.00133249972458, rel=REL)
    assert p.ve == pytest.approx(1.33249972458, rel=REL)
    assert p.vc == pytest.approx(9.0879145092, rel=REL)
    assert p.vce == pytest.approx(7.75541478462, rel=REL)
    assert p.p_transistor == pytest.approx(0.0102656503952, rel=REL)
    assert p.model == "exact"


def test_exact_without_emitter_resistor():
    p = solve_exact(replace(GOLDEN, re=0.0))
    assert p.ib == pytest.approx(0.000170425531915, rel=REL)
    assert p.ic == pytest.approx(0.0255638297872, rel=REL)
    assert p.ve == 0.0
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k exact`
Expected: FAIL — `ImportError: cannot import name 'solve_exact'`.

- [ ] **Step 3: Implement `OperatingPoint` and `solve_exact`**

```python
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
    ...
```

Formulas (spec §7.3): `vbb = vcc*r2/(r1+r2)`, `rb = r1*r2/(r1+r2)`,
`ib = (vbb-vbe)/(rb+(beta+1)*re)`, `ic = beta*ib`, `ie = ib+ic`, `ve = ie*re`,
`vc = vcc-ic*rc`, `vce = vc-ve`, `p_transistor = vce*ic`.

- [ ] **Step 4: Run and watch them pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k exact`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias.py tests/test_bjt_bias.py
git commit -m "feat: add exact bias solver"
```

---

### Task 5: Region classification and cut-off clamping

**Files:**
- Modify: `bjt_bias.py`
- Test: `tests/test_bjt_bias.py`

**Interfaces:**
- Consumes: `BiasInputs`, `OperatingPoint`.
- Produces:
  - `Message` frozen dataclass: `severity: str`, `text: str`.
  - Constants `VCE_SAT_V = 0.2`, `VCE_NEAR_SAT_V = 1.0`.
  - `clamp_cutoff(inputs: BiasInputs, point: OperatingPoint) -> OperatingPoint` — returns `ib=ic=ie=ve=p_transistor=0.0`, `vc=vcc`, `vce=vcc`, same `vbb`/`rb`/`model`.
  - `classify(inputs: BiasInputs, point: OperatingPoint) -> tuple[str, tuple[Message, ...]]` — assumes the point is not cut off; returns `saturation` (`vce < 0.2`), `near-saturation` (`< 1.0`), or `active`.
  - `saturation_reference(inputs: BiasInputs, point: OperatingPoint) -> tuple[float, float]` — `((vcc - VCE_SAT_V)/(rc + re), ic_sat/point.ib)`.

- [ ] **Step 1: Write the failing tests**

```python
from bjt_bias import (VCE_NEAR_SAT_V, VCE_SAT_V, classify,
                      clamp_cutoff, saturation_reference, solve_exact)

ACTIVE_POINT = solve_exact(GOLDEN)


def test_active():
    region, messages = classify(GOLDEN, ACTIVE_POINT)
    assert region == "active"
    assert [m.severity for m in messages] == ["info"]
    assert "forward-active" in messages[0].text


def test_saturation_when_vce_below_threshold():
    region, messages = classify(GOLDEN, replace(ACTIVE_POINT, vce=0.19))
    assert region == "saturation"
    assert [m.severity for m in messages] == ["error"]


def test_boundary_at_vce_sat_is_near_saturation():
    region, _ = classify(GOLDEN, replace(ACTIVE_POINT, vce=VCE_SAT_V))
    assert region == "near-saturation"


def test_boundary_at_vce_near_sat_is_active():
    region, _ = classify(GOLDEN, replace(ACTIVE_POINT, vce=VCE_NEAR_SAT_V))
    assert region == "active"


def test_clamp_cutoff_zeroes_currents():
    clamped = clamp_cutoff(GOLDEN, replace(ACTIVE_POINT, ib=-1e-6, ic=-1e-4, ve=-0.5, vc=13.0, vce=13.5))
    assert (clamped.ib, clamped.ic, clamped.ie, clamped.ve, clamped.p_transistor) == (0.0, 0.0, 0.0, 0.0, 0.0)
    assert clamped.vc == GOLDEN.vcc
    assert clamped.vce == GOLDEN.vcc


def test_saturation_reference():
    point = replace(ACTIVE_POINT, vce=-2.56925195549)
    ic_sat, forced_beta = saturation_reference(replace(GOLDEN, rc=10000.0), point)
    assert ic_sat == pytest.approx(0.00107272727273, rel=REL)
    assert forced_beta == pytest.approx(121.562365225, rel=REL)
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k "region or cutoff or saturation or active"`
Expected: FAIL — `ImportError: cannot import name 'classify'`.

- [ ] **Step 3: Implement the dataclass, constants and three functions**

Message texts (exact strings, asserted only by substring):
- active: `"Transistor is in the forward-active region."` severity `info`
- near-saturation: `"VCE is close to saturation; the Q-point is sensitive to beta and VBE."` severity `warning`
- saturation: `"Transistor is in saturation: VCE is below VCE(sat) = 0.2 V, so the linear-region values are not valid."` severity `error`

- [ ] **Step 4: Run and watch them pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k "region or cutoff or saturation or active"`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias.py tests/test_bjt_bias.py
git commit -m "feat: add operating region detection"
```

---

### Task 6: Approximate model, comparison and verdict

**Files:**
- Modify: `bjt_bias.py`
- Test: `tests/test_bjt_bias.py`

**Interfaces:**
- Consumes: `BiasInputs`, `OperatingPoint`.
- Produces:
  - `solve_approximate(inputs: BiasInputs) -> OperatingPoint | None` — `None` when `re == 0`; `model="approximate"`.
  - `ComparisonRow` frozen dataclass: `key, label, unit: str`, `exact, approximate, delta: float`, `delta_pct: float | None`.
  - `compare(exact: OperatingPoint, approximate: OperatingPoint) -> tuple[tuple[ComparisonRow, ...], float | None, str | None]` — six rows in order `IB, IC, IE, VE, VC, VCE`; `max_delta_pct` over non-`None` rows; verdict from `comparison_verdict`.
  - `comparison_verdict(max_delta_pct: float | None) -> str | None` — `None` → `None`; `≤ 2.0` → `"negligible"`; `≤ 10.0` → `"small"`; else `"large"`.
  - Constants `DELTA_NEGLIGIBLE_PCT = 2.0`, `DELTA_ACCEPTABLE_PCT = 10.0`.

- [ ] **Step 1: Write the failing tests**

```python
from bjt_bias import compare, comparison_verdict, solve_approximate


def test_approximate_matches_hand_calculation():
    p = solve_approximate(GOLDEN)
    assert p.vbb == pytest.approx(2.10526315789, rel=REL)
    assert p.rb == pytest.approx(8245.61403509, rel=REL)
    assert p.ib == pytest.approx(9.36842105263e-06, rel=REL)
    assert p.ic == pytest.approx(0.00140526315789, rel=REL)
    assert p.ve == pytest.approx(1.40526315789, rel=REL)
    assert p.vc == pytest.approx(8.90842105263, rel=REL)
    assert p.vce == pytest.approx(7.50315789474, rel=REL)
    assert p.p_transistor == pytest.approx(0.0105439113573, rel=REL)
    assert p.model == "approximate"


def test_approximate_is_none_without_emitter_resistor():
    assert solve_approximate(replace(GOLDEN, re=0.0)) is None


def test_comparison_rows_and_verdict():
    rows, max_delta, verdict = compare(solve_exact(GOLDEN), solve_approximate(GOLDEN))
    assert [row.key for row in rows] == ["ib", "ic", "ie", "ve", "vc", "vce"]
    ic_row = rows[1]
    assert ic_row.exact == pytest.approx(0.00132367522309, rel=REL)
    assert ic_row.approximate == pytest.approx(0.00140526315789, rel=REL)
    assert ic_row.delta_pct == pytest.approx(6.16374269006, rel=REL)
    assert max_delta == pytest.approx(6.16374269006, rel=REL)
    assert verdict == "small"


@pytest.mark.parametrize("value,expected", [
    (None, None), (0.0, "negligible"), (1.99, "negligible"), (2.0, "negligible"),
    (2.001, "small"), (10.0, "small"), (10.01, "large"), (250.0, "large"),
])
def test_comparison_verdict_boundaries(value, expected):
    assert comparison_verdict(value) == expected
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k "approximate or comparison"`
Expected: FAIL — `ImportError: cannot import name 'solve_approximate'`.

- [ ] **Step 3: Implement the model, rows and verdict**

Approximate formulas (spec §7.4): `ie = (vbb - vbe)/re`, `ic = ie`, `ib = ie/beta`, `ve = ie*re`,
`vc = vcc - ic*rc`, `vce = vc - ve`, `p_transistor = vce*ic`. Labels `IB/IC/IE/VE/VC/VCE`, units
`A/A/A/V/V/V`. `delta = approximate - exact`; `delta_pct = None` when `exact == 0` else
`delta/exact*100`.

- [ ] **Step 4: Run and watch them pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k "approximate or comparison"`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias.py tests/test_bjt_bias.py
git commit -m "feat: add approximate model comparison"
```

---

### Task 7: `solve()` assembly

**Files:**
- Modify: `bjt_bias.py`
- Test: `tests/test_bjt_bias.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `BiasSolution` frozen dataclass: `inputs, exact, approximate, rows, max_delta_pct, verdict, region, messages, ic_sat, forced_beta`.
  - `solve(inputs: BiasInputs) -> BiasSolution`.

- [ ] **Step 1: Write the failing tests**

```python
from bjt_bias import solve


def test_golden_solution_is_active_and_compares():
    solution = solve(GOLDEN)
    assert solution.region == "active"
    assert solution.approximate is not None
    assert len(solution.rows) == 6
    assert solution.verdict == "small"
    assert solution.max_delta_pct == pytest.approx(6.16374269006, rel=REL)
    assert solution.ic_sat is None and solution.forced_beta is None


def test_cutoff_suppresses_comparison():
    solution = solve(replace(GOLDEN, r1=100000.0, r2=1000.0))
    assert solution.region == "cut-off"
    assert solution.exact.ic == 0.0 and solution.exact.vc == GOLDEN.vcc
    assert solution.approximate is None and solution.rows == ()
    assert solution.verdict is None and solution.max_delta_pct is None
    assert [m.severity for m in solution.messages] == ["warning"]


def test_saturation_reports_reference_values():
    solution = solve(replace(GOLDEN, rc=10000.0))
    assert solution.region == "saturation"
    assert solution.ic_sat == pytest.approx(0.00107272727273, rel=REL)
    assert solution.forced_beta == pytest.approx(121.562365225, rel=REL)
    assert solution.messages[0].severity == "error"


def test_zero_emitter_resistor_does_not_crash():
    solution = solve(replace(GOLDEN, re=0.0))
    assert solution.exact.ic == pytest.approx(0.0255638297872, rel=REL)
    assert solution.approximate is None and solution.rows == ()
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bjt_bias.py -q -k "solution or cutoff or saturation_reports or zero_emitter"`
Expected: FAIL — `ImportError: cannot import name 'solve'`.

- [ ] **Step 3: Implement `BiasSolution` and `solve`**

Order inside `solve`:
1. `exact = solve_exact(inputs)`.
2. If `exact.vbb <= inputs.vbe`: `exact = clamp_cutoff(inputs, exact)`, `region = "cut-off"`,
   `messages = (Message("warning", "VBB is at or below VBE, so the transistor is cut off: IC = 0."),)`,
   `ic_sat = forced_beta = None`. Otherwise `region, messages = classify(inputs, exact)` and, when
   `region == "saturation"`, compute `ic_sat, forced_beta = saturation_reference(...)`.
3. `approximate = solve_approximate(inputs) if exact.ic > 0 else None` (`solve_approximate` already
   returns `None` for `re == 0`).
4. `rows, max_delta_pct, verdict = compare(exact, approximate) if approximate is not None else ((), None, None)`.

- [ ] **Step 4: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all tests pass, no failures.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias.py tests/test_bjt_bias.py
git commit -m "feat: assemble bias solution"
```

---

### Task 8: Flask app, templates and stylesheet

**Files:**
- Create: `app.py`, `templates/base.html`, `templates/index.html`, `static/style.css`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `parse_inputs`, `solve`, `si`.
- Produces: Flask `app` object; `GET /` and `POST /`; Jinja filter `si`; `DEFAULTS` dict with the seven string values of the golden example.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from app import app

VALID = {"vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
         "re": "1000", "beta": "150", "vbe": "0.7"}


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_get_renders_all_seven_inputs(client):
    body = client.get("/").get_data(as_text=True)
    for name in VALID:
        assert f'name="{name}"' in body


def test_valid_post_shows_qpoint_with_units(client):
    response = client.post("/", data=VALID)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "1.32 mA" in body
    assert "7.76 V" in body
    assert "Active" in body


def test_invalid_post_returns_400_and_keeps_input(client):
    response = client.post("/", data={**VALID, "r1": "-5"})
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "must be greater than 0" in body
    assert 'value="-5"' in body


def test_cutoff_post_warns(client):
    response = client.post("/", data={**VALID, "r1": "100000", "r2": "1000"})
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "cut off" in body
```

- [ ] **Step 2: Run and watch them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implement `app.py`**

```python
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
```

- [ ] **Step 4: Implement `templates/base.html` and `templates/index.html`**

`base.html` provides the HTML shell, `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`, a `<main>` block, and `{% block content %}{% endblock %}`.

`index.html` must contain:
- the title, a one-line description, and an inline SVG schematic with `role="img"` and an `aria-label` naming the divider, RC, RE and transistor;
- a `<form method="post" action="/">` with seven `<input type="number" step="any" name="<field>" value="{{ raw.<field> }}" ...>` controls, each with a unit in its label, and `{% if errors.<field> %}<p class="error">{{ errors.<field> }}</p>{% endif %}`;
- a results section shown only `{% if solution %}`, containing a region pill whose text is `Active` / `Near saturation` / `Cut-off` / `Saturation`, a Q-point table using `|si` for every number (`VBB, RB, IB, IC, IE, VE, VC, VCE, P`), the `solution.messages` list styled by `severity`, and for saturation the `IC(sat)` and forced-beta values;
- a comparison card showing the six `solution.rows` with exact, approximate and `Δ%` (`n/a` when `delta_pct is None`), the `max_delta_pct` headline, and the verdict sentence;
- a note instead of the comparison table when `solution.rows` is empty.

- [ ] **Step 5: Implement `static/style.css`**

System font stack, a centred `max-width: 960px` layout, a two-column CSS grid for the form and results above 800 px wide and one column below, visible focus outlines, and pill colours: green for active, amber for near-saturation and cut-off, red for saturation.

- [ ] **Step 6: Run and watch them pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
Expected: 4 passed.

- [ ] **Step 7: Launch it and look at it**

```powershell
$server = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m flask --app app run --port 5000 --no-reload" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3
(Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing).StatusCode
Stop-Process -Id $server.Id -Force
```

Expected: `200`. Open `http://127.0.0.1:5000` in a browser and confirm the default example shows IC `1.32 mA`, VCE `7.76 V` and an **Active** pill.

- [ ] **Step 8: Commit**

```bash
git add app.py templates static tests/test_app.py
git commit -m "feat: add flask user interface"
```

---

### Task 9: README, full verification and push

**Files:**
- Create: `README.md`
- Test: none (verification only)

**Interfaces:**
- Consumes: the finished application.
- Produces: a documented, pushed repository.

- [ ] **Step 1: Write `README.md`**

Contents: what the app is and which course it serves; the circuit and the two methods (exact
Thevenin, approximate with `IB ≈ 0`) with their formulas; the input and output tables with units;
the worked example from the spec §7.7 including the +6.16 % comparison; the region rules and their
thresholds; how to run on Windows (`py -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.venv\Scripts\python.exe app.py`, port 5001 fallback); how to run tests; the file map; and the limitations (no AC, no temperature, no FET).

- [ ] **Step 2: Verify the suite and the repository**

```powershell
.venv\Scripts\python.exe -m pytest -q
git grep -n "<<<<<<<"
git status --short
```

Expected: every test passes; `git grep` prints nothing; `git status` shows only `README.md` untracked.

- [ ] **Step 3: Verify the running app one last time**

```powershell
$server = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m flask --app app run --port 5000 --no-reload" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3
(Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing).StatusCode
Stop-Process -Id $server.Id -Force
```

Expected: `200`.

- [ ] **Step 4: Commit and push**

```bash
git add README.md
git commit -m "docs: rewrite readme and verify"
git push origin main
```

- [ ] **Step 5: Confirm the push**

```powershell
git log --oneline -3
git status -sb
```

Expected: `git status` reports `## main...origin/main` with no ahead/behind markers.
