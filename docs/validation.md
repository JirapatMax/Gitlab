# Lab 03 — Browser acceptance record (A1–A5)

## สภาพแวดล้อมและวิธีตรวจ

- เว็บที่ตรวจ: `http://127.0.0.1:5000/` (Flask + Python, รันจาก `.venv`)
- วิธีตรวจที่ใช้จริง: **OpenCode Browser** (เครื่องมือเบราว์เซอร์ใน OpenCode Desktop)
  เปิด URL จริง เปลี่ยนโหมดผ่าน dropdown **Bias circuit → Apply circuit** กรอกช่อง
  ในฟอร์มด้วยเครื่องมือ fill แล้วกด **Calculate DC Bias** จริงทุกกรณี
- **Playwright MCP: NOT RUN** — ไม่ได้ตั้งค่า MCP server ในเครื่องนี้ จึงใช้
  OpenCode Browser แทนตามเงื่อนไขในใบงาน (ให้คะแนนการตรวจผลเท่ากันทุกวิธี)
- ไม่ได้ใช้ `curl` หรืออ่านโค้ดแทนการรันเบราว์เซอร์ และไม่ได้แก้ไฟล์โปรแกรม
  ระหว่างรอบตรวจรอบแรก
- หน่วยบนฟอร์มเป็น **Ω** ดังนั้น `1 MΩ = 1000000 Ω`, `1 kΩ = 1000 Ω`
  (ไม่ต้องแปลงหน่วยเพิ่ม เพราะ parser อ่านเป็น Ω อยู่แล้ว)

## ค่าอ้างอิงอิสระ

คำนวณจากสมการในใบงานด้วยสคริปต์แยกต่างหาก
[`docs/reference_calculation.py`](reference_calculation.py) ซึ่ง **ไม่ import**
`app.py`, `bjt_bias.py` หรือ `dc_bias.py` — จึงเป็นค่าที่เป็นอิสระจากโปรแกรมที่ตรวจ

ใช้ร่วมกันทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`

```
Fixed   : IB = (VCC − VBE) / RB
Emitter : IB = (VCC − VBE) / [RB + (β + 1)·RE]
Divider : VTH = VCC·R2/(R1+R2),  RTH = R1·R2/(R1+R2)
          IB  = (VTH − VBE) / [RTH + (β + 1)·RE]
ทุกโหมด : IC = β·IB,  IE = (β+1)·IB,  VE = IE·RE,
          VB = VE + VBE,  VC = VCC − IC·RC,  VCE = VC − VE
          (Fixed ใช้ RE = 0 → VE = 0)
