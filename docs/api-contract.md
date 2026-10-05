# KeyCheck — API / Result Contract (v1)

**อ้างอิง:** Spec §10–§14 · [`implementation-plan.md`](./implementation-plan.md) P3.A, P5, P6 · [`web-implementation-plan.md`](./web-implementation-plan.md)
**สถานะ:** ล็อกแล้วสำหรับ Backend / Frontend / `ai.inference` — แก้ที่นี่ก่อนแก้โค้ด

ข้อตกลงที่ใช้ (ตอบ W-Q1–W-Q5 ของ Web plan):

- `slot_id` เป็นตำแหน่ง `r<row>c<col>` (เช่น `r0c0` = ช่อง Q) ไม่ใช่ตัวอักษร; UI แสดงด้วย `expected_label`
- Session cookie ทำตั้งแต่แรก, Overlay วาดฝั่ง Frontend ด้วย SVG, OCR บน CPU
- พอร์ตตอนพัฒนา: Backend `9010` (พอร์ต 9000 มีโปรเจกต์อื่นใช้อยู่), Frontend `5173` (Vite proxy `/api` → `9010`)

---

## 1. `ai.inference.Inspector` (Python, ใช้โดย Worker)

```python
from ai.inference import Inspector, InvalidReferencePoints, load_bundle_meta

insp = Inspector(bundle_dir, layout_id="qwerty_stagger_letters_v1", ocr_device="cpu")   # โหลดโมเดลครั้งเดียว
insp.bundle_id        # str
insp.layout_id        # str
insp.layout_version   # int
result = insp.inspect(image_bgr, ref_points_px, on_stage=callback)                     # callback(stage: str)
```

- `image_bgr`: ภาพที่จัด EXIF orientation แล้ว (`np.ndarray` HxWx3 uint8)
- `ref_points_px`: `(4,2)` พิกัดพิกเซลบนภาพเดียวกัน ลำดับ TL→TR→BR→BL = กึ่งกลางช่อง Q, P, M, Z ตามตำแหน่ง
- จุดไม่ผ่าน `validate_reference_points` → raise `InvalidReferencePoints(message)` (Backend แปลงเป็น `INVALID_CORNERS`)
- `on_stage` ถูกเรียกด้วย `"rectifying"`, `"detecting"`, `"reading"`, `"matching"` ตามลำดับ
- คืน `dict` ที่มีคีย์ตาม §3 ต่อไปนี้: `status` (`completed` | `rejected`), `error_code` (`null` | `LAYOUT_MISMATCH`), `layout_id`, `layout_version`, `model_bundle_id`, `coordinate_system`, `summary`, `slots`, `suggestions`, `warnings`, `timings_ms`, `fit`
- ค่าทุกตัวเป็นชนิด JSON ได้ทันที (ไม่มี numpy scalar)

## 2. HTTP API (prefix `/api/v1`)

ทุก Response ที่ผิดพลาดใช้รูปแบบ §4 ทุก Endpoint ต้องมี Session cookie (ออกให้อัตโนมัติถ้ายังไม่มี) และตรวจ Ownership: ทรัพยากรของ Session อื่นตอบ **404 `NOT_FOUND`** (ไม่บอกว่ามีอยู่)

| Method | Path | Request | Success |
| --- | --- | --- | --- |
| GET | `/health` | — | 200 `{status, api, database, model, model_bundle_id}` |
| GET | `/layouts` | — | 200 `{layouts: [Layout]}` (กรอง `internal_only` ออก) |
| POST | `/uploads` | multipart field `image` | 201 `Upload` |
| GET | `/uploads/{image_id}/image` | — | 200 ภาพ (Content-Type ตามจริง, `Cache-Control: private`) |
| DELETE | `/uploads/{image_id}` | — | 204; 409 `IMAGE_IN_USE` ถ้ามีงานอ้างอิงอยู่ |
| POST | `/inspections` | JSON `InspectionCreate` | **202** `{inspection_id, status, status_url}` |
| GET | `/inspections/{inspection_id}` | — | 200 `Inspection` |
| DELETE | `/inspections/{inspection_id}` | — | 204; 409 `INSPECTION_IN_PROGRESS` ถ้า `queued`/`processing` |
| GET | `/inspections` | `?limit=20&cursor=` | 200 `{items: [InspectionListItem], next_cursor}` (Should-have) |

### 2.1 Schemas

