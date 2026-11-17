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