```

| กรณี | IC อ้างอิง (ไม่ปัดเศษ) | VCE อ้างอิง (ไม่ปัดเศษ) |
|---|---:|---:|
| A1 Divider | 1.229858146 mA | 8.052155351 V |
| A2 Fixed | 1.130000000 mA | 9.514000000 V |
| A3 Emitter | 1.026339691 mA | 8.705449591 V |
| A4 Emitter (RE=2 kΩ) | 0.940099834 mA | 8.032778702 V |

เกณฑ์: ผลต่างไม่เกิน **0.01 mA** สำหรับ IC และ **0.02 V** สำหรับ VCE
เมื่อเทียบค่าที่หน้าเว็บแสดง (3 significant figures) กับค่าอ้างอิงที่ยังไม่ปัดเศษ

## ผล A1–A5

| กรณี | โหมดและอินพุตที่กรอกจริง | คาดหมายก่อนรัน | เห็นจริง (พร้อมหน่วย) | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| **A1 · โหมดเดิม** | Divider · VCC=12, R1=100000, R2=22000, RC=2200, RE=1000, β=100, VBE=0.7 | ต้องตรงกับ Lab 02 ก่อนแก้; IC=1.229858 mA, VCE=8.052155 V | `IC = 1.23 mA`, `VCE = 8.05 V`, `VBB = 2.16 V`, `IB = 12.3 µA`; status `Active region approximation OK` | OpenCode Browser | **PASS** |
| **A2 · Fixed** | Fixed · VCC=12, RB=1000000, RC=2200, β=100, VBE=0.7 (**ไม่มีช่อง RE**) | IC=1.130000 mA, VCE=9.514000 V | `IC = 1.13 mA`, `VCE = 9.51 V`, `VE = 0 V`, `IB = 11.3 µA`; status `Forward-active region OK` | OpenCode Browser | **PASS** |
| **A3 · Emitter** | Emitter · VCC=12, RB=1000000, RC=2200, RE=1000, β=100, VBE=0.7 | IC=1.026340 mA, VCE=8.705450 V | `IC = 1.03 mA`, `VCE = 8.71 V`, `VE = 1.04 V`, `IB = 10.3 µA`; status `Forward-active region OK` | OpenCode Browser | **PASS** |
| **A4 · เปลี่ยนค่าเดียว** | Emitter · เหมือน A3 ทุกประการ เปลี่ยนเฉพาะ `RE` เป็น `2000` | ทำนายว่า **IC ลดลง** เพราะ `(β+1)·RE` ในตัวหารเพิ่มขึ้น → IB ลดลง → IC ลดลง | `IC = 940 µA` (ลดจาก `1.03 mA`), `IB = 9.4 µA` (ลดจาก `10.3 µA`), `VCE = 8.03 V` → ทิศทางตรงตามทำนาย | OpenCode Browser | **PASS** |
| **A5 · อินพุตผิด** | Fixed · RB=0 (ที่เหลือเหมือน A2) | มีข้อความให้แก้ RB, เว็บไม่ล่ม, ไม่โชว์ผลเดิมเป็นผลรอบนี้ | ข้อความถัดจากช่อง RB: `must be greater than 0`; status `Check the highlighted inputs`; ช่องผลทั้ง 7 ช่องเป็น `—` หมด | OpenCode Browser | **PASS** |

### ตรวจเกณฑ์ตัวเลข

| กรณี | \|ΔIC\| (mA) | \|ΔVCE\| (V) | ผล |
|---|---:|---:|---|
| A1 | 0.000142 | 0.002155 | ผ่าน |
| A2 | 0.000000 | 0.004000 | ผ่าน |
| A3 | 0.003660 | 0.004550 | ผ่าน |
| A4 | 0.000100 | 0.002779 | ผ่าน |

ผลต่างทุกกรณีอยู่ใต้เกณฑ์ 0.01 mA และ 0.02 V

## หลักฐานจากหน้าเว็บ

- [`evidence/A3-emitter-bias.png`](evidence/A3-emitter-bias.png) — หน้า Emitter Bias
  ที่กรอก RB=1 MΩ, RE=1 kΩ แล้วกดคำนวณจริง เห็น `IC = 1.03 mA`, `VCE = 8.71 V`
- [`evidence/A5-invalid-rb.png`](evidence/A5-invalid-rb.png) — หน้า Fixed Bias ที่กรอก
  RB=0 เห็น `must be greater than 0` และผลเป็น `—` ทุกช่อง
- [`evidence/schematic-divider-bias.png`](evidence/schematic-divider-bias.png) — ภาพวงจร
  Voltage Divider Bias หลังปรับดีไซน์ (R1/R2 แบ่งแรงดัน Base, RC/RE ที่ขา C/E)
- [`evidence/schematic-fixed-bias.png`](evidence/schematic-fixed-bias.png) — ภาพวงจร
  Fixed Bias (RB ต่อจาก VCC ไป Base, Emitter ต่อกราวด์ตรง ๆ)
- [`evidence/schematic-emitter-bias.png`](evidence/schematic-emitter-bias.png) — ภาพวงจร
  Emitter Bias (RB ต่อ Base, RE ต่อ Emitter ลงกราวด์)
- ภาพวงจรทั้ง 3 ใช้สไตล์เดียวกัน: การ์ดพื้นหลังโทนฟ้า, เส้น VCC/Base/Collector/Emitter
  แยกสี, ป้ายค่าตัวต้านทานแบบ pill และสัญลักษณ์ NPN พร้อมลูกศร Emitter
- ข้อความผลข้างต้นคัดมาจาก accessibility snapshot ของหน้าเว็บหลังส่งฟอร์มจริง
  (ไม่ได้อ่านจากโค้ด)
- ไม่พบข้อความ error/warning ใน browser console ระหว่างรอบตรวจ

## ทวนผลเอง 1 รอบ (A3 → A4)

เปิดหน้า A3 อยู่แล้ว ยืนยันว่า hidden field `mode=emitter` และค่า
`vcc=12, rb=1000000, rc=2200, beta=100, vbe=0.7` เท่าเดิมจาก snapshot
ของฟอร์ม แล้วแก้เฉพาะช่อง `RE` จาก `1000` เป็น `2000` และกดคำนวณใหม่
สังเกตว่าหน้าเว็บแสดงโหมด Emitter เหมือนเดิม แต่ IB เปลี่ยน 10.3 → 9.4 µA
และ IC เปลี่ยน 1.03 mA → 940 µA แสดงว่าค่า RE ที่กรอกเดินทางถึงสมการจริง

เส้นทางข้อมูล: `ช่อง RE (name="re")` → `request.form` ใน `app.py` →
`parse_mode_inputs("emitter", raw)` แปลงสตรริงเป็นฟลอยด์ Ω →
`solve_emitter(vcc, rb, re, rc, beta, vbe)` →
`IB = (VCC−VBE)/(RB+(β+1)RE)` → `ie=(β+1)ib`, `ve=ie·re` →
`vc=VCC−ic·rc`, `vce=vc−ve` → `dict` → `templates/index.html`

## บทบาทของ MCP ในใบงานนี้

- **MCP (Model Context Protocol)** คือมาตรฐานที่ให้แอป AI รู้ว่ามีเครื่องมืออะไร
  เรียกใช้ได้ และรับผลกลับมา
- **OpenCode** เป็น MCP Client (แอปที่เอเจนต์ทำงานอยู่)
- **Playwright MCP** เป็น MCP Server ที่เปิดเครื่องมือควบคุมเบราว์เซอร์
  ให้เอเจนต์เรียกผ่าน MCP
- เส้นทางคำขอ: OpenCode → (MCP) → Playwright MCP → Browser → (HTTP) → Flask
  เส้นทางผลกลับ: Flask → (HTTP) → Browser → Playwright MCP → (MCP) → OpenCode
- สองเส้นทางนี้ต่างกัน: Browser คุยกับ Flask ด้วย HTTP ส่วน OpenCode คุยกับ
  Playwright ด้วย MCP ดังนั้น Flask ไม่ต้องติดตั้ง Playwright ใน
  `requirements.txt` แต่อย่างใด
- รอบนี้ใช้ OpenCode Browser แทน (เครื่องมือเบราว์เซอร์ที่มีอยู่แล้ว) จึงต้อง
  ระบุวิธีจริงว่าเป็น OpenCode Browser ไม่ใช่ Playwright MCP ตามตารางด้านบน

## คำถามปิด Lab

> ถ้าตัวเลขคำนวณมือถูก แต่เปลี่ยน RE แล้วผลบนหน้าเว็บไม่เปลี่ยน
> จะตรวจค่าที่ส่งจากฟอร์มและค่าที่เข้าไปในฟังก์ชันอย่างไร?

1. อ่าน snapshot ของฟอร์มหลังเปลี่ยน RE ตรวจว่าโหมดยังเป็น Emitter
   และช่องที่แก้มี `name="re"` จริง (ไม่ใช่ไปแก้ช่องอื่น)
2. ดู hidden field `mode` ว่ายังส่ง `emitter` อยู่ — ถ้าเป็น `divider`
   ฟอร์มจะส่ง R1/R2/RE เข้าเส้นทางผิด
3. กดคำนวณแล้วดู network request ว่าเป็น POST จริงและ body มี `re=2000`
   (ไม่ใช่แค่แก้ค่าในช่องแล้วไม่ได้ submit)
4. ไล่ต่อที่ `app.py`: `parse_mode_inputs` ต้องคืน `values["re"] = 2000.0`
   และต้องเรียก `solve_emitter` ไม่ใช่ `solve_fixed`
5. ถ้าค่าเข้าฟังก์ชันถูกแต่ผลไม่เปลี่ยน ให้ตรวจว่าฟังก์ชันใช้ `re` ในตัวหาร
   `(β+1)*re` และใช้ `re` ตอนคำนวณ `ve = ie*re` หรือไม่
6. สุดท้ายตรวจว่าหน้าเว็บอ่านผลจากรอบล่าสุด (`result`) ไม่ใช่ผลที่ค้างจากรอบก่อน
   วิธีสังเกตอย่างรวดเร็วคือดูว่า IB เปลี่ยนตาม RE หรือไม่ (A3→A4 ควรลดลง)

---

# Lab 04 — Browser acceptance record (B1–B8)

## สภาพแวดล้อมจริงที่ใช้ตรวจ

- เว็บ: Flask dev server ที่ `http://127.0.0.1:5001/` (`/` = Lab 03,
  `/simulator` = Lab 04) รันจาก Python virtualenv ของโปรเจกต์
