# KeyCheck — QWERTZ Single-Notebook Pipeline: Implementation Plan

**อ้างอิง:** [`implementation-plan.md`](./implementation-plan.md) · [`keycheck-technical-specification.md`](./keycheck-technical-specification.md) v1.1
**เวอร์ชัน:** 0.3 — 1 ตุลาคม 2026 (v0.2 รวมเป็น Notebook เดียว → v0.3 รันบนเครื่อง Local + RTX 4060 เป็นหลัก, ตัด Unit tests ออก)
**สถานะ:** เขียนโค้ดครบทุก Stage แล้ว (ขั้น 2–10 + Notebook `notebooks/keycheck_qwertz_pipeline.ipynb`, `00_env_check.ipynb`) — ตรวจแล้วเฉพาะ Q1–Q2 และตรรกะ Matching/Metrics ด้วยข้อมูลจำลอง; ยังไม่ได้รัน OCR เต็ม, Q4/Q5 (ฝึก), Q6, Q7 — รอรันใน Notebook

---

## 0. เป้าหมายและขอบเขต

สร้าง **Notebook เดียว** `notebooks/keycheck_qwertz_pipeline.ipynb` ที่รันได้ตั้งแต่ข้อมูลดิบจนถึงรายงาน Test โดยรัน **บนเครื่อง Local (Linux + RTX 4060 Laptop GPU 8 GB) เป็นหลัก** และใช้ Google Colab เป็นตัวสำรอง:

```
ข้อมูล Kaggle → Audit/Split → Rectify → OCR → Train Detector → Pipeline eval → Proxy Test
```

- ใช้ **Kaggle dataset แบบเยอรมัน QWERTZ** เป็นข้อมูล Proxy ระหว่างที่ยังไม่มีภาพ QWERTY ของเรา
- **ไม่เปลี่ยนขอบเขตสินค้า:** แอปยังตรวจ QWERTY (§3.1) และ QWERTZ ยังอยู่นอกขอบเขตของผู้ใช้ (§3.3)
- Logic ทั้งหมดอยู่ใน `ai/` ส่วน Notebook มีแค่ Config, การเรียก Stage และการแสดงผล เพื่อให้โค้ดชุดเดียวกันใช้กับภาพ QWERTY ของเราและ Worker ได้
- ผลรายงานเป็น "ผลบนข้อมูล Proxy" แยกจากผล Test หลัก (§5.1)
- **ไม่มี Unit tests ในแผนนี้** เพื่อให้ได้ผลเร็ว ความถูกต้องตรวจจากผลที่ Notebook แสดง (ตาราง, ตัวเลขเทียบกับ §1, ภาพตรวจด้วยตา) และ Smoke run — ข้อควรรู้: Spec §16 และ Definition of Done §20 ยังกำหนดให้มี Tests ของพิกัด, Assignment, Upload และการงดตอบ จึงต้องเพิ่มภายหลังก่อนส่งงาน

---

## 1. ข้อมูลตั้งต้น (ผลตรวจจาก `datasets/dataset_final/`)

| รายการ | จำนวน |
| --- | --- |
| ภาพทั้งหมด / ภาพต้นฉบับ (`source_id`) | 5,254 / 1,884 |
| ต้นฉบับที่มีกรอบ A–Z ครบ 26 ตัว | **1,608** |
| ต้นฉบับที่มีตัวอักษรบางส่วน (21–25 ตัว) | 48 |
| ต้นฉบับที่ไม่มีตัวอักษร (รวม `empty`) | 174 |
| ต้นฉบับที่มีกรอบตัวอักษรซ้ำ (Label ผิด / หลายคีย์บอร์ด) | 22 |
| ยี่ห้อในชุดที่ครบ 26 ตัว | 81 (+ กลุ่มไม่ระบุยี่ห้อ `sonstige`/`sonstiges` 61 ภาพ) |
| Flip ซ้าย-ขวา / บน-ล่าง | 14 / 24 จาก 4,518 ภาพ |
| Generic letter-block: Error สูงสุดต่อคีย์บอร์ด < 0.25u | 96.2% ของ 1,613 คีย์บอร์ด |

---

## 2. Layout สำหรับ Proxy

