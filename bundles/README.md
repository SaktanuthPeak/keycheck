# Model bundles

Bundle คือโฟลเดอร์เดียวที่ Worker โหลดผ่าน `ai.inference.Inspector` (Spec §12.4, [api-contract](../docs/api-contract.md) §1)
Backend เลือก Bundle ด้วย `MODEL_BUNDLE_DIR` (ค่าเริ่มต้น `../bundles/baseline_dev_v0`) และไม่รับ Path จาก Client

> **Weights ไม่ขึ้น Git** (`*.pt` อยู่ใน `.gitignore`) — Commit เฉพาะ `bundle.json` และ README นี้

## โครงสร้าง

```
bundles/<bundle_id>/
├── bundle.json            # ค่าทั้งหมดที่ Inspector ใช้
└── weights_<detector>.pt  # เฉพาะ yolo / frcnn (ไม่มีใน baseline)
```

`bundle.json` ใช้ Format เดียวกับที่ [`ai/bundle.py`](../ai/bundle.py) `build_bundle()` เขียนใน Notebook Q6:

| คีย์ | ความหมาย |
| --- | --- |
| `bundle_id` | ส่งกลับใน `model_bundle_id` ของผลตรวจ |
| `detector` | `baseline` (Fixed layout crops, ไม่ใช้ Torch) / `yolo` / `frcnn` |
| `weights_file` | ชื่อไฟล์ Weights **ภายในโฟลเดอร์ Bundle** (Path ที่ออกนอกโฟลเดอร์จะถูกปฏิเสธ); `null` สำหรับ baseline |
| `detector_config` | `yolo`: `{imgsz, max_det?}`; `frcnn`: `{min_size, max_size, box_detections_per_img, box_score_thresh, box_nms_thresh}` |
| `px_per_unit` | ความละเอียดภาพ Rectified (พิกเซลต่อ 1u) |
| `crop_mode` | `key_full` / `key_full_pad<f>` / `key_center_<f>` ([`crop_box_px`](../ai/recognition/ocr.py)) |
| `ocr` | ฟิลด์ของ `OcrSpec`: `id`, `mode` (`rec` / `auto`), `rec_model`, `det_model`, `pad_px` — `device` มาจาก `OCR_DEVICE` |
| `thresholds` | ฟิลด์ของ `Params` ([`decision.py`](../ai/matching/decision.py)); คีย์อื่นเช่น `objective` ถูกข้าม; Baseline บังคับ `skip_layout_fit=true` เสมอ |
| `evidence.det_floor` | (ไม่บังคับ, ค่าเริ่มต้น 0.05) Detection ที่ Score ต่ำกว่านี้ไม่ถูกนำมาใช้เลย |
| `layouts` | Layout ที่ Bundle รองรับ; `Inspector(layout_id=...)` นอกรายการนี้จะ Error |
| `proxy` | มีค่า → ผลทุกงานมี Warning `proxy_model` |
| `notes` | (ไม่บังคับ) เหตุผลของค่าที่เลือก |

ตอนให้บริการ Inspector อ่าน OCR **เฉพาะ Detection ที่ถูกจับคู่กับช่อง** (≤ 26 Crop) ผลเท่ากับ `collect_evidence` + `decide` ที่ Q6 ใช้ประเมิน
เพราะ `decide` ไม่ใช้ตัวอักษรของ Detection ที่ไม่ได้จับคู่ (มี Test `test_serving_evidence_equals_q6_path`)

## `baseline_dev_v0`

Bundle ที่เขียนด้วยมือ (Web plan W0 ข้อ 5) ใช้ Fixed layout crops จึงไม่ต้องมี Weights และไม่ใช้ Torch

- `px_per_unit: 64` และ OCR `auto_server` (PP-OCRv5 server det + rec) จาก Q3 (`outputs/pipeline/qwertz_v1/q3_ocr/summary.json`)
- `crop_mode: key_center_0.7` **ต่างจาก `chosen` ของ Q3** (`key_full`): ไม่มีแถวไหนใน Q3 ผ่าน `max_reject_rate 0.10` โค้ด `run_q3` จึงคงแถวแรกไว้
  แทนที่จะเลือกแถวที่ดีที่สุด ในตารางเดียวกันที่ ppu 64 `key_center_0.7` ได้ 0.815 เทียบกับ `key_full` 0.613 (`key_center_0.55` 0.819)
  เลือก 0.7 แทน 0.55 เพราะเก็บผิวปุ่มไว้มากกว่า (ปุ่มไทย-อังกฤษมักวางอักษรละตินไว้ใกล้มุม)