- วิธีตรวจจริง: **OpenCode Browser** — เปิด tab ใหม่ต่อเคส, อ่าน snapshot ก่อน,
  เลือก/กรอกผ่าน tool, กดปุ่มจริง, อ่านค่าจาก DOM หลัง POST, ดู network request
  (method/body/status) และ browser console ทุกเคส
- **Playwright MCP: NOT RUN** — ไม่ได้ configure MCP server ในเครื่องนี้ จึงไม่มี
  tool `playwright_*` ให้ OpenCode เรียก ใช้ OpenCode Browser แทนตามที่ใบงานอนุญาต
- **Impeccable: NOT RUN** — skill ไม่มีอยู่ใน harness นี้ จึงไม่มี before/after
  จาก Impeccable; การดู UI ทำด้วย OpenCode Browser และแก้เฉพาะ缺陷ที่พบจริง
- ngspice version จาก raw header ของการรันจริง:
  `ngspice-47, Build Aug 11 2026   13:49:23` (`ngspice --version` ไม่พิมพ์输出บน
  Windows build นี้)
- BJT model: `QNPN_TEACH` =
  `.model QNPN_TEACH NPN(IS=1E-14 BF=100 BR=0.1 VAF=100 CJE=25p CJC=5p TF=0.3n)`
  เป็น teaching model ไม่ใช่ part จริง
