# BJT CE Bias Calculator + ngspice Simulator — Lab 03/04

Flask web app ที่คำนวณจุดทำงานกระแสตรง (Q-point) ของทรานซิสเตอร์ NPN แบบ
common-emitter ได้ **3 วงจรไบอัส** จากเว็บเดียว:

| โหมด | วงจร | สมการหา I<sub>B</sub> | อินพุตที่ใช้ |
|---|---|---|---|
| `divider` | Voltage Divider Bias (ของเดิมจาก Lab 02) | `(VTH − VBE) / [RTH + (β+1)·RE]` | VCC, R1, R2, RC, RE, β, VBE |
| `fixed` | Fixed Bias | `(VCC − VBE) / RB` | VCC, RB, RC, β, VBE |
| `emitter` | Emitter Bias (แหล่งจ่ายเดียว) | `(VCC − VBE) / [RB + (β+1)·RE]` | VCC, RB, RC, RE, β, VBE |

โดย `VTH = VCC·R2/(R1+R2)` และ `RTH = R1·R2/(R1+R2)`

ค่าที่ได้จากทุกโหมด: `VB, VE, VC, VCE` (V), `IB, IC, IE` (A)
และ `IC` แสดงเป็น mA ด้วย ผลที่ได้อยู่ในรูป `dict` ที่มีคีย์และหน่วยตรงกันทุกโหมด
(`vb_v`, `ve_v`, `vc_v`, `vce_v`, `ib_a`, `ic_a`, `ie_a`, `ib_ua`, `ic_ma`,
`ie_ma`, `region`, `warnings`, ...)

Lab 04 เพิ่มหน้า `/simulator` สำหรับ CE voltage-divider หนึ่งวงจรที่รันจริงด้วย
ngspice `.op`, `.ac`, `.tran` ส่วน `/` ยังเป็น DC calculator แบบประมาณจาก Lab 03
เหมือนเดิม และผล SPICE กับผล Analytical ถูกแยกป้ายชื่อไว้เสมอ

---

## วิธีเลือกวงจร

1. เปิดเว็บ แล้วใช้ dropdown **Bias circuit** ด้านบน เลือกโหมดแล้วกด
   **Apply circuit** — หน้าเว็บจะโหลดใหม่และโชว์เฉพาะช่องที่โหมดนั้นใช้
   (เช่น Fixed ไม่มีช่อง R1/R2/RE, Emitter มี RB และ RE)
2. กรอกค่าตามหน่วยบนฟอร์ม ( Resistance เป็น **Ω**: `1 MΩ = 1000000 Ω`,
   `1 kΩ = 1000 Ω`) แล้วกด **Calculate DC Bias**
3. การ์ด **Circuit: Common-Emitter Amplifier** จะแสดงภาพวงจร SVG ของโหมดนั้น
   พร้อมค่าตัวต้านทานที่กรอก (Divider มี R1/R2/RE, Fixed มี RB และ emitter
   ต่อกราวด์ตรง ๆ, Emitter มี RB และ RE) — ใช้สไตล์การ์ดสีเดียวกันทั้ง 3 แบบ
4. ผลและข้อความเตือนจะระบุโหมดที่เลือกเสมอ และถ้าอินพุตผิด ช่องผลจะเป็น
   `—` ทั้งหมด ไม่โชว์ผลของรอบก่อน

ไม่มี JavaScript ในหน้าเว็บ — การเปลี่ยนโหมดเป็น GET ธรรมดา
(`/?mode=fixed`) และการคำนวณเป็น POST พร้อม hidden field `mode`

## Inputs

| Field | ความหมาย | หน่วย | กฎ |
|---|---|---|---|
| `VCC` | แหล่งจ่าย | V | > 0, ≤ 1000 |
| `RB` | ตัวต้านทานเบส (Fixed/Emitter) | Ω | > 0, 10⁻⁶ … 10⁹ |
| `R1`, `R2` | ตัวแบ่งแรงดัน (Divider) | Ω | > 0, 10⁻⁶ … 10⁹ |
| `RC` | ตัวต้านทานคอลเลกเตอร์ | Ω | > 0, 10⁻⁶ … 10⁹ |
| `RE` | ตัวต้านทานอีมิเตอร์ (Divider/Emitter) | Ω | 0 หรือ 10⁻⁶ … 10⁹ |
| `β` | current gain | — | 1 … 100000 |
| `VBE` | แรงดันเบส–อีมิเตอร์ | V | ≥ 0 และ < VCC |