ตำแหน่งช่อง A–Z ของ QWERTZ และ QWERTY เหมือนกันทุกช่อง ต่างกันแค่ Expected label สองช่อง

| ช่อง (ตำแหน่ง) | พิกัด (u) | `qwerty_stagger_letters_v1` | `qwertz_letters_eval_v1` |
| --- | --- | --- | --- |
| แถวบน ช่องที่ 6 | (5, 0) | Y | **Z** |
| แถวล่าง ช่องที่ 1 | (0.75, 2) | Z | **Y** |
| ช่องอื่น 24 ช่อง | ตาม §7.2 | เหมือนกัน | เหมือนกัน |

- `qwertz_letters_eval_v1` ใช้ภายในเพื่อประเมินเท่านั้น ไม่ส่งผ่าน `GET /api/v1/layouts`
- จุดอ้างอิง TL/TR/BR/BL = (0,0) · (9,0) · (6.75,2) · (0.75,2) — บน QWERTZ คือปุ่ม Q, P, M, **Y**
- **Q-D1:** ใช้ `slot_id` ตามตำแหน่ง (เช่น `r0c5`) แทนตัวอักษร เพราะช่องเดียวกันมี Expected label ต่างกันตาม Layout — ถ้าตกลงต้องแก้ Spec §11.4 / §12.1

---

## 3. Split แบบ Leave-brand-out

Kaggle ไม่มี `keyboard_id` จึงใช้ยี่ห้อ (จากชื่อไฟล์) เป็นตัวแทนของ "คีย์บอร์ดที่ไม่เคยเห็น"

| ชุด | วิธีเลือก | ขนาดโดยประมาณ (ต้นฉบับ) |
| --- | --- | --- |
| **Test — Unseen brands** | สุ่มยี่ห้อด้วย Seed ที่บันทึก จนได้ ~15%; คู่ `x` / `x_pc` (เช่น `lenovo` / `lenovo_pc`) อยู่ชุดเดียวกัน | ~240 |
| **Validation** | Group split ตาม `source_id` จากยี่ห้อที่เหลือ ~15% + ยี่ห้อ Held-out 1–2 ยี่ห้อ | ~240 |
| **Train** | ที่เหลือ รวมทั้ง 3 Copy ของ Roboflow; `sonstige(s)`, `empty` และต้นฉบับที่กรอบตัวอักษรซ้ำ อยู่ Train เท่านั้น | ~1,130 (~3,400 ภาพ) |

Validation และ Test ใช้ 1 Copy ต่อต้นฉบับ Manifest และ `split_manifest_hash` เก็บใน `data/manifests/kaggle_qwertz_v1/` และ Commit ก่อนเริ่มฝึก

---

## 4. โครงสร้าง Notebook

```
keycheck_qwertz_pipeline.ipynb
│
├── §0 Config            ← ค่าทั้งหมดที่ปรับได้อยู่ที่นี่ที่เดียว
├── §1 Setup             ← ตรวจ GPU/Env, ตั้ง Path ตาม ENV (Local: อ่าน datasets/ ตรง; Colab: Mount Drive + Copy dataset)
├── §2 Stage Q1  Ingest + Audit + Split          (CPU)
├── §3 Stage Q2  Rectified dataset + S1–S4        (CPU)
├── §4 Stage Q3  OCR eval + เลือก px_per_unit    (CPU/GPU)
├── §5 Stage Q4  Train YOLO11n                    (GPU, Resume ได้)
├── §6 Stage Q5  Train Faster R-CNN               (GPU, Resume ได้)
├── §7 Stage Q6  Pipeline eval บน Validation + Dev bundle
├── §8 Stage Q7  Proxy Test  🔒 ต้องเปิด Flag เอง
└── §9 Summary           ← ตารางสรุปทุก Stage + Path ของไฟล์ผล
```

แต่ละ Section มี 3–5 Cell: (1) เรียก `run_stage(...)` (2) แสดงตาราง/กราฟสรุป (3) ภาพตัวอย่างสำหรับตรวจด้วยตา

### 4.1 Cell Config (§0)