- ไม่พบ error/warning ใน browser console ระหว่างรอบ B1–B8

## ผล B1–B8

| Case | Method | Input | Expected/Reference | Observed | Evidence | Status |
|---|---|---|---|---|---|---|
| **B1 · Regression** | OpenCode Browser, tab ใหม่, เลือกโหมดแล้ว fill/submit จริง 3 โหมด | Divider `12,100000,22000,2200,1000,100,0.7`; Fixed `12,1000000,2200,100,0.7`; Emitter `12,1000000,2200,1000,100,0.7` | ตรง A1–A3 ในตาราง Lab 03 ด้านบน | Divider: `VBB=2.16 V, VE=1.24 V, VC=9.29 V, VCE=8.05 V, IB=12.3 µA, IC=1.23 mA`, `Active region approximation OK` · Fixed: `VB=700 mV, VE=0 V, VC=9.51 V, VCE=9.51 V, IB=11.3 µA, IC=1.13 mA`, `Forward-active region OK` · Emitter: `VB=1.74 V, VE=1.04 V, VC=9.74 V, VCE=8.71 V, IB=10.3 µA, IC=1.03 mA`, `Forward-active region OK` | network POST `/` status 200 และ `.qrow` จาก DOM ของแต่ละโหมด | **PASS** |
| **B2 · DC SPICE** | tab ใหม่ `/simulator`, เลือก DC, submit จริง | `VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, RL=10k, Cin=Cout=10µF, amplitude=0.01, frequency=1000` | SPICE ต้องแสดง VB/VE/VC/VCE/IC พร้อม status, engine, model และแยกจาก Analytical (Lab 3) | `Success`; `Engine: ngspice · ngspice-47, Build Aug 11 2026 13:49:23`; `Model: QNPN_TEACH`; SPICE `VB=1.95 V, VE=1.29 V, VC=9.19 V, VCE=7.9 V, IC=1.28 mA, VBE=660 mV` เทียบ Analytical `1.94/1.24/9.29/8.05 V, 1.23 mA` | [`simulator-dc-success.jpeg`](evidence/simulator-dc-success.jpeg), [`ngspice-dc-run.txt`](evidence/ngspice-dc-run.txt) (netlist + log + raw header), POST body มีครบ 10 field | **PASS** |
| **B3 · Change RE** | tab ใหม่, แก้เฉพาะ `RE=2000` แล้ว submit DC ซ้ำ | เหมือน B2 ทุกประการ ยกเว้น `RE` | Operating point ต้องเปลี่ยน ไม่ใช่ค่าค้างจาก B2 | จาก B2 `IC=1.28 mA, VCE=7.9 V` → B3 `VB=2.05 V, VE=1.4 V, VC=10.5 V, VCE=9.06 V, IC=696 µA, VBE=644 mV`; POST body `...&re=2000&...` | POST body/status 200 และตาราง SPICE vs Analytical จาก DOM | **PASS** |
| **B4 · AC** | tab ใหม่, เลือก `AC sweep` แล้ว submit จริง | ค่าเดียวกับ B2 (RE=1000) | Bode ต้องมี Frequency/Gain(dB)/Phase(deg) จาก run จริง | `Success`; `Peak gain 4.86 dB`, `f_low=1.82 Hz`, `f_high=not determined in sweep range`; SVG `data-points="801"`, 2 polyline, label `Gain (dB)`, `Phase (deg)`, `Frequency (Hz)`; POST body ครบ 10 field, status 200 | [`simulator-ac-bode.jpeg`](evidence/simulator-ac-bode.jpeg) + network body/DOM chart metadata | **PASS** |
| **B5 · Transient** | tab ใหม่, เลือก `Transient waveform` แล้ว submit จริง | `10 mV peak / 1 kHz`, ค่าที่เหลือเหมือน B2 | เห็น Vin/Vout ตามเวลา มีหน่วย s/V และสัญญาณกลับเฟส | `Success`; `tstop=0.005 s`, `Vin peak=10 mV`, `Vout peak=17.5 mV`; SVG `data-points="508"`, 2 polyline, label `Vin`, `Vout`, `V`, `s`; correlation ของ y-series บนกราฟ = **−0.999997** → กลับเฟสตาม CE | [`simulator-tran-10mv.jpeg`](evidence/simulator-tran-10mv.jpeg) + DOM polyline/correlation | **PASS** |
| **B6 · Change Source** | tab ใหม่, เลือก transient ก่อน, fill `amplitude=0.02`, submit จริง | เหมือน B5 ทุกประการ ยกเว้น amplitude `0.01 → 0.02` | waveform ต้องเปลี่ยนตาม amplitude ไม่ใช่กราฟ hard-code | `Vin peak 10 mV → 20 mV`, `Vout peak 17.5 mV → 35 mV`; chart ยังเป็น `data-points="508"`/2 polyline; POST body `...&amplitude=0.02&...`, status 200 | [`simulator-tran-20mv.jpeg`](evidence/simulator-tran-20mv.jpeg) (รัน amplitude 0.02) + network body | **PASS** |
| **B7 · Invalid / Fail** | tab ใหม่, fill `RE=0`, submit จริง | DC พร้อม `RE=0` | แจ้ง error, ไม่ค้าง, ไม่โชว์ success ปลอม | POST `/simulator` **400**; ข้อความข้างช่อง RE `must be greater than 0`; status `Not run yet` พร้อม `Check the highlighted inputs`; `svg.chart` count **0**; ช่อง RE ยังเป็น `0` ให้แก้ | [`simulator-invalid-re.jpeg`](evidence/simulator-invalid-re.jpeg) + network 400 | **PASS** |
| **B8 · UI** | tab จริง + iframe ขนาด ~390px เปิดหน้าเดิมและหน้า AC success | desktop 800×654, mobile 388×898 และ 390×1050 | ปุ่ม/กราฟ/หน่วยอ่านง่าย ไม่มีเนื้อหาสำคัญถูกตัด | desktop `scrollWidth=800`, ปุ่มกว้าง 119/329 px, chart ไม่ overflow; mobile_initial `innerWidth=388, scrollWidth=388`; mobile AC `innerWidth=390, scrollWidth=375`, ปุ่ม 119/309 px, chart 801 points, status `Success`; console สะอาด | [`simulator-desktop.jpeg`](evidence/simulator-desktop.jpeg), [`simulator-mobile-390.jpeg`](evidence/simulator-mobile-390.jpeg), [`simulator-mobile-ac.jpeg`](evidence/simulator-mobile-ac.jpeg) | **PASS** |