อินพุตผิด → HTTP 400, แสดงข้อความข้างช่องนั้น และเก็บค่าที่กรอกไว้แก้ได้
โหมดที่ไม่รู้จักถูกปฏิเสธ (ไม่เดาว่าเป็น Divider)

## Region rules

| Region | เงื่อนไข | การแสดงผล |
|---|---|---|
| Active | VCE ≥ 1.0 V | แสดงผลปกติ |
| Near saturation | 0.2 V ≤ VCE < 1.0 V | เตือนว่า Q-point ไวต่อ β และ VBE |
| Saturation | VCE < 0.2 V | เตือนว่าแบบจำลอง forward active อาจใช้ไม่ได้ |
| Cut-off | IB ≤ 0 | เตือนว่าแบบจำลอง forward active อาจใช้ไม่ได้ |

Divider ยังคงมีตาราง **Exact vs Approximate** แบบ Lab 02 (เทียบ Thevenin
แบบ finite β กับวิธีประมาณ `IB ≈ 0`) และค่าอ้างอิง IC(sat)/forced β
เหมือนเดิมทุกประการ

## ติดตั้ง ngspice 47 (Windows)

ใช้ ngspice 47 Windows 64-bit (`ngspice-47_64.7z`) จากโฟลเดอร์ release ของ
ngspice บน SourceForge แล้วแตกไฟล์ด้วย `py7zr` (ติดตั้งชั่วคราวนอก
`requirements.txt`):

```powershell
.venv\Scripts\python.exe -m pip install py7zr
.venv\Scripts\python.exe -c "import py7zr; py7zr.unpack_7zarchive(r'C:\Users\<you>\Downloads\ngspice-47_64.7z', r'C:\Users\<you>\AppData\Local\ngspice-47')"
```

ตำแหน่งที่โปรแกรมคาดหวังคือ `%LOCALAPPDATA%\ngspice-47\Spice64\bin\ngspice.exe`
ถ้าเก็บที่อื่นให้ตั้ง环境变量 `NGSPICE_EXE` ให้ชี้ถึงไฟล์ `.exe` หรือเพิ่มโฟลเดอร์
ลงใน `PATH` (ลำดับค้นหาคือ `NGSPICE_EXE` → `PATH` → ตำแหน่งด้านบน) binary
ของ ngspice ไม่ได้ Commit ลง repository

> บน build Windows นี้ `ngspice --version` ไม่พิมพ์ข้อความ โปรแกรมจึงอ่านเวอร์ชันจาก
> บรรทัด `Command:` ใน ASCII raw ของผลรันจริง เช่น
> `ngspice-47, Build Aug 11 2026   13:49:23`

## Run it (Windows)

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m flask --app app run
```

เปิด <http://127.0.0.1:5000> สำหรับ Lab 03 และ <http://127.0.0.1:5000/simulator>
สำหรับ Lab 04 ถ้าพอร์ต 5000 ถูกใช้ ให้เปลี่ยนพอร์ต:

```powershell
.venv\Scripts\python.exe -m flask --app app run --port 5001
```

## Run the tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

ตอนนี้มี **102 tests** (71 tests เดิมของ Lab 03 บวกชุด adapter/validation/parser/
chart/route ของ Lab 04) ผ่านทั้งหมด — หลักฐานว่าโหมด Divider เดิมไม่เสียจากการเพิ่ม simulator
บาง test (เช่น `test_simulate_changes_with_input` และ route test ที่คาด `Success`)
เรียก ngspice จริง ไม่ได้ mock ถ้าไม่ติดตั้ง engine ตามข้างบน ชุดทดสอบจะไม่ผ่าน

## Browser acceptance (A1–A5)

ค่าอ้างอิงอิสระคำนวณด้วย [`docs/reference_calculation.py`](docs/reference_calculation.py)
ซึ่ง **ไม่ import** `app.py`, `bjt_bias.py` หรือ `dc_bias.py` รายละเอียดและการทวนผล
อยู่ใน [`docs/validation.md`](docs/validation.md)

ใช้ร่วมกันทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`<br>
เกณฑ์ผ่าน: `|ΔIC| ≤ 0.01 mA` และ `|ΔVCE| ≤ 0.02 V` เมื่อเทียบค่าที่หน้าเว็บแสดง
(3 significant figures) กับค่าอ้างอิงที่ยังไม่ปัดเศษ