```python
ENV           = "local"                # "local" (RTX 4060) หรือ "colab" (สำรอง)
DATA_ROOT     = "datasets/dataset_final"            # Colab: /content/data/dataset_final
OUTPUT_ROOT   = "outputs/pipeline"                  # Colab: /content/drive/MyDrive/keycheck/pipeline
PIPELINE_ID   = "qwertz_v1"            # โฟลเดอร์ผลภายใต้ OUTPUT_ROOT
MODE          = "full"                 # "smoke" = Subset 50 ต้นฉบับ + 1 Epoch ใช้ทดสอบทั้งเส้นภายในไม่กี่นาที
REPO_REF      = "<commit หรือ tag>"
SEED          = 0
RUN = {"q1": True, "q2": True, "q3": True, "q4": True, "q5": True, "q6": True}
FORCE = set()                          # ชื่อ Stage ที่ต้องการรันใหม่แม้มีผลแล้ว
RUN_FINAL_TEST = False                 # 🔒 Q7 รันเฉพาะเมื่อตั้งเป็น True เอง
CONFIG_FILE   = "experiments/configs/qwertz/pipeline.yaml"   # Hyperparameters ทั้งหมด
```

ค่า Hyperparameter จริงอยู่ใน YAML ไม่เขียนลง Notebook เพื่อให้ Diff และทำซ้ำได้

### 4.2 กลไก Stage (หัวใจของ Notebook เดียว)

`ai/pipeline/stage.py` มี `run_stage(name, fn, config_subset, upstream)` ทำงานดังนี้:

1. คำนวณ **Fingerprint** = Hash ของ (Config ส่วนที่ Stage ใช้ + Fingerprint ของ Stage ก่อนหน้า + เวอร์ชันโค้ดของ Stage)
2. ถ้าโฟลเดอร์ผลมี `_DONE.json` ที่ Fingerprint ตรงกัน และ Stage ไม่อยู่ใน `FORCE` → **ข้าม** แล้วโหลด `summary.json` มาแสดง
3. ถ้าไม่ตรง → รัน `fn` แล้วเขียนผล + `summary.json` + `report.md` + `_DONE.json`
4. Stage ต้นทางเปลี่ยน → Fingerprint ปลายทางเปลี่ยนตาม → Stage ปลายทางรันใหม่อัตโนมัติ
5. Stage ฝึกโมเดล (Q4, Q5): Checkpoint ทุก Epoch และเขียน `_DONE.json` เมื่อฝึกจบเท่านั้น → Kernel ตาย / เครื่องดับ / Colab หลุด แล้วกด Run all ใหม่จะ **Resume จาก `last`** ไม่เริ่มใหม่

ผลลัพธ์ (Local: `outputs/pipeline/` ซึ่งต้องเพิ่มใน `.gitignore`; Colab: Drive):

```
<OUTPUT_ROOT>/<PIPELINE_ID>/
├── run_info.json                 # commit, package versions, nvidia-smi, seed, MODE, ENV
├── q1_ingest/   {coco.json, manifest.json, audit_report.md, _DONE.json}
├── q2_rectified/{rectified_ppu<N>.zip, eval_scenarios/, _DONE.json}
├── q3_ocr/      {ocr_report.md, chosen_config.yaml, _DONE.json}
├── q4_yolo/     {checkpoints/, metrics.json, _DONE.json}
├── q5_frcnn/    {checkpoints/, metrics.json, _DONE.json}
├── q6_eval/     {val_report.md, thresholds.yaml, bundle/keycheck_qwertz_dev_v1/, _DONE.json}
└── q7_test/     {test_report.md, _DONE.json}   # เขียนครั้งเดียว
```

### 4.3 การล็อก Test (Q7)

Q7 รันเมื่อผ่านทุกข้อเท่านั้น:

- `RUN_FINAL_TEST = True`
- `MODE == "full"`
- Repo ไม่มีไฟล์ค้างแก้ และ `REPO_REF` ตรงกับ Commit ที่ Checkout
- Hash ของ `thresholds.yaml` + Bundle จาก Q6 และ `split_manifest_hash` ตรงกับไฟล์ที่ Commit ไว้
- ยังไม่มี `q7_test/_DONE.json` — **ไม่รับ `FORCE`** สำหรับ Q7