## หลักฐานว่ากราฟมาจาก ngspice จริง (B4/B5/B6)

- ทุกเคสกดปุ่ม submit จริงแล้วดู **network request body** ว่าเป็น `POST /simulator`
  พร้อมค่าที่กรอก (ไม่ใช่แค่แก้ DOM) และ response status 200
- after-POST DOM มี `svg.chart` ที่ `data-points` ตรงกับจำนวน vector ที่ parser อ่านได้
  (AC 801 จุด, transient 508 จุด) และมี `<polyline>` สองเส้นสำหรับ gain/phase หรือ
  Vin/Vout — ไม่มีค่าจำนวนจุดหรือ gain ถูก hard-code ใน template
- ข้อความ `Peak gain 4.86 dB`, `f_low=1.82 Hz`, `Vin/Vout peak` มาจาก dict ที่
  `spice_engine.simulate()` คืนหลังอ่าน raw file ของรันนั้น
- [`ngspice-dc-run.txt`](evidence/ngspice-dc-run.txt) บันทึก netlist, log และ raw
  header จากการรันจริงบนเครื่องนี้ รวมเวอร์ชัน `ngspice-47`
- B5 ตรวจทิศทางเฟสจากพิกัด polyline ที่ browser วาดจริง ได้ correlation −0.999997
- B6 เปลี่ยน amplitude เดียวแล้ว peak ของ Vin/Vout เปลี่ยนตาม (~2×) แสดงว่า
  ไม่ใช่กราฟที่ค้างหรือ mock