- `thresholds` = `q6.default_params` ใน [`pipeline.yaml`](../experiments/configs/qwertz/pipeline.yaml) + `skip_layout_fit: true`
  ยังคง `ref_invalid_max: 2` ไว้ จึงตอบ `LAYOUT_MISMATCH` เมื่ออ่านช่องอ้างอิง Q/P/M/Z ไม่ได้ตั้งแต่ 2 ช่อง (กันแตะจุดเลื่อนไปหนึ่งช่อง)
- Baseline ตรวจ Layout fit (Spec §7.8) ไม่ได้ → ผลมี Warning `layout_fit_not_checked`

ผลลองบนภาพ Validation ของ Kaggle 2 ภาพ (จุดอ้างอิง GT, Layout `qwertz_letters_eval_v1`, CPU ขณะมีงานฝึกโมเดลใช้ CPU อยู่):

| ภาพ | Bundle | correct / incorrect / uncertain | อ่าน OCR (warm) | รวม (warm) | RAM สูงสุด |
| --- | --- | --- | --- | --- | --- |
| asus28 | baseline_dev_v0 | 23 / 0 / 3 | 4.6–5.1 s | 4.6–5.1 s | 1.3 GB |
| corsair14 (ฟอนต์เกมมิ่ง ไฟ RGB) | baseline_dev_v0 | 14 / 0 / 12 | 5.4–5.6 s | 5.4–5.6 s | 1.3 GB |
| asus28 | smoke `keycheck_qwertz_dev_v1` (frcnn) | 14 / 0 / 12 | 5.2–5.4 s | 7.2–7.4 s (detect ~2 s) | 1.8 GB |

ครั้งแรกหลังเริ่ม Process ช้ากว่านี้ราว 4–5 วินาที เพราะ Paddle โหลดโมเดลตอนอ่าน Crop ชุดแรก ตัวเลขเหล่านี้เป็นของ Proxy ไม่ใช่ความแม่นยำของเว็บ

## ติดตั้ง Dev bundle จาก Notebook Q6 (W4)

หลัง Notebook รอบเต็มจบ Q6 จะมีโฟลเดอร์ `outputs/pipeline/qwertz_v1/q6_eval/bundle/keycheck_qwertz_dev_v1/`

```fish
cp -r outputs/pipeline/qwertz_v1/q6_eval/bundle/keycheck_qwertz_dev_v1 bundles/
```

1. ตรวจ `bundle.json` ก่อนใช้:
   - `thresholds.ref_invalid_max` — ถ้าเป็น `null` การแตะจุดอ้างอิงเลื่อนไปหนึ่งช่องจะ **ไม่ถูก Reject** เพราะ Detector พบปุ่มข้างเคียง (Ü, `[` ฯลฯ)
     ครบทุกช่องและ Layout fit ผ่าน (เห็นแล้วใน Smoke bundle: ผลออกมา 0 / 13 / 13 แทน `LAYOUT_MISMATCH`) ถ้า Q6 รอบเต็มยังได้ `null` ให้พิจารณาตั้งเป็น `2`
   - `crop_mode` — มาจาก Q3 `chosen` ซึ่งตอนนี้เป็น `key_full` ด้วยเหตุผลข้างบน
   - `layouts` ต้องมี `qwerty_stagger_letters_v1`
2. ติดตั้ง Dependency ของ Detector ใน Env ของ Backend: `keycheck-ai[detector]` (Torch ต้องเป็น Build เดียวกับที่ฝึก)
3. ลองด้วย Demo ก่อน:
   ```fish
   env CUDA_VISIBLE_DEVICES="" python -m ai.inference.demo photo.jpg --points "x1,y1 x2,y2 x3,y3 x4,y4" \
       --bundle bundles/keycheck_qwertz_dev_v1 --out /tmp/overlay.png --repeat 2
   ```
4. ตั้ง `MODEL_BUNDLE_DIR=../bundles/keycheck_qwertz_dev_v1` แล้ว Restart Backend (ไม่ต้องแก้ Frontend)

**ความปลอดภัย:** Faster R-CNN โหลด Checkpoint ด้วย `torch.load(weights_only=False)` ซึ่งรันโค้ดในไฟล์ได้ ใช้เฉพาะ Bundle ที่สร้างเองจาก Notebook เท่านั้น

## Demo

```fish
python -m ai.inference.demo <image> --points "x1,y1 x2,y2 x3,y3 x4,y4" [--normalized] [--bundle DIR] [--layout ID] [--out PNG] [--json FILE] [--repeat N]
```

จุดทั้งสี่คือกึ่งกลางช่อง Q, P, M, Z ตามตำแหน่ง (TL, TR, BR, BL) บนภาพที่จัด EXIF แล้ว ภาพผลวาด Polygon สีเขียว = ถูก, แดง = ผิด (`A>S` คือช่อง A พบ S),
เหลือง = ไม่แน่ใจ (`A?`) และพิมพ์ Summary, Warnings, Timings เป็น JSON