### 4.4 หน่วยความจำและ Dependency

- แต่ละ Stage โหลดโมเดลเองและคืนหน่วยความจำเมื่อจบ (`del`, `gc.collect()`, `torch.cuda.empty_cache()`)
- ถ้าขั้น 1 (Env check) พบว่า PaddleOCR กับ Torch ชนกันใน Env เดียว ให้ Q3 และส่วน OCR ของ Q6/Q7 รันผ่าน **Subprocess** ที่ใช้ Env แยก (`ai/recognition/ocr_worker.py`) Notebook ยังเป็นไฟล์เดียวเหมือนเดิม
- **VRAM 8 GB (RTX 4060 Laptop):** YOLO11n 640 ใช้ Batch ปกติได้; 960 และ Faster R-CNN ใช้ Batch เล็ก + AMP (+ Gradient accumulation) และบันทึก Effective batch; ไม่รัน OCR บน GPU พร้อมกับการฝึก
- **Laptop ฝึกนาน:** เสียบสายชาร์จ ตั้ง Power mode เป็น Performance และวางในที่ระบายอากาศดี เพื่อลดการลดความเร็วเพราะความร้อน; บันทึกเวลาฝึกพร้อมหมายเหตุนี้

### 4.5 Environment (Local)

| รายการ | ข้อกำหนด |
| --- | --- |
| เครื่อง | พัฒนาโค้ดบนเครื่องหนึ่ง แล้ว Push ขึ้น Git และไปรันบนเครื่อง GPU; `datasets/` และ `outputs/` ไม่ขึ้น Git ต้อง Copy Dataset ไปเครื่อง GPU เอง |
| Driver | NVIDIA proprietary driver; `nvidia-smi` ต้องเห็น RTX 4060 |
| Python env | Conda env จาก `environment.yml` (หรือ venv ที่มีอยู่ `.venv-ml`) — แนะนำ Python 3.11/3.12 เพราะบาง Library เช่น PaddlePaddle อาจยังไม่มี Wheel สำหรับ 3.13 ต้องตรวจในขั้น 1 |
| PyTorch | Wheel ที่มี CUDA runtime ในตัว ไม่ต้องติดตั้ง CUDA Toolkit แยก |
| PaddleOCR | `paddlepaddle-gpu` Build ที่ตรงกับ CUDA หรือ `paddlepaddle` (CPU) ถ้า GPU ชนกับ Torch; ถ้าชนกันให้ใช้ Env แยก + Subprocess |
| Jupyter | รัน Notebook ด้วย Kernel ของ Env นี้ (VS Code หรือ JupyterLab) |
| Colab (สำรอง) | `requirements-colab.txt` ที่ Pin เวอร์ชันเดียวกัน; Mount Drive และเขียนผลลง Drive |

---

## 5. รายละเอียดแต่ละ Stage

### Q1 — Ingest + Audit + Split

- VOC → COCO กลาง พร้อม `source_id` (ตัด `.rf.<hash>`), `brand`, `copy_index`, `original_split`
- Audit: ภาพไม่มีกรอบ, Flip, มุมแถว > 15°, กรอบหลุดภาพ, กรอบตัวอักษรซ้ำ, จำนวนตัวอักษรที่เห็น, Error ของ Generic letter-block ต่อคีย์บอร์ด
- Class map: 59 คลาสปุ่ม → `keycap`; `keyboard` แยกเก็บ; ตัวอักษร `a`–`z` → `A`–`Z`
- Ground Truth รายช่อง: จับกรอบตัวอักษรเข้าช่องด้วยตำแหน่งหลัง Rectify ด้วยจุด GT (ไม่ใช้ Label จับคู่)
- Split ตาม §3
- **แสดงใน Notebook:** ตาราง Audit, จำนวนต่อ Split/ยี่ห้อ, Histogram ของ Error letter-block, ภาพที่ถูกคัดออกตัวอย่าง
- **Exit:** ไม่มี `source_id` หรือยี่ห้อ Test อยู่ใน Train; Manifest ถูก Commit

### Q2 — Rectified dataset + ชุดประเมิน S1–S4