## ข้อบกพร่องที่พบระหว่างตรวจ และการแก้

- พบครั้งแรกใน B4: ปุ่ม **Run simulation** แถบด้านบนส่ง POST body เพียง
  `analysis=ac` → HTTP 400 `required` ทุกช่อง Root cause:ฟอร์มแถบด้านบนไม่มี
  hidden input สำหรับ 10 parameter ที่ฟอร์มด้านล่างใช้
- แก้ขั้นแรกด้วย regression test
  `tests/test_app_spice.py::test_analysis_selector_form_carries_current_parameters`
  (RED ก่อน → GREEN หลังเพิ่ม hidden input ใน `templates/simulator.html`) แล้ว restart
  server เพราะตอนนั้นรันแบบ debug off จึงยัง cache template เก่าอยู่
- ในการตรวจ branch รอบสุดท้าย พบว่าการใช้ hidden input สองชุดยังทำให้ state คลาดเคลื่อน
  (เลือก analysis ด้านบนแล้วกดปุ่มล่าง หรือแก้ค่าล่างแล้วกดปุ่มบน) จึงรวมเป็น
  **ฟอร์มเดียว** `id="sim-run-form"` โดย `<select>` และปุ่มด้านบนใช้ attribute
  `form="sim-run-form"` ไม่มี hidden input ซ้ำอีกต่อไป
- regression ใหม่: `test_analysis_selector_and_inputs_share_one_form` (RED → GREEN),
  `test_single_submission_uses_selected_analysis_and_edited_value`, และตรวจใน browser
  จริง: เลือก `Transient waveform` ด้านบน → แก้ amplitude เป็น `0.02` ในฟอร์มล่าง →
  กดปุ่มบน ได้ POST `analysis=tran&amplitude=0.02&...`, status 200, `Vin peak 20 mV`;
  อีกเคสเลือก `AC sweep` ด้านบนแล้วกดปุ่มล่างก็ได้ AC จริงเช่นกัน
- หลังแก้ B4 POST body มีครบ `analysis, vcc, r1, r2, rc, re, rl, cin, cout,
  amplitude, frequency` และ status 200; รันชุดทดสอบเต็มอีกครั้ง = **102 passed**
- parser fixtures ถูกเปลี่ยนจากตัวอย่างที่แต่งขึ้นเป็น `.raw` จริงของ ngspice 47 ที่
  ตัดเฉพาะบางจุด (ดู `tests/fixtures/README.md`) และมี test ตรวจหัว raw จริง
  `Command: ngspice-47` พร้อม `test_simulate_uses_real_ac_capture`

## ข้อจำกัดที่ยังต้องระบุให้ตรงความจริง

- รัน SPICE ได้เฉพาะ CE voltage-divider วงจรอ้างอิงเดียว; AC ของ Fixed/Emitter
  ไม่มีใน v1 นี้ และไม่มี circuit editor
- `QNPN_TEACH` เป็น teaching model ไม่ใช่ transistor รุ่นจริง ไม่มี temperature,
  mismatch, self-heating หรือ Monte Carlo
- AC sweep 0.1 Hz–10 MHz; ถ้าไม่มีจุดตัด −3 dB ในช่วงนี้ จะแสดง
  `not determined in sweep range` (B4 ไม่ได้แต่ง capping value)
- transient รัน 5 period ของความถี่ที่ป้อน (`tstop=0.005 s` ที่ 1 kHz)
- AC/transient ไม่มีตาราง analytical เทียบ เพราะ `dc_bias.py` คำนวณ DC เท่านั้น
-Playwright MCP และ Impeccable ไม่ได้รัน จึงไม่ควรอ้างว่ามีหลักฐานจากสองเครื่องมือนี้