| กรณี | อินพุตที่กรอกจริง | ค่าคาดหมาย (มีหน่วย) | ผลจริงที่เห็นบนหน้าเว็บ (มีหน่วย) | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| **A1 · Divider (โหมดเดิม)** | `VCC=12, R1=100000, R2=22000, RC=2200, RE=1000, β=100, VBE=0.7` | `IC=1.229858 mA`, `VCE=8.052155 V` | `IC = 1.23 mA`, `VCE = 8.05 V`, `VBB = 2.16 V`, `IB = 12.3 µA`; `Active region approximation OK` | OpenCode Browser | **PASS** |
| **A2 · Fixed** | `VCC=12, RB=1000000, RC=2200, β=100, VBE=0.7` (**ไม่มีช่อง RE**) | `IC=1.130000 mA`, `VCE=9.514000 V` | `IC = 1.13 mA`, `VCE = 9.51 V`, `VE = 0 V`, `IB = 11.3 µA`; `Forward-active region OK` | OpenCode Browser | **PASS** |
| **A3 · Emitter** | `VCC=12, RB=1000000, RC=2200, RE=1000, β=100, VBE=0.7` | `IC=1.026340 mA`, `VCE=8.705450 V` | `IC = 1.03 mA`, `VCE = 8.71 V`, `VE = 1.04 V`, `IB = 10.3 µA`; `Forward-active region OK` | OpenCode Browser | **PASS** |
| **A4 · เปลี่ยนค่าเดียวจาก A3** | Emitter · เหมือน A3 ทุกประการ เปลี่ยนเฉพาะ `RE=2000` | ทำนายว่า **IC ลดลง** เพราะ `(β+1)·RE` ในตัวหารเพิ่มขึ้น; ค่าอ้างอิง `IC=0.940100 mA`, `VCE=8.032779 V` | `IC = 940 µA` (ลดจาก `1.03 mA`), `IB = 9.4 µA` (ลดจาก `10.3 µA`), `VCE = 8.03 V` → ทิศทางตรงตามทำนาย | OpenCode Browser | **PASS** |
| **A5 · อินพุตผิด** | Fixed · `RB=0` (ที่เหลือเหมือน A2) | มีข้อความให้แก้ RB, เว็บไม่ล่ม, ไม่โชว์ผลเดิมเป็นผลรอบนี้ | ข้อความถัดจากช่อง RB: `must be greater than 0`; status `Check the highlighted inputs`; ช่องผลทั้ง 7 ช่องเป็น `—` หมด | OpenCode Browser | **PASS** |

ตรวจเกณฑ์ตัวเลขเพิ่มได้:

| กรณี | \|ΔIC\| (mA) | \|ΔVCE\| (V) | ผล |
|---|---:|---:|---|
| A1 | 0.000142 | 0.002155 | ผ่าน |
| A2 | 0.000000 | 0.004000 | ผ่าน |
| A3 | 0.003660 | 0.004550 | ผ่าน |
| A4 | 0.000100 | 0.002779 | ผ่าน |

### หลักฐานจากหน้าเว็บ

ข้อความผลด้านบนคัดมาจาก accessibility snapshot ของหน้าเว็บหลังกรอกฟอร์มและกด
**Calculate DC Bias** จริง ไม่ได้อ่านจากโค้ด และมีภาพหน้าจอแนบอย่างน้อย 1 กรณี:

- **A3** — เห็น `IC = 1.03 mA`, `VCE = 8.71 V`:

  ![A3 Emitter Bias](docs/evidence/A3-emitter-bias.png)

- **A5** — เห็น `must be greater than 0` และผล `—` ทุกช่อง:

  ![A5 invalid RB](docs/evidence/A5-invalid-rb.png)

- ภาพวงจรที่ใช้ตรวจทุกโหมด:
  [Divider](docs/evidence/schematic-divider-bias.png) ·
  [Fixed](docs/evidence/schematic-fixed-bias.png) ·
  [Emitter](docs/evidence/schematic-emitter-bias.png)

### เครื่องมือที่ใช้ / เหตุผลที่เปลี่ยน

- ตรวจจริงด้วย **OpenCode Browser**: เปิด URL จริง ใช้ dropdown **Bias circuit →
  Apply circuit** กรอกช่องในฟอร์มด้วยเครื่องมือ fill แล้วกด **Calculate DC Bias**
- **Playwright MCP: NOT RUN** — ไม่ได้ตั้งค่า MCP server ในเครื่องนี้ จึงใช้
  **OpenCode Browser** แทนตามเงื่อนไขในใบงาน (ให้คะแนนการตรวจผลเท่ากันทุกวิธี)