- Rectify ด้วยจุด GT (Q, P, M, Y) ไปยัง Canvas ในหน่วย u + Margin (เช่น u ∈ [−1.5, 10.5] × [−1.5, 3.5])
- แปลงกรอบทุกปุ่ม (มุมทั้งสี่ผ่าน H → Axis-aligned); ตัดกรอบที่กึ่งกลางอยู่นอก Canvas หรือเหลือ < 50%
- Jitter จุดอ้างอิง σ ∈ {0.05, 0.10, 0.20}u — Train หลาย Variant ต่อต้นฉบับ; Val/Test ชุด Jitter คงที่ + จุด GT ตรง
- `px_per_unit` สร้างไว้สามค่า (64 / 96 / 128) ให้ Q3 เลือก แล้ว Q4 เป็นต้นไปใช้ค่าที่เลือก
- ชุดประเมิน (Val และ Test แยกกัน):

| รหัส | วิธีสร้าง | Layout ที่ใช้ตรวจ | ผลที่ต้องได้ | วัดอะไร |
| --- | --- | --- | --- | --- |
| **S1 เรียงถูก** | ภาพจริง | `qwertz_letters_eval_v1` | correct = 26 | False-alarm image rate, Coverage, Uncertain rate |
| **S2 สลับจริง Y↔Z** | ภาพจริงเดิม | `qwerty_stagger_letters_v1` | 24 correct / 2 incorrect + แนะนำสลับ Y↔Z | Recall ข้ามแถว, Suggestion, FP ช่องอื่น |
| **S3 สลับสังเคราะห์** | สลับภาพปุ่มในภาพ Rectified: 1 คู่ข้างกัน, 1 คู่ข้ามแถว, 2–3 คู่, วงจร 3 ปุ่ม (Seed คงที่) | `qwertz_letters_eval_v1` | ตามรูปแบบที่สร้าง | P/R/F1 ของ `incorrect`, `observed_label` accuracy, Suggestion/Cycle |
| **S4 Robustness** | (a) จุดอ้างอิงเลื่อนหนึ่งช่อง (b) ต้นฉบับที่เห็น 21–25 ตัว (c) ภาพหมุนแรงที่คัดออก | Layout ของ S1 | (a) `LAYOUT_MISMATCH` (b) ช่องที่หาย `uncertain` (c) Reject/Uncertain | การงดตอบและการปฏิเสธ |

- S3 ติดป้าย `synthetic=true` และใช้ประเมินเท่านั้น ห้ามใช้ฝึก
- **แสดงใน Notebook:** Grid ภาพ Rectified พร้อมกรอบ, ตัวอย่าง S3 ก่อน/หลังสลับ
- **Exit:** ตรวจด้วยตาแล้วกรอบตรงปุ่มหลัง Rectify; จำนวนภาพแต่ละชุดตรงตาม Manifest

### Q3 — OCR eval

- Crop ตัวอักษรจากกรอบ GT บนภาพ Rectified (Val, 1 Copy ต่อต้นฉบับ)
- PP-OCRv5 + Uppercase/trim + ตัวกรอง "ละติน A–Z ตัวเดียว"; ห้ามใช้ Expected label ช่วย; ไม่แปลง 0→O / 1→I
- เทียบ Crop ทั้งปุ่ม vs บริเวณตัวอักษร × `px_per_unit` 64/96/128
- รายงานแยกปุ่ม Q (`@`), E (`€`), M (`µ` อาจถูกอ่านเป็น `U`)
- **Exit:** เลือก OCR config + `px_per_unit` แล้วเขียน `chosen_config.yaml`

### Q4 — Train YOLO11n

- คลาส `keycap` บนภาพ Rectified (หลัก) และ Original (เทียบ) ด้วย `px_per_unit` จาก Q3
- `fliplr=0`, `flipud=0`, `mosaic=0`, `mixup=0`, `degrees` เล็กน้อย (§5.6) — Ultralytics เปิด Flip/Mosaic เป็นค่าเริ่มต้น ต้องปิดใน YAML
- `imgsz` 640 / 960, `max_det` ≥ จำนวนปุ่มที่เห็น, Early stopping บน Validation, Resume จาก `last.pt`
- **Output:** `best.pt` (= โมเดล E-K ใช้ช่วย Annotate ภาพของเราและ Pretrain E2)

