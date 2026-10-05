# KeyCheck — Frontend

เว็บสำหรับถ่ายภาพคีย์บอร์ด แตะจุดอ้างอิง 4 จุด (กึ่งกลางช่อง Q, P, M, Z ตามตำแหน่ง) แล้วดูผลตรวจตำแหน่งคีย์แคป A–Z บนภาพ
สร้างจาก SvelteKit SPA template (Svelte 5 runes, Tailwind v4, TanStack Query, shadcn-svelte)

อ้างอิง: [Spec §10, §17](../docs/keycheck-technical-specification.md) · [API contract](../docs/api-contract.md) · [Web plan W3/W5](../docs/web-implementation-plan.md) · [Implementation plan P6](../docs/implementation-plan.md)

## หน้าจอ

| Route                       | หน้าที่                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| `/`                         | ขอบเขตที่รองรับ วิธีถ่าย ชื่อ Layout เปิดกล้อง / ถ่ายด้วยแอปกล้อง / เลือกไฟล์ → Preview → อัปโหลด |
| `/inspect?image=<image_id>` | แตะจุดอ้างอิงบนภาพที่ Backend จัด Orientation แล้ว (`CornerPicker`) → ส่งตรวจ                     |
| `/inspections/[id]`         | Poll ทุก 1.5 วินาที แสดงชื่อขั้นตอน → ผล: Summary, `ResultOverlay`, `SlotList`, คำแนะนำ           |
| `/history`                  | งานล่าสุดของ Session (`GET /inspections`, Should-have)                                            |

โค้ดหลักอยู่ที่ `src/lib/features/inspection/`

| ไฟล์                             | เนื้อหา                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `schema.ts`                      | Zod schemas ตาม API contract (Upload, Layout, InspectionCreate, Inspection, Slot, Error)                           |
| `port.ts` / `api.ts` / `mock.ts` | Interface `InspectionApi`, HTTP จริง (fetch + session cookie), API จำลองในเบราว์เซอร์                              |
| `queries.ts`                     | TanStack Query: Poll, Retry เฉพาะ Error ที่ `retryable`, สร้างงานด้วย `client_request_id` เดิมทุกครั้งที่ Retry    |
| `machine.ts` / `flow.svelte.ts`  | State machine ตาม Spec §10.6 (`idle` … `failed`)                                                                   |
| `geometry.ts`                    | ตรวจ 4 จุดแบบเดียวกับ Backend (`validate_reference_points`), Homography                                            |
| `errors.ts` / `messages.ts`      | แปลง `error.code` และค่า enum เป็นข้อความภาษาไทย                                                                   |
| `components/`                    | `camera`, `corner-picker`, `letter-block-guide`, `result-overlay`, `result-summary`, `slot-list`, `stage-progress` |

## เริ่มพัฒนา

ต้องมี Node ≥ 20 และ pnpm

```bash
cd frontend
pnpm install
cp .env.example .env        # ครั้งแรก
```

### ต่อกับ Backend จริง (พอร์ต 9010)

พอร์ต 9000 มีโปรเจกต์อื่นใช้อยู่ Backend ของ KeyCheck จึงใช้ `9010` ระหว่างพัฒนา

```bash
# Terminal 1 — Backend (ดู backend/README.md) ให้ฟังที่ http://localhost:9010
# Terminal 2 — Frontend
pnpm dev                    # http://localhost:5173
```

- ตั้ง `PUBLIC_API_URL=` (ว่าง) เพื่อเรียก `/api/v1/...` แบบ Same-origin; Vite proxy ส่ง `/api` ต่อไปที่ `http://localhost:9010`
  (เปลี่ยนปลายทางได้ด้วย env `KEYCHECK_API_TARGET`) Session cookie `kc_session` จึงเป็น First-party เหมือนตอน Deploy หลัง Reverse proxy
- ถ้าตั้ง `PUBLIC_API_URL` เป็น Origin อื่น Frontend จะส่ง `credentials: 'include'` และ Backend ต้องอนุญาต Origin นั้นใน `ALLOWED_ORIGINS`

### โหมดจำลอง (ไม่ต้องรัน Backend)

```bash
PUBLIC_USE_MOCK=1 pnpm dev
```

