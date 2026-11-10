# BJT Common-Emitter DC Bias Calculator

A small Flask web app that solves the DC operating point (Q-point) of an NPN BJT in a
common-emitter **voltage-divider bias** circuit, validates the input, warns when the
transistor is outside the forward-active region, and checks the answer against an
independent textbook approximation.

Written for the ENG29 2121 lab. No AC analysis, no transient analysis, no FET — just the
DC bias point.

แอป Flask ขนาดเล็กสำหรับคำนวณจุดทำงานกระแสตรง (Q-point) ของทรานซิสเตอร์ NPN แบบ
common-emitter ที่ไบอัสด้วยตัวแบ่งแรงดัน ตรวจสอบค่าที่กรอก เตือนเมื่อทรานซิสเตอร์
ไม่อยู่ในย่าน forward-active และเทียบผลกับวิธีประมาณแบบตำราอีกวิธีหนึ่ง

---

## Circuit

```
        VCC
         │
    ┌────┴────┐
   R1         RC
    │         │
    ├─────────┤ collector
    │         │
   R2        Q1  base at the R1/R2 node
    │         │
    │        RE
    │         │
   GND       GND
```

`VCC` feeds the divider `R1`/`R2`, which sets the base voltage. `RC` sets the collector
voltage and `RE` stabilises the operating point against β variation. The emitter is also
the reference for `VBE`.

## Two calculations

### 1. Exact — Thévenin equivalent with finite β

Replace the divider with its Thévenin equivalent:

```
VBB = VCC · R2 / (R1 + R2)
RB  = R1 · R2 / (R1 + R2)
```

Then write the base loop and solve for the base current:

```
IB  = (VBB − VBE) / (RB + (β + 1) · RE)
IC  = β · IB
IE  = IB + IC = (β + 1) · IB
VE  = IE · RE
VC  = VCC − IC · RC
VCE = VC − VE
P   = VCE · IC
```

This is the value the app reports as the operating point.

### 2. Approximate — textbook method with `IB ≈ 0`

Assume the base current is negligible, so `IE ≈ IC` and the base sits at `VBB`:

```
IE  = (VBB − VBE) / RE
IC  ≈ IE
IB  = IE / β
VE  = IE · RE
VC  = VCC − IC · RC
VCE = VC − VE
```

Skipped when `RE = 0` (division by zero) or when the transistor is cut off.

### Independent check

The app puts the exact and approximate values side by side for `IB, IC, IE, VE, VC, VCE`
and reports the largest relative difference:

| Largest difference | Verdict |
|---|---|
| ≤ 2 % | negligible — the approximation is fine |
| ≤ 10 % | small — the exact solution corrects a few percent |
| > 10 % | large — the divider is too lightly loaded, use the exact value |

The two methods are independent: the exact one keeps the `(β + 1)·RE` term, the
approximate one drops it. Agreement between them is the sanity check.

## Inputs

| Field | Meaning | Unit | Rule |
|---|---|---|---|
| `VCC` | supply voltage | V | > 0, ≤ 1000 |
| `R1` | upper divider resistor | Ω | > 0, ≤ 10⁹ |
| `R2` | lower divider resistor | Ω | > 0, ≤ 10⁹ |
| `RC` | collector resistor | Ω | > 0, ≤ 10⁹ |
| `RE` | emitter resistor | Ω | ≥ 0, ≤ 10⁹ |
| `β` | forward current gain | — | ≥ 1, ≤ 100000 |
| `VBE` | base-emitter voltage | V | ≥ 0, < VCC |

Invalid input returns HTTP 400, shows the message next to the field, and keeps the raw
values so the form can be corrected.

## Outputs

| Quantity | Unit |
|---|---|
| `VBB`, `RB` (Thévenin equivalent) | V, Ω |
| `IB`, `IC`, `IE` | A |
| `VE`, `VC`, `VCE` | V |
| `P` (transistor dissipation) | W |

Values use engineering prefixes (`µA`, `mA`, `kΩ`, …) and three significant figures.

## Region rules

| Region | Condition | Message |
|---|---|---|
| Cut-off | `VBB ≤ VBE` | warning; `IC = 0`, `VC = VCC`, comparison suppressed |
| Saturation | `VCE < 0.2 V` | error; reports `IC(sat) = (VCC − 0.2) / (RC + RE)` and forced β |
| Near saturation | `0.2 V ≤ VCE < 1.0 V` | warning; Q-point is sensitive to β and VBE |
| Active | `VCE ≥ 1.0 V` | info; transistor is in the forward-active region |

In cut-off and saturation the linear-region numbers are still displayed, but they are not
a valid bias point — read the message.

## Worked example

Default form state: `VCC = 12 V`, `R1 = 47 kΩ`, `R2 = 10 kΩ`, `RC = 2.2 kΩ`,
`RE = 1 kΩ`, `β = 150`, `VBE = 0.7 V`.

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

Region: **active** (`VCE = 7.76 V`). Largest difference 6.16 % → verdict **small**.

Other reference cases (used in the tests):

- **Saturation:** same but `RC = 10 kΩ` → `VCE = −2.569 V`, `IC(sat) = 1.0727 mA`,
  forced β ≈ 121.6.
- **Cut-off:** same but `R1 = 100 kΩ`, `R2 = 1 kΩ` → `VBB = 0.1188 V ≤ VBE` → `IC = 0`,
  `VC = 12 V`.
- **`RE = 0`:** same but `RE = 0` → exact `IB = 170 µA`, `IC = 25.56 mA`, `VE = 0`;
  the approximate model is skipped.

## Run it (Windows)

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Open <http://127.0.0.1:5000>. If port 5000 is taken, run with an explicit port:

```powershell
.venv\Scripts\python.exe -m flask --app app run --port 5001
```

## Run the tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

55 tests: formulas against hand-calculated golden values, region boundaries, input
validation, the comparison, SI formatting, and the four routes (GET, valid POST, invalid
POST → 400, cut-off POST).

## Files

```
app.py                      Flask app: routes, template filter, defaults
bjt_bias.py                 engineering logic — no Flask import
formatting.py               SI-prefix number formatting
templates/base.html         page shell and stylesheet link
templates/index.html        form, schematic, Q-point, comparison
static/style.css            the only stylesheet
tests/test_bjt_bias.py      formulas, regions, validation, comparison
tests/test_formatting.py    SI formatting edge cases
tests/test_app.py           route-level tests
requirements.txt            Flask and pytest version ranges
docs/superpowers/specs/     approved design
docs/superpowers/plans/     implementation plan
```

## Limitations

- DC only: no AC gain, frequency response, or transient analysis.
- No temperature sweep and no self-heating; `VBE` is a constant you supply.
- One BJT topology (NPN common-emitter, voltage-divider bias). No FET, no PNP, no
  circuit editor.
- The models are the ideal Shockley-free textbook ones — no Early effect, no
  recombination current, no parasitic resistances.