### Q5 — Train Faster R-CNN

- ResNet50-FPN V2, 2 คลาส (Background + keycap), ข้อมูล/Split เดียวกับ Q4
- Training loop: Loss components แยก, AMP, Checkpoint model + optimizer + scheduler + epoch
- บันทึก `min_size`/`max_size`, `box_detections_per_img`
- ตั้ง `RUN["q5"] = False` ได้ถ้า GPU จำกัด แล้วกลับมารันทีหลัง (Q6 จะประเมินเฉพาะ Detector ที่มีผล)

### Q6 — Pipeline eval บน Validation + Dev bundle

- รันทั้ง Pipeline บน Validation S1–S4 สำหรับ Baseline (Fixed layout crops), YOLO11n, Faster R-CNN
- ปรับ Detection/OCR threshold, Gating, Unmatched cost, Layout fit threshold **บน Validation เท่านั้น** แล้วเขียน `thresholds.yaml`
- Metrics §9.1 + แยกจุด GT vs Jitter, ยี่ห้อ Held-out vs ยี่ห้อที่เคยเห็น
- สร้าง Dev model bundle `keycheck_qwertz_dev_v1`
- **Exit:** มีตารางเทียบ Baseline vs Detector และเลือก Configuration แล้ว → Commit `thresholds.yaml` + Hash ของ Bundle

### Q7 — Proxy Test 🔒

- ผ่านเงื่อนไข §4.3 แล้วรัน Baseline + ทุก Detector บน Test S1–S4 ครั้งเดียว
- รายงานทุก Metric พร้อม Counts, ตัวอย่าง FP/FN, Letter confusion matrix, แยกยี่ห้อ
- หัวรายงาน: "Proxy: Kaggle QWERTZ, ภาพสินค้า/เว็บ, ไม่ใช่ผล Test หลัก"

---

## 6. ลำดับการลงมือทำ (Implementation steps)

ทำตามลำดับนี้ แต่ละขั้นมีเงื่อนไขก่อนไปขั้นถัดไป

| ขั้น | งาน | ไฟล์หลัก | เงื่อนไขผ่าน |
| --- | --- | --- | --- |
| **1** | Env check บนเครื่อง Local: `nvidia-smi`, `torch.cuda.is_available()`, Import Paddle + Torch + Ultralytics ใน Env เดียว, ฝึก YOLO11n สั้นๆ แล้วหยุดกลางทางและ Resume | `notebooks/00_env_check.ipynb`, `environment.yml` | เห็น RTX 4060; รู้ว่า OCR ต้องแยก Subprocess ไหม; Resume ได้จริง |
| **2** | โครง Notebook + กลไก Stage + Config + Setup ด้วย Stage ปลอม | `ai/pipeline/stage.py`, `ai/colab/bootstrap.py`, Notebook §0–§1 | ใน Notebook เห็นว่าข้าม Stage ได้, `FORCE` ได้, Fingerprint ส่งต่อปลายทาง, Q7 Guard ปฏิเสธเมื่อไม่ครบเงื่อนไข |
| **3** | Layout ทั้งสอง + Geometry (Homography, แปลงพิกัด) | `layouts/*.json`, `ai/preprocessing/geometry.py` | ภาพตัวอย่างใน Notebook: จุดกึ่งกลาง 26 ช่องตกบนปุ่มจริงหลัง Rectify |
| **4** | Q1 Ingest/Audit/Split | `ai/data/kaggle_voc.py`, `ai/data/split.py`, `ai/data/audit.py` | ตัวเลข Audit ตรงกับ §1; ตารางใน Notebook ยืนยันว่า Split ไม่รั่ว |
| **5** | Q2 Rectified dataset + S1–S4 + Cell ตรวจด้วยตา | `ai/data/rectify_dataset.py`, `ai/data/synthetic_swap.py` | กรอบตรงปุ่มในภาพตัวอย่าง; S3 มีคำตอบถูก |
| **6** | Q3 OCR | `ai/recognition/ocr.py` (+ `ocr_worker.py` ถ้าต้องแยก) | เลือก Config + `px_per_unit` ได้ |
| **7** | Matching + Decision + Suggestion + Layout fit + Evaluation → รัน **Baseline บน Val ก่อนฝึกโมเดลใดๆ** | `ai/matching/`, `ai/detection/fixed_layout.py`, `ai/evaluation/` | Pipeline ครบเส้นด้วย Baseline; ตัวเลข S1–S4 ออกมาสมเหตุสมผล |
| **8** | Q4 YOLO11n | `ai/training/train_yolo.py`, `experiments/configs/qwertz/yolo.yaml` | ฝึกจบ, Resume ทดสอบแล้ว, ได้ `best.pt` |
| **9** | Q5 Faster R-CNN | `ai/training/train_frcnn.py`, `experiments/configs/qwertz/frcnn.yaml` | ฝึกจบ, Loss components บันทึกครบ |
| **10** | Q6 Eval + Dev bundle | `ai/evaluation/report.py`, `ai/bundle.py` | ตารางเทียบครบ; Commit Thresholds + Bundle hash |
| **11** | **Smoke run** ทั้ง Notebook (`MODE="smoke"`) แล้ว **Full run** ด้วย Run all | — | Run all ผ่านโดยไม่แก้มือ; Restart Kernel กลาง Q4 แล้ว Run all ใหม่ต่อได้ |
| **12** | Q7 Proxy Test ครั้งเดียว | — | รายงาน Test พร้อมข้อจำกัด §7 |