- API จำลองทำงานในเบราว์เซอร์ มีดีเลย์และไล่ขั้นตอน `queued → rectifying → detecting → reading → matching → completed` (~4 วินาที)
- ผลจำลองคำนวณกรอบจากจุดที่แตะ (Homography) มีช่องผิด (A/S สลับ + คำแนะนำสลับ) และช่องไม่แน่ใจ 2 ช่อง
- ทุกหน้ามีแถบ "โหมดจำลอง" และหน้าผลมีป้าย "ผลจำลอง" (Spec §17.3) ห้ามใช้ภาพหน้าจอโหมดนี้เป็นผลทดสอบจริง
- เลือกสถานการณ์ได้ใน DevTools console: `sessionStorage.setItem('keycheck.mockScenario', '<ค่า>')`
  ค่า: `default`, `all_correct`, `layout_mismatch`, `failed`, `flaky_poll` (เน็ตหลุดระหว่าง Poll)
- ข้อมูลอยู่ในหน่วยความจำ Reload แล้วงานเดิมจะหายไป (จะเห็นข้อความ "ไม่พบงานตรวจนี้")

### กล้องบนมือถือ

`getUserMedia` ใช้ได้เฉพาะ Secure context (HTTPS หรือ `localhost`) ถ้าเปิดผ่าน IP ใน LAN ด้วย HTTP ปุ่ม "เปิดกล้องถ่ายภาพ" จะถูกซ่อน
และใช้ "ถ่ายด้วยแอปกล้อง" (`<input capture="environment">`) หรือ "เลือกไฟล์ภาพ" แทน ทดสอบกล้องจริงบนมือถือให้ใช้ HTTPS reverse proxy ตาม Web plan W5

## Build

```bash
pnpm build                  # ได้ static site ที่ build/
pnpm preview                # เปิดดู build ที่ http://localhost:4173
```

เป็น SPA (`ssr = false`) หน้า `/inspections/[id]` ไม่ถูก Prerender จึงต้องให้ Web server ส่ง `build/200.html` สำหรับ Path ที่ไม่มีไฟล์
(เช่น Caddy: `try_files {path} {path}.html /200.html`)

## ตรวจคุณภาพโค้ด

```bash
pnpm check                  # svelte-check + TypeScript
pnpm lint                   # prettier --check + eslint
pnpm format                 # จัดรูปแบบโค้ด
npx @sveltejs/mcp svelte-autofixer ./src/path/component.svelte
```

## ทดสอบ e2e (Playwright, โหมดจำลอง)

```bash
pnpm exec playwright install chromium   # ครั้งแรก หรือเมื่อ @playwright/test อัปเดต
pnpm test:e2e                           # vite build --mode test (.env.test: PUBLIC_USE_MOCK=1) แล้วรัน Playwright
```

- โปรเจกต์ `unit`: ทดสอบโมดูล Pure (`validateQuad` ให้ผลเดียวกับ Backend, Homography, State machine) ไม่ต้องเปิดเบราว์เซอร์
- โปรเจกต์ `desktop` (Desktop Chrome) และ `mobile` (Pixel 7, Touch): Flow เต็ม เลือกไฟล์ → Preview → อัปโหลด → แตะ 4 จุด → ขั้นตอน → ผลบน Overlay,
  จุดไขว้ถูกบล็อก, ลากจุดบนมือถือแล้วหน้าไม่เลื่อน, ปฏิเสธกล้อง/ไม่มี MediaDevices แล้วใช้ไฟล์แทน, ถ่ายจากกล้องจำลองแล้วหยุด Track,
  ปฏิเสธ HEIC, `LAYOUT_MISMATCH`, เน็ตหลุดระหว่าง Poll, กดส่งซ้ำได้งานเดียว, เลือกช่องด้วย Keyboard
- ภาพทดสอบ `e2e/fixtures/keyboard.jpg` เป็นภาพสังเคราะห์ 1200×700 (A/S สลับ) ไม่ใช่ภาพถ่ายจริง
- รายงาน HTML อยู่ที่ `playwright-report/` (`pnpm exec playwright show-report`)

การทดสอบบนมือถือจริงผ่าน HTTPS (Spec §16.3, Web plan W5) ยังต้องทำด้วยมือ