```jsonc
// Layout
{ "layout_id": "qwerty_stagger_letters_v1", "version": 1, "name": "...", "supported_form_factors": ["ANSI","ISO"],
  "reference_points": [ {"order":"TL","slot_id":"r0c0","expected_label":"Q"}, {"order":"TR",...,"P"}, {"order":"BR",...,"M"}, {"order":"BL",...,"Z"} ],
  "slots": [ {"slot_id":"r0c0","row":0,"col":0,"expected_label":"Q"}, ... 26 ] }

// Upload
{ "image_id": "img_<random>", "width": 4032, "height": 3024, "mime_type": "image/jpeg", "byte_size": 123456,
  "image_url": "/api/v1/uploads/img_.../image", "created_at": "ISO-8601Z", "expires_at": "ISO-8601Z" }

// InspectionCreate
{ "image_id": "img_...", "layout_id": "qwerty_stagger_letters_v1",
  "reference_points_normalized": [[x,y],[x,y],[x,y],[x,y]],   // 0..1, TL,TR,BR,BL
  "client_request_id": "uuid (optional, idempotency key per session)" }

// Inspection
{ "inspection_id": "ins_<random>",
  "status": "queued" | "processing" | "completed" | "rejected" | "failed",
  "stage": null | "rectifying" | "detecting" | "reading" | "matching",
  "image_id": "img_...", "image_url": "/api/v1/uploads/.../image", "image_width": 4032, "image_height": 3024,
  "image_expired": false,
  "layout_id": "...", "layout_version": 1, "model_bundle_id": "baseline_dev_v0" | null,
  "coordinate_system": "original_oriented_normalized",
  "reference_points_normalized": [[x,y]x4],
  "created_at": "...", "finished_at": null | "...",
  "summary": null | { "total_slots": 26, "correct": 24, "incorrect": 2, "uncertain": 0 },
  "slots": [ Slot x26 ],                 // [] ถ้ายังไม่เสร็จหรือ rejected/failed
  "suggestions": [ { "type": "swap_pair" | "cycle", "slots": ["r1c0","r1c1"] } ],
  "warnings": [ "layout_fit_not_checked", "proxy_model", ... ],
  "timings_ms": null | { "rectify": 12, "detect": 3, "read": 2400, "match": 2, "total": 2430 },
  "error": null | Error.error }          // มีค่าเมื่อ rejected / failed

// Slot
{ "slot_id": "r1c0", "row": 1, "col": 0, "expected_label": "A", "observed_label": "S" | null, "candidate_label": "S" | null,
  "status": "correct" | "incorrect" | "uncertain",
  "reason": "label_match" | "label_mismatch" | "detection_unavailable" | "mapping_ambiguous" | "ocr_low_confidence" | "ocr_invalid_label" | "crop_quality_low",
  "reason_codes": ["label_mismatch"],
  "detector_score": 0.91 | null, "ocr_score": 0.88 | null, "assignment_distance": 0.07 | null,
  "polygon": [[x,y],[x,y],[x,y],[x,y]],  // normalized บนภาพที่จัด orientation แล้ว
  "polygon_source": "detection" | "layout",
  "is_reference": false }                // true สำหรับ 4 ช่องอ้างอิง Q/P/M/Z
```

- `summary.correct + incorrect + uncertain == total_slots == len(slots) == 26` เสมอเมื่อ `completed`
- ค่าที่ไม่มีเป็น `null` ไม่สร้างคะแนนขึ้นเอง (Baseline: `detector_score = null`)
- `candidate_label` มีค่าเฉพาะช่อง `uncertain` ที่ `reason = ocr_low_confidence`: ตัวอักษรที่อ่านได้แต่ `ocr_score` ต่ำกว่าเกณฑ์ เป็นคำใบ้ให้ผู้ใช้ตรวจด้วยตา **ไม่นับเป็นผลตรวจ** (สถานะและ `summary` ไม่เปลี่ยน)
- `warnings` ที่กำหนดไว้: `layout_fit_not_checked` (Baseline ตรวจ §7.8 ไม่ได้), `proxy_model` (Bundle ฝึกจาก Kaggle QWERTZ), `image_quality_low` (เบลอ/แสงจัด เกินเกณฑ์)

### 2.2 สถานะงาน

```
queued → processing (stage: rectifying → detecting → reading → matching) → completed
                                                                         → rejected (LAYOUT_MISMATCH / INVALID_CORNERS)
                                                                         → failed   (PROCESSING_FAILED / MODEL_UNAVAILABLE / IMAGE_EXPIRED)
```