**ทำไม Baseline (ขั้น 7) มาก่อนฝึก:** พิสูจน์ว่า OCR + Matching + Decision + Evaluation ถูกต้องก่อน ถ้าตัวเลขผิดจะรู้ว่าไม่ใช่ปัญหาของ Detector และเป็นไปตามหลัก "Baseline ก่อน Detector" ของ Implementation plan

**Smoke mode แทน Unit tests:** รันซ้ำทุกครั้งที่แก้โค้ดใน `ai/` — Subset 50 ต้นฉบับ, 1 Epoch, เขียนผลไปที่ `PIPELINE_ID + "_smoke"` จึงไม่ปนกับผลจริง ถ้า Smoke run ผ่านและตัวเลข/ภาพตรวจในแต่ละ Stage ดูถูกต้อง ถือว่าผ่าน

---

## 7. สิ่งที่ Pipeline นี้ตอบได้และตอบไม่ได้

| ตอบได้ | ตอบไม่ได้ |
| --- | --- |
| Pipeline ทำงานครบเส้นและ Metrics คำนวณถูก | ความแม่นยำบนภาพถ่ายมือถือจริงของผู้ใช้ |
| Detector ช่วยเหนือ Baseline ไหมบน 81 ยี่ห้อ | ผลบนปุ่มไทย-อังกฤษ (Kaggle ไม่มี) |
| OCR อ่านได้ข้ามฟอนต์แค่ไหน | การสลับข้ามแถวจริงบนปุ่ม Sculpted (S3 จำลองไม่ได้) |
| ระบบทนต่อการแตะจุดอ้างอิงคลาดเคลื่อนแค่ไหน | ผลต่อผู้ใช้ QWERTY จริง — ต้องรอ Test ภาพของเรา |
| ค่าเริ่มต้นของ Threshold ก่อนมีภาพของเรา | ค่า Threshold สุดท้าย |

---

## 8. การตัดสินใจ

| # | เรื่อง | ข้อเสนอ |
| --- | --- | --- |
| Q-D1 | `slot_id` ตามตำแหน่ง (`r0c5`) | ใช้ตามตำแหน่ง แล้วแก้ Spec §11.4 / §12.1 |
| Q-D2 | `px_per_unit` | เลือกใน Q3 จาก 64 / 96 / 128 |
| Q-D3 | ยี่ห้อ Unseen test | สุ่มด้วย Seed, `x` / `x_pc` อยู่ด้วยกัน, ล็อกใน Q1 |
| Q-D4 | กลุ่ม `sonstige(s)` / `empty` | Train เท่านั้น |
| Q-D5 | ผล Proxy ในรายงาน | ใส่เป็นหัวข้อแยกพร้อมข้อจำกัด §7 |
| Q-D6 | Notebook เดียว vs แยก | Notebook เดียว + กลไก Stage; ถ้า Paddle/Torch ชนกัน ใช้ Subprocess แทนการแยก Notebook |
| Q-D7 | รันที่ไหน | Local RTX 4060 เป็นหลัก, Colab สำรอง (เช่นถ้า VRAM ไม่พอสำหรับ Faster R-CNN 960) |
| Q-D8 | Unit tests | ไม่ทำในแผนนี้ ใช้ Smoke run + ผลตรวจใน Notebook; เพิ่ม Tests ตาม Spec §16 ภายหลังก่อนส่งงาน |