- ไม่ได้ใช้ `curl` หรืออ่านโค้ดแทนการรันเบราว์เซอร์ และไม่พบ error/warning
  ใน browser console ระหว่างรอบตรวจ

## Lab 04 — CE Amplifier Simulator

หน้า `/simulator` ใช้วงจรอ้างอิงเดียวตามใบงาน: `VCC=12 V`, `R1=100 kΩ`,
`R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `RL=10 kΩ`, `Cin=Cout=10 µF`,
แหล่งสัญญาณ `10 mV peak / 1 kHz` ค่าเหล่านี้เป็น default ในฟอร์มและแก้ได้
(generator ส่ง `VIN in 0 DC 0 AC 1 SIN(0 <amplitude> <frequency>)`)

หน่วยที่ป้อนเป็นหน่วยฐาน: Ω สำหรับตัวต้านทาน, F สำหรับ capacitor, V สำหรับ
VCC/amplitude, Hz สำหรับความถี่ ทุกค่าถูก validate ก่อนสร้าง netlist และ
ngspice ถูกเรียกด้วย `subprocess.run([...], shell=False, timeout=20)` ใน temporary
directory แยกต่อการรัน ผล `.op/.ac/.tran` ถูกอ่านจาก ASCII raw จริง แล้วค่อยวาด
SVG บนเซิร์ฟเวอร์ ไม่มีค่ากราฟหรือ gain ที่ hard-code ไว้ล่วงหน้า

ขอบเขตอินพุตที่ validator ยอมรับ: ทุกค่าต้องเป็น finite และมากกว่า 0;
`VCC ≤ 1000 V`, `amplitude ≤ 1 V`, `frequency ≤ 1 MHz` ส่วน R/C ทุกตัว
(รวม R1–RL, Cin, Cout) อยู่ในช่วง `1e-6` ถึง `1e9` ในหน่วยฐาน (Ω/F)
ค่าขาดหรือผิดประเภทจะถูกปฏิเสธก่อนสร้าง netlist

BJT model ที่ใช้คือ **model การสอน** ไม่ใช่ส่วนประกอบจริงรุ่นใดรุ่นหนึ่ง:

```spice
.model QNPN_TEACH NPN(IS=1E-14 BF=100 BR=0.1 VAF=100 CJE=25p CJC=5p TF=0.3n)
```

node ใน netlist คือ `vcc, base, collector, emitter, in, out` โดย `Vin` วัดที่
node `in` (หลังแหล่งสัญญาณก่อน `Cin`) และ `Vout` วัดที่ node `out` (หลัง `Cout`
บน `RL`) กราฟ AC แกนเป็น Hz/dB/deg กราฟ transient แกนเป็น s/V และมี legend
`Gain`, `Phase`, `Vin`, `Vout` กำกับ

แถบสถานะแสดงทั้ง engine (`ngspice`), เวอร์ชันจาก raw header, model และ
`Success/Error` ตาราง DC แยกคอลัมน์ **ngspice (SPICE)** กับ **Analytical (Lab 3)**
อย่างชัดเจน ฝั่ง analytical ใช้สมการประมาณเดิมด้วย `β=100`, `VBE=0.7 V` เท่านั้น
สำหรับ AC/transient หน้าเว็บระบุว่าตาราง analytical ไม่มีผล ถ้าสolver ล้มเหลว
หรืออินพุตผิด สถานะจะเป็น Error และไม่มีการแสดงกราฟเก่าค้างอยู่

หมายเหตุสำหรับผู้เรียก `spice_engine` โดยตรง: แผนเดิมเขียนว่า `parse_op(log)`
แต่ ngspice 47 ในเครื่องนี้เขียน node voltage ของ `.op` ไว้ใน ASCII raw file ไม่ใช่ log
จึงเป็น `parse_op(raw, *, rc)` และใช้ร่วมกับ `parse_ac(raw)` / `parse_tran(raw)` เหมือนกัน
(path ของ log/raw ใน `RunResult` เป็นข้อมูลวินิจฉัยภายในรัน temporary directory
ที่ถูกลบแล้ว ไม่ควรใช้เปิดไฟล์ภายหลัง)

ดูวิธีตรวจ B1–B8, หลักฐานจาก browser และข้อจำกัดได้ที่
[`docs/validation.md`](docs/validation.md)

### AI เขียน vs นักศึกษาตรวจ

- **AI เขียน/แก้:** `spice_engine.py`, `charts.py`, หน้า `/simulator`, CSS, test
  ของ Lab 04 และเอกสารนี้
- **AI ยังไม่ได้ตรวจแทนนักศึกษา:** ความถูกต้องของสมการและหน่วยเทียบใบงาน,
  ที่มาของ BJT model, log/raw ของ ngspice ที่รันบนเครื่องผู้ใช้, และการยืนยัน
  ผล B1–B8 จาก browser จริงตามตารางใน `docs/validation.md`

## Files

```
app.py                      Flask routes: Lab 03 `/` และ Lab 04 `/simulator`
bjt_bias.py                 วิศวกรรมเดิมของ Lab 02 (Divider, exact/approx, region)
dc_bias.py                  solve_fixed/solve_emitter/solve_divider + validator
formatting.py               SI-prefix number formatting
spice_engine.py             validate → netlist → subprocess ngspice → parse raw
charts.py                   SVG Bode/waveform จาก parsed vectors เท่านั้น
templates/index.html        mode selector, ฟอร์มตามโหมด, ผลลัพธ์, การตรวจสอบ
templates/simulator.html    ฟอร์ม CE, status strip, กราฟ, ตาราง SPICE vs Analytical
static/style.css            stylesheet ร่วมของทั้งสองหน้า
tests/                      102 tests: 71 เดิม + 31 ของ Lab 04
docs/validation.md          A1–A5 และ B1–B8, ค่าอ้างอิง, หลักฐาน, บทบาท MCP
docs/reference_calculation.py   สคริปต์คำนวณค่าอ้างอิงอิสระของ Lab 03
docs/evidence/              ภาพหน้าจอและ log ตัวอย่างจากเบราว์เซอร์/ngspice จริง
docs/superpowers/           spec/plan ของ Lab 02 และ Lab 04
requirements.txt            Flask, pytest (ไม่รวม ngspice binary)
```

## สิ่งที่ AI เขียน vs สิ่งที่ตรวจ

- **AI เขียน:** `dc_bias.py` (ฟังก์ชัน Fixed/Emitter, validator ตามโหมด, รูป dict ร่วม),
  ส่วนที่เลือกโหมดใน `app.py`, โครงฟอร์ม/ผลใน `index.html`, CSS ของ mode bar
- **ผู้สอน/นักศึกษาตรวจ:** สมการเทียบใบงาน (IB ของทั้ง 3 วงจร และ VE ของ Fixed ที่เป็น 0),
  หน่วย Ω/A → V/mA, ค่าอ้างอิงอิสระ A1–A4, ว่า Divider ให้ผลเดิม (ชุดทดสอบ 71 tests),
  และผลจริงจากเบราว์เซอร์ A1–A5

## Submission

- GitHub: <https://github.com/JirapatMax/Gitlab>
- งาน Lab 3 อยู่บน branch `main`
- Commit SHA ของงานนี้ดูได้จาก `git log -1 --format=%H` หรือจากคำตอบที่ส่งพร้อมตาราง A1–A5

## Limitations

- Lab 03 ยังเป็น DC แบบประมาณ ส่วน Lab 04 รัน SPICE ได้เฉพาะ CE voltage-divider
  วงจรอ้างอิงเดียว ไม่มี AC/transient สำหรับ Fixed/Emitter และไม่มี circuit editor
- ฝั่ง analytical ของ Lab 04 ตายตัวที่ `β=100`, `VBE=0.7 V` เพื่อใช้เทียบกับ model
  การสอน ไม่ใช่ค่าที่อ่านจาก ngspice
- SPICE ใช้ `QNPN_TEACH` ซึ่งเป็น teaching model ไม่ใช่ข้อมูลของ transistor รุ่นจริง
  และไม่มี temperature sweep, self-heating, mismatch หรือ Monte Carlo
- AC sweep อยู่ในช่วง 0.1 Hz–10 MHz (100 points/decade) และ transient รัน 5 period
  ของความถี่ที่ป้อน ถ้าไม่มีจุดตัด −3 dB ในช่วง sweep หน้าเว็บจะแสดง
  `not determined in sweep range` แทนการแต่งค่า f<sub>high</sub>
- ต้องมี ngspice 47 ติดตั้งนอก repo; repository นี้ไม่ได้รวม binary หรือ large run files
- ใช้ Flask development server เหมาะสำหรับแล็บ/รันในเครื่อง ไม่ใช่ production deployment
- ในย่าน cutoff/saturation ของหน้า Lab 03 แสดงผลของแบบจำลอง *forward active*
  ไว้ให้ดูพร้อมข้อความเตือน ไม่ได้คำนวณค่าจริงของ cutoff/saturation ให้