## 3. Error contract (Spec §11.5)

```json
{ "error": { "code": "INVALID_CORNERS", "message": "ข้อความภาษาไทยสำหรับผู้ใช้", "retryable": true } }
```

| Code | HTTP | ใช้เมื่อ |
| --- | --- | --- |
| `UNSUPPORTED_IMAGE` | 415 | Magic bytes ไม่ใช่ JPEG/PNG (รวม HEIC) |
| `IMAGE_TOO_LARGE` | 413 | เกิน `MAX_UPLOAD_BYTES` หรือ `MAX_IMAGE_PIXELS` |
| `IMAGE_DECODE_FAILED` | 422 | Decode ไม่ได้ |
| `INVALID_CORNERS` | 422 | จุดไม่ครบ 4 / นอก 0–1 / ไขว้ / พื้นที่เล็กเกิน |
| `LAYOUT_NOT_FOUND` | 422 | `layout_id` ไม่มี หรือเป็น `internal_only` |
| `VALIDATION_ERROR` | 422 | Body ไม่ผ่าน Schema อื่น ๆ |
| `NOT_FOUND` | 404 | ไม่มี หรือเป็นของ Session อื่น |
| `IMAGE_EXPIRED` | 410 | ภาพถูกลบตาม Retention แล้ว |
| `IMAGE_IN_USE` / `INSPECTION_IN_PROGRESS` | 409 | ลบไม่ได้ตาม §11.2 |
| `QUEUE_FULL` | 429 | คิวเต็ม หรือ Session มีงานค้างเกิน `MAX_ACTIVE_JOBS_PER_SESSION` |
| `ORIGIN_FORBIDDEN` | 403 | `Origin` ของคำขอเปลี่ยนข้อมูลไม่ตรง Same-origin / `ALLOWED_ORIGINS` |
| `MODEL_UNAVAILABLE` | 503 / ใน `error` ของงาน | โหลด Bundle ไม่ได้ |
| `LAYOUT_MISMATCH` | ใน `error` ของงาน (`rejected`) | Layout fit check ไม่ผ่าน |
| `PROCESSING_FAILED` | ใน `error` ของงาน (`failed`) | Exception ใน Worker หรือ Lease หมดเกินจำนวน Retry |
| `INTERNAL_ERROR` | 500 | ไม่ส่ง Stack trace |

## 4. Configuration (env)

| ตัวแปร | ค่าเริ่มต้น | หมายเหตุ |
| --- | --- | --- |
| `MONGODB_URI` | ว่าง | ว่าง = เก็บในหน่วยความจำ + Worker thread ใน API (W2); มีค่า = Beanie + Worker แยกโปรเซส (W6) |
| `STORAGE_ROOT` | `../var/storage` | ไฟล์ภาพ ชื่อไฟล์จาก Internal ID เท่านั้น |
| `MODEL_BUNDLE_DIR` | `../bundles/baseline_dev_v0` | Bundle ที่อนุมัติ ไม่รับ Path จาก Client |
| `OCR_DEVICE` | `cpu` | |
| `MAX_UPLOAD_BYTES` | `15728640` | 15 MiB |
| `MAX_IMAGE_PIXELS` | `24000000` | 24 MP |
| `QUEUE_CAPACITY` | `8` | งาน `queued`+`processing` ทั้งระบบ |
| `MAX_ACTIVE_JOBS_PER_SESSION` | `2` | |
| `IMAGE_RETENTION_HOURS` | `24` | |
| `METADATA_RETENTION_HOURS` | `168` | 7 วัน |
| `SESSION_SECRET` | (ต้องตั้ง) | ใช้ HMAC ค่า Token ก่อนเก็บ |
| `COOKIE_SECURE` | `false` | `true` หลัง HTTPS proxy |
| `ALLOWED_ORIGINS` | `[]` | ว่าง = ยอมเฉพาะ Same-origin (`Origin` host == `Host`) |
| `WORKER_LEASE_SECONDS` | `120` | Heartbeat ทุก ~1/4 ของค่านี้ |
| `WORKER_MAX_RETRIES` | `1` | Lease หมดเกินนี้ → `failed` `PROCESSING_FAILED` |

Session cookie ชื่อ `kc_session`: HttpOnly, `SameSite=Lax`, `Path=/`, `Secure` ตาม `COOKIE_SECURE`; เก็บใน DB เฉพาะ `owner_session_hash = HMAC-SHA256(SESSION_SECRET, token)`