---

## 9. ความเสี่ยง

| ความเสี่ยง | การรับมือ |
| --- | --- |
| Kernel ตาย / เครื่องดับ / Colab หลุด ระหว่างฝึก | Checkpoint ทุก Epoch + Resume อัตโนมัติจากกลไก Stage |
| Laptop ร้อนจนลดความเร็ว | Performance mode + เสียบสายชาร์จ + ระบายอากาศ; ไม่เทียบเวลาฝึกข้ามเงื่อนไขต่างกัน |
| VRAM 8 GB ไม่พอ | Batch เล็ก + AMP + Gradient accumulation; ถ้ายังไม่พอใช้ Colab |
| ไม่มี Unit tests ทำให้ Bug หลุด | Smoke run ทุกครั้งที่แก้โค้ด + ตัวเลข Audit ต้องตรงกับ §1 + ภาพตรวจด้วยตาในแต่ละ Stage |
| Run all ทับผลเก่าโดยไม่ตั้งใจ | Fingerprint + `_DONE.json`; รันใหม่เฉพาะเมื่อ Config เปลี่ยนหรือสั่ง `FORCE` |
| รัน Test ซ้ำเพื่อจูน | Guard §4.3, ไม่รับ `FORCE` |
| RAM/VRAM เต็มเพราะโหลดหลายโมเดล | คืนหน่วยความจำทุก Stage; OCR แยก Subprocess ถ้าจำเป็น |
| Notebook ยาวจนแก้ยาก | Logic อยู่ใน `ai/`; Notebook มีแค่ Config/เรียก Stage/แสดงผล |
| ภาพสินค้าไม่เหมือนภาพถ่ายมือถือ | ถือเป็น Proxy; Fine-tune ด้วยภาพของเรา (E2) ก่อนสรุป |
| Label Kaggle ผิดบางภาพ | Audit ใน Q1; ต้นฉบับที่ Error letter-block > 0.25u ตรวจด้วยตาก่อนใช้ใน Val/Test |
| Threshold จูนจน Proxy ดีแต่ภาพจริงแย่ | ใช้เป็นค่าเริ่มต้นเท่านั้น ปรับใหม่บน Validation ภาพของเรา |

---

## 10. การเปลี่ยนไปใช้ภาพ QWERTY ของเรา

สร้าง Notebook ที่สองจากไฟล์นี้ (`keycheck_qwerty_pipeline.ipynb`) โดยใช้กลไก Stage เดิม:

| ส่วน | Proxy (QWERTZ) | ภาพของเรา (QWERTY) |
| --- | --- | --- |
| Q1 Dataset adapter | `ai/data/kaggle_voc.py` | COCO จาก CVAT/Label Studio + Slot GT + `keyboards.csv` |
| Layout | `qwertz_letters_eval_v1` (S1/S3), `qwerty_stagger_letters_v1` (S2) | `qwerty_stagger_letters_v1` |
| Split | Leave-brand-out | Leave-keyboard-out (§5.5) |
| Q4/Q5 Detector | E-K | E1 / **E2 (Fine-tune จาก E-K)** / E3 |
| Q2–Q3, Q6–Q7 Logic | โค้ดใน `ai/` | **ใช้โค้ดเดิมไม่แก้** |

**Exit ของแผนนี้:** Notebook เดียว Run all ได้ทั้งเส้น (Smoke และ Full), Q7 มีรายงาน Proxy, Dev bundle ใช้กับ Worker ได้, โมเดล E-K พร้อมช่วย Annotate ภาพของเรา
