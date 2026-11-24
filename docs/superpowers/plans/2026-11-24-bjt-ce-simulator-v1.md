# BJT CE Amplifier Simulator v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Lab 3 Flask bias app into a minimal CE amplifier simulator that runs real ngspice `.op`, `.ac`, and `.tran` for one voltage-divider reference circuit without breaking the three analytical DC modes.

**Architecture:** Keep `app.py`/`dc_bias.py`/`bjt_bias.py` and all 71 existing tests untouched. Add `spice_engine.py` (validate → netlist → subprocess → parse), `charts.py` (server-rendered SVG from parsed ngspice vectors), and a separate `/simulator` page so the Lab 3 routes stay regression-safe. ngspice 47 is installed outside the repo; only code, docs, and evidence are committed.

**Tech Stack:** Python 3.14, Flask ≥3.1, pytest ≥8, ngspice 47 Windows 64-bit (`ngspice -b -o log -r raw circuit.cir`), `py7zr` used once outside the repo for extraction, OpenCode Browser for acceptance.

**Spec:** `C:\Users\b6826604\Downloads\Lab04_BJT_Amplifier_Simulator_2-2569.html` (Lab 04 handout). Parallel reference: `README.md`, `docs/validation.md`.

## Global Constraints

- Preserve all three Lab 3 analytical DC bias modes and the existing 71 tests; never delete or modify their solver paths.
- Reference fixture values from the handout: `VCC=12 V`, `R1=100 kΩ`, `R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `RL=10 kΩ`, `Cin=Cout=10 µF`, source `10 mV peak / 1 kHz`.
- BJT model must be stated by name and parameters in code and README; no guessed "specific part" claims, no instructor starter file exists on this machine.
- Call ngspice with `subprocess.run([...], shell=False, timeout=...)` in a per-run temporary working directory. Never pass raw form text to the command line or netlist.
- Never fabricate traces, hard-code gain/frequency/waveform "success" values, or show old plots with a success status after a failed run.
- Distinguish SPICE results from analytical `dc_bias.py` values everywhere they appear.
- Do not commit `.venv/`, `.env`, API keys/tokens, ngspice binaries, or large temporary run files.
- Browser acceptance cases B1–B8 must be recorded as PASS/FAIL/NOT RUN honestly; Playwright MCP and Impeccable are not installed, so use OpenCode Browser and say so explicitly.

## Review Focus

- `RE=0`, negative/non-numeric frequency, amplitude above the supported range → field-level error and HTTP 400, no crash and no stale chart. Test: `tests/test_spice_engine.py::test_validate_rejects_invalid_values` (Task 2) and `tests/test_app_spice.py::test_invalid_input_returns_400_without_chart` (Task 4).
- ngspice missing / non-zero exit / empty raw output / timeout → explicit error status, never a success graph. Test: `tests/test_spice_engine.py::test_run_netlist_reports_timeout_and_failure` (Task 1) and `tests/test_spice_engine.py::test_simulate_error_paths` (Task 3).
- Changing `RE` or source amplitude/frequency must change parsed vectors and plots, not reuse cached values. Test: `tests/test_spice_engine.py::test_simulate_changes_with_input` (Task 3) and browser B3/B6 (Task 6).
- AC gain/phase and transient axes must carry Hz/dB/deg and s/V labels; with no −3 dB crossing in the sweep, report "not determined in sweep range" instead of inventing a cutoff. Test: `tests/test_spice_engine.py::test_parse_ac_and_transient_units` (Task 3) and `tests/test_charts.py::test_charts_have_labeled_axes` (Task 4).
- Lab 3 regression: all three bias modes still compute and the original 71 tests still pass. Test: `tests/test_app_spice.py::test_lab3_routes_unchanged` (Task 4) plus full `pytest -q` in every task.

---

### Task 1: ngspice toolchain and process adapter

**Files:**
- Install outside repo: `%LOCALAPPDATA%\ngspice-47\Spice64\bin\ngspice.exe`
- Create: `spice_engine.py` (first section only)
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: nothing; Python 3.14 standard library.
- Produces: `class SpiceUnavailable(Exception)`, `class SpiceRunError(Exception)`, `find_ngspice() -> Path`, `run_netlist(netlist: str, *, timeout: float = 20.0) -> RunResult`; `RunResult` has `ok: bool`, `log: str`, `raw: str`, `error: str`, `returncode: int`, `log_path: Path`, `raw_path: Path`.

- [ ] **Step 1: Install and verify ngspice 47**
  Download the official `ngspice-47_64.7z` (~13.8 MB) from the ngspice SourceForge release folder, extract it to `%LOCALAPPDATA%\ngspice-47` using `py7zr` installed only in `.venv`, then run `ngspice --version` and record the exact output. Do not commit the binary or `py7zr` to `requirements.txt`.

- [ ] **Step 2: Write the failing tests**
  In `tests/test_spice_engine.py`, monkeypatch `spice_engine.subprocess.run`: assert the executable list contains `-b`, `-o`, `-r`, ends with a `.cir` path, has `shell=False` and the given `timeout`; assert `TimeoutExpired` and a non-zero return code produce `ok=False` with a non-empty `error` and empty `raw`; assert `find_ngspice()` honours `NGSPICE_EXE` and raises `SpiceUnavailable` when nothing is found.

- [ ] **Step 3: Run the tests and verify they fail** (`pytest tests/test_spice_engine.py -q`) — expected `ModuleNotFoundError`/missing symbols.

- [ ] **Step 4: Implement `find_ngspice` and `run_netlist`**
  Search `NGSPICE_EXE`, then `PATH`, then the install directory above. Use `tempfile.TemporaryDirectory()` per run, write `circuit.cir`, call `subprocess.run([...], capture_output=True, text=True, timeout=timeout, cwd=workdir, shell=False)`, read the `.log` and `.raw` files inside the context manager, and convert exceptions into `RunResult(ok=False, error=...)`.

- [ ] **Step 5: Run the full test suite** (`pytest -q`) — expected all prior 71 tests plus the new tests pass.

- [ ] **Step 6: Commit** `git add spice_engine.py tests/test_spice_engine.py && git commit -m "feat: add ngspice process adapter with timeout and error handling"`

### Task 2: Validated inputs and named netlists

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `RunResult` from Task 1.
- Produces: `SIM_FIELDS`, `ANALYSES = ("dc", "ac", "tran")`, `MODEL_NAME = "QNPN_TEACH"`, `MODEL_CARD`, dataclass `SimInputs(vcc, r1, r2, rc, re, rl, cin, cout, amplitude, frequency)`, `validate_sim_inputs(raw: Mapping[str, str]) -> tuple[SimInputs | None, dict[str, str]]`, `build_netlist(inputs: SimInputs, analysis: str) -> str`.

- [ ] **Step 1: Write the failing tests**
  Assert `re=0`, `frequency=-1`, `amplitude="abc"`, and a form value containing `;` are rejected with field errors; assert valid fixture values parse to floats in Ω/V/Hz; assert each analysis netlist contains `.model QNPN_TEACH NPN(...)`, `.op` / `.ac dec 100 0.1 10Meg` / `.tran` as appropriate, `Cin` and `Cout` of `10u`, `RL` of `10k`, a `SIN(0 <amp> <freq>)` source, and that `.tran` stop time shrinks when frequency increases.

- [ ] **Step 2: Run the tests and verify they fail** (`pytest tests/test_spice_engine.py -q`).

- [ ] **Step 3: Implement validation and netlist generation**
  Reuse the finite-number style of `dc_bias._read_number`; require all resistances and capacitors > 0 and frequency/amplitude > 0 with explicit upper bounds. Build the netlist from an f-string of already-validated floats only: nodes `vcc, base, collector, emitter, in, out`; `VCC`, `R1`, `R2`, `RC`, `RE`, `RL`, `Q1`, `CIN`, `COUT`, `VIN`. Use `VIN in 0 DC 0 AC 1 SIN(0 <amplitude> <frequency>)`, `Vout` measured at `out`, `Vin` at `in`. Model card: `.model QNPN_TEACH NPN(IS=1E-14 BF=100 BR=0.1 VAF=100 CJE=25p CJC=5p TF=0.3n)`, documented as a teaching model, not a specific transistor.

- [ ] **Step 4: Run the tests and verify they pass**, then `pytest -q` for the whole suite.

- [ ] **Step 5: Commit** `git commit -am "feat: validate simulator inputs and generate CE reference netlists"`

### Task 3: Parse real ngspice output and expose `simulate()`

**Files:**
- Modify: `spice_engine.py`
- Create: `tests/fixtures/` with small real `.log`/`.raw` samples captured from the installed ngspice (trim to the needed vectors)
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `SimInputs`, `build_netlist`, `run_netlist` from Tasks 1–2.
- Produces: `parse_op(log: str) -> dict`, `parse_ac(raw: str) -> dict`, `parse_tran(raw: str) -> dict`, `simulate(raw: Mapping[str, str], analysis: str) -> dict`. Every success result has `status="success"`, `engine="ngspice"`, `model=MODEL_NAME`, `analysis`, and a `values` dict; every failure has `status="error"`, `error`, and no `values`.

- [ ] **Step 1: Capture one real run for each analysis**
  Write the three netlists from Task 2 to a scratch directory and run `ngspice -b -o run.log -r run.raw circuit.cir` for `.op`, `.ac`, and `.tran`. Confirm the raw/header format actually produced by ngspice 47 before writing the parser, and save only trimmed fixtures in `tests/fixtures/`.

- [ ] **Step 2: Write the failing tests**
  `test_parse_op_reads_node_voltages` asserts `VB`, `VE`, `VC`, `VCE` decoded from a real log with volts units; `test_parse_ac_and_transient_units` asserts AC points carry `frequency_hz`, `gain_db`, `phase_deg` and transient points carry `time_s`, `vin_v`, `vout_v`, and that a sweep without a −3 dB crossing yields `fc="not determined in sweep range"`; `test_simulate_error_paths` monkeypatches `run_netlist` to fail and asserts `status="error"`; `test_simulate_changes_with_input` asserts raising `re` changes `IC` and changing `frequency` changes the transient time vector.

- [ ] **Step 3: Run the tests and verify they fail.**

- [ ] **Step 4: Implement the parsers and `simulate()`**
  Parse `.op` node voltages from the log; parse the ASCII raw blocks by `Plotname`, `No. Points`, `Variables` and `Values` sections, handling complex `real,imag` pairs for AC (`gain_db = 20log10(|v(out)/v(in)|)`, `phase_deg = degrees(atan2(imag, real))`) and real pairs for transient. Derive `IC` from `(V(vcc) − V(collector))/RC` when `@vcc` current is absent. Never return partial data as success: empty vectors, parse exceptions, or missing engine all become `status="error"`.

- [ ] **Step 5: Run the tests and the full suite; verify all pass.**

- [ ] **Step 6: Commit** `git commit -am "feat: parse ngspice op/ac/tran output into unit-bearing results"`

### Task 4: Simulator page, charts, and regression-safe routing

**Files:**
- Create: `charts.py`, `templates/simulator.html`
- Modify: `app.py`, `templates/base.html`, `templates/index.html`, `static/style.css`, `tests/test_app_spice.py` (new), `tests/test_charts.py` (new)

**Interfaces:**
- Consumes: `simulate()` and `validate_sim_inputs()` from Tasks 2–3; `dc_bias.solve_divider()` for the analytical DC reference.
- Produces: `bode_svg(result: dict) -> str`, `wave_svg(result: dict) -> str`; Flask routes `GET/POST /simulator`, and helper `_render_simulator(raw, errors, result, analysis)`.

- [ ] **Step 1: Write the failing tests**
  `test_charts_have_labeled_axes` asserts Bode SVG contains `Hz`, `dB`, `deg` and the waveform SVG contains `s`, `V`, `Vin`, `Vout`, with point count matching the parsed data; `test_invalid_input_returns_400_without_chart` posts `re=0` and asserts 400, field error, and no SVG; `test_engine_error_shows_error_status` monkeypatches `spice_engine.simulate` to return an error and asserts the page shows the error with no chart; `test_lab3_routes_unchanged` posts the Lab 3 A1 values to `/` and asserts the old result keys are still rendered.

- [ ] **Step 2: Run the tests and verify they fail.**

- [ ] **Step 3: Implement charts and routes**
  Generate SVG in Python with explicit viewBox, grid, axes ticks, SI labels using `formatting.si`, and polylines built only from parsed floats; return an empty string on failure. In `app.py`, add `GET /simulator` with fixture defaults and `POST /simulator` that validates, calls `simulate()`, and passes SPICE plus analytical results with separate "ngspice" and "Analytical (Lab 3)" labels. Leave the existing `/` handlers byte-for-byte unchanged apart from a link to the simulator.

- [ ] **Step 4: Implement the UI**
  Add a compact analysis selector (DC / AC / Transient), grouped inputs with units, a Run button, a status strip showing `Running/Success/Error` plus engine/model, chart cards with legends, and a DC comparison table. Add a nav link in `base.html` and a small "Open simulator" link on the Lab 3 page. Keep the existing responsive CSS conventions; verify desktop and narrow widths later in Task 6.

- [ ] **Step 5: Run the tests and the whole suite; verify all pass.**

- [ ] **Step 6: Commit** `git commit -am "feat: add CE simulator page with real ngspice charts"`

### Task 5: Honest UI review and documentation

**Files:**
- Modify: `static/style.css`, `templates/simulator.html`, `README.md`, `docs/validation.md`
- Create: `docs/evidence/` screenshots from the real browser

**Interfaces:**
- Consumes: the working simulator from Task 4.
- Produces: a reviewed UI without changing formulas or plot data, plus setup/validation documentation.

- [ ] **Step 1: Review the running page**
  Start Flask, inspect the simulator at desktop and ~390 px widths. Fix only UI files: input grouping, readable legends/units, visible error state, and no clipped buttons or charts. Do not touch numerical code. If the `impeccable` skill is unavailable, state that plainly in `docs/validation.md` rather than claiming it ran.

- [ ] **Step 2: Update README and validation record**
  Document ngspice 47 download/extraction, `NGSPICE_EXE` (or PATH) setup, `py7zr` extraction step, `.venv` test command, Flask run command, the model card, the netlist node/Vin/Vout definitions, and the fact that results come from real runs with separate analytical labels. Add 3–5 lines stating which parts AI created and which the student must check (equations/units, model provenance, ngspice logs, browser B1–B8).

- [ ] **Step 3: Commit** `git commit -am "docs: document ngspice setup, model and simulator UI review"`

### Task 6: Browser acceptance B1–B8, final verification, publish

**Files:**
- Modify: `docs/validation.md`, `docs/evidence/` (screenshots)
- Test: full suite plus real browser runs

**Interfaces:**
- Consumes: all earlier tasks.
- Produces: a truthful B1–B8 table and a pushed commit.

- [ ] **Step 1: Run B1–B8 in OpenCode Browser**
  For each case: fresh snapshot → select mode → fill exact values → submit real form → read values/units/status from the page → compare with ngspice logs or independent calculation → record PASS/FAIL/NOT RUN with evidence. B3 changes only `RE`; B6 changes only amplitude or frequency. Capture desktop and mobile screenshots. Record Playwright MCP as `NOT RUN` because it is not configured.

- [ ] **Step 2: Fix only defects found, then re-run those cases and the full suite** (`pytest -q`).

- [ ] **Step 3: Verify git diff contains no binaries, secrets, or temporary run files** (`git status --short`, `git diff --stat`).

- [ ] **Step 4: Commit and push** `git commit -am "docs: record Lab 4 browser acceptance B1-B8" && git push origin main`, then report the final commit SHA.
