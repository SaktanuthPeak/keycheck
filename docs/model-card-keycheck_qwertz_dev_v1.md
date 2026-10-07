# KeyCheck — Model Card: `keycheck_qwertz_dev_v1`

**อ้างอิง:** [`model-card-template.md`](./model-card-template.md) v0.2 · [`keycheck-technical-specification.md`](./keycheck-technical-specification.md) v1.1 · รายงานผลการทดลองฉบับเต็ม: [`report/04-experiments.md`](./report/04-experiments.md)
**สถานะ:** Dev bundle ฝึกและประเมินด้วยข้อมูล **Proxy (Kaggle QWERTZ)** เท่านั้น ยังไม่ได้รัน Test (Q7)

> **Proxy:** ตัวเลขทุกค่าในเอกสารนี้มาจาก "Kaggle QWERTZ, ภาพสินค้า/เว็บ" บนชุด **Validation** ซึ่งใช้เลือก Threshold ด้วย จึงไม่ใช่ผล Test หลักของขอบเขตสินค้า (คีย์บอร์ด QWERTY ที่ถ่ายด้วยมือถือ) ไฟล์ต้นทาง: `outputs/pipeline/qwertz_v1/q6_eval/` (รอบที่ 4), `q3b_keycls/metrics.json`, `q4_yolo/summary.json`

---

## 1. ข้อมูลโมเดล

| รายการ | ค่า |
| --- | --- |
| `bundle_id` | `keycheck_qwertz_dev_v1` (โฟลเดอร์ `bundles/keycheck_qwertz_dev_v1/`) |
| สถานะ | dev / proxy |
| Detector | `yolo11n` |
| Detector config | `imgsz` 640, `det_score_min` 0.10 (ค่า floor ของหลักฐาน 0.05) |
| Pretrained weights ตั้งต้น | Detector: `yolo11n.pt` (COCO) · ตัวอ่าน: ResNet18 `IMAGENET1K_V1` (torchvision) |
| `checkpoint_hash` (SHA-256) | `weights_yolo.pt` = `2969e3a59b027482afe504cd6c11bcffa538d61c0ef38be03fc311bda1e4ec2f` · `recognizer_keycls.pt` = `e6f4f927eddbfc3d9c5277442b0c891efc22080348943fe47373fe0360414def` |
| `ocr_model_id` | **ไม่ใช้ OCR** ใช้ตัวจำแนก `keycls` (ResNet18, 27 คลาส A–Z + OTHER, ภาพเข้า 64×64, ฝึกด้วยอักษรไทยสังเคราะห์ร่วม) แทน PP-OCRv5 |
| Recognizer สำรอง | PP-OCRv5 (`auto_server`) ใช้ได้โดยตั้ง `q6.recognizer: q3` แต่ไม่อยู่ใน Bundle นี้ |
| `preprocessing_version` | `px_per_unit` 64, `crop_mode` `key_full`, Canvas extent u ∈ [−1.5, 10.5] × [−1.5, 3.5] |
| Layout | `qwerty_stagger_letters_v1` v1 (ใช้งานบนเว็บ) · `qwertz_letters_eval_v1` v1 (ประเมิน Proxy) |
| `thresholds` | `ocr_score_min` 0.99 · `gating_u` 0.6 · `unmatched_cost` 0.6 · `ambiguity_margin_u` 0.15 · `fit_min_matched_fraction` 0.6 · `fit_max_mean_residual_u` 0.3 · `ref_invalid_max` null · `mismatch_min_wrong` 3 · `mismatch_wrong_fraction` 0.5 — เลือกบน Validation เท่านั้น (`experiments/configs/qwertz/thresholds.yaml`) |
| `dataset_version` / `split_manifest_hash` | `kaggle_qwertz_v1` / `4fd3990958a69265afeac12c9b021e1f3879761732085b1f43c54450f41b8e99` |
| `validation_metrics` | objective 1.311 · S1 false alarm 8/422 ภาพ · S2 F1 0.955 · S3 F1 0.980 · S4a ปฏิเสธ 213/215 (ตาราง §5.0) |
| `library_versions` | Inference (backend): Python 3.12.12, torch 2.14.1+cpu, torchvision 0.29.1+cpu, ultralytics 8.4.173, opencv 5.0.0, numpy 2.3.5, scipy 1.18.1 · Training: torch 2.14.1+cu130, torchvision 0.29.1+cu130 (paddlepaddle/paddleocr ไม่ใช้ใน Bundle นี้) |
| Commit | `bdf7b9a` (ค่า `commit` ใน `bundle.json` ขณะสร้าง Bundle) |
| ผู้จัดทำ / วันที่ | `<…>` / 2026-10-05 |

## 2. วัตถุประสงค์และขอบเขต (Spec §1, §3)

**ใช้เพื่อ:** ตรวจว่าคีย์แคป A–Z บนคีย์บอร์ด QWERTY แถวเยื้อง (ANSI/ISO) อยู่ถูกช่องหรือไม่ จากภาพนิ่งหนึ่งภาพ + จุดอ้างอิงสี่จุดที่ผู้ใช้แตะ ผลรายช่อง `correct` / `incorrect` / `uncertain` (Bundle นี้เป็นต้นแบบสำหรับ Demo ไม่ใช่โมเดลสุดท้าย)

**ไม่ได้ออกแบบมาสำหรับ (§3.3):** Ortholinear/Split/Alice, AZERTY/QWERTZ/Dvorak (ใช้ QWERTZ เป็น Proxy เท่านั้น), การอ่านอักษรไทย (อ่านเฉพาะตัวอังกฤษ ฝึกให้ละอักษรไทย), Laptop/Chiclet, Side-print/Artisan, ปุ่มหาย/กลับหัว/Profile ผิดแถว, สวิตช์เสีย, Real-time, การรันบนมือถือ

**ผู้ใช้เป้าหมาย:** ผู้ที่ถอดคีย์แคปทำความสะอาดหรือเปลี่ยนชุดคีย์แคป · Private demo (§13)

**คำเตือนการตีความ:** Detector confidence และคะแนนของตัวจำแนก (`ocr_score`) ไม่ใช่ความน่าจะเป็นที่ Calibrate แล้ว และไม่ใช่ "ความแม่นยำ" ของภาพนั้น (§6.2, §10.5) ช่อง `uncertain` ที่มี `candidate_label` เป็นคำใบ้ ไม่ใช่ผลตรวจ

## 3. ข้อมูลฝึก (Spec §5)

### 3.1 แหล่งข้อมูล

| แหล่ง (`source`) | ใช้ใน | จำนวนภาพ | License | หมายเหตุ |
| --- | --- | ---: | --- | --- |
| `own_capture` | — | 0 | — | ยังไม่ได้เก็บ (เครื่องมือและคู่มือพร้อมแล้ว) |
| `own_capture_fixed` | — | 0 | — | ยังไม่ได้เก็บ |
| `own_pilot` | — | 0 | — | ภาพถ่ายคีย์บอร์ดไทย-อังกฤษจริง 4 ภาพใช้ทดลองเท่านั้น ไม่ได้ใช้ฝึก (§5.7) |
| `public_dataset` / `augment` | Train (ตัวจำแนก) | — | — | อักษรไทยสังเคราะห์ (ผังเกษมณี, ฟอนต์ Noto Thai 6 แบบ) วาดลงบนครอปร้อยละ 50 ระหว่างฝึก |
| `web_cc` | — | 0 | — | ไม่ใช้ |
| Kaggle QWERTZ (Proxy) | Train/Val/Test ของ Dev bundle นี้ | 5,254 (1,884 ต้นฉบับ) | `<ต้องตรวจจากหน้า Dataset>` | ไม่ใช่ข้อมูลของขอบเขตสินค้า |

### 3.2 Split และคีย์บอร์ด (Leave-keyboard-out, §5.5)

Kaggle ไม่มีรหัสคีย์บอร์ดรายตัว จึงใช้ **ยี่ห้อ (brand group)** แทน `keyboard_id` (seed 20261001)

| Split | ภาพ | ยี่ห้อ / ต้นฉบับ | `en_only` / `th_en` | ถูกทั้งหมด / สลับ 1 คู่ / สลับ 2–3 คู่ |
| --- | ---: | ---: | --- | --- |
| Train | 3,762 (ภาพ rectified 9,144) | 1,356 ต้นฉบับ | ทั้งหมดไม่มีอักษรไทย (QWERTZ) / 0 | ทั้งหมดเรียงถูก (ไม่ใช้ภาพสลับในการฝึก) |
| Validation (รวม Held-out 2 ยี่ห้อ) | 215 หลัก + 11 หมุนผิดทิศ | 215 ต้นฉบับ (Held-out 74 ภาพในสถานการณ์ S1/S2) | ทั้งหมด / 0 | S1 430 / S2 (Y↔Z) 430 / S3 860 (คู่ติดกัน คู่ต่างแถว หลายคู่ วน 3) |
| Test — Seen keyboards | 217 หลัก + 6 พิเศษ | 217 ต้นฉบับ | ทั้งหมด / 0 | ล็อกไว้ ยังไม่ได้รัน |
| Test — Unseen keyboards | รวมอยู่ใน Test (ยี่ห้อที่สุ่มกันไว้ประมาณร้อยละ 15) | — | — | ล็อกไว้ ยังไม่ได้รัน |
| Robustness — Validation | S4a 215 · S4b 0 · S4c 11 | — | — | สร้างจากภาพ Validation |
| Robustness — Test | S4a 217 · S4b 1 · S4c 5 | — | — | ล็อกไว้ ยังไม่ได้รัน |

- ภาพ Robustness ไม่อยู่ใน Train: **ใช่** (สร้างจากภาพ Validation/Test เท่านั้น ตาม `split_manifest.json`)
- Annotation: ใช้กรอบคีย์แคปและตัวอักษรจาก Kaggle (VOC, รวม 59 ประเภทเป็น `keycap`) ไม่มีการ annotate เพิ่ม (`assist_model_id` = ไม่มี)
- ลักษณะคีย์บอร์ดที่มีใน Train: ภาพสินค้าและเว็บ หลายยี่ห้อ (71 กลุ่มยี่ห้อที่ใช้ประเมิน) ปุ่มสีเข้มเป็นส่วนใหญ่ มีปุ่มสีอ่อนและไฟ RGB บางส่วน ไม่มีอักษรไทยจริง

## 4. การฝึก (Spec §8)

| รายการ | Detector (YOLO11n) | ตัวอ่าน (ResNet18 `keycls`) |
| --- | --- | --- |
| Epochs (สูงสุด / ที่หยุดจริง) | 100 / 57 (early stop) | 20 / 20 (เลือกรอบที่ 19) |
| Early stopping (Metric / Patience) | ค่า fitness ของ Ultralytics / 15 | ค่าเฉลี่ย accuracy ของ Val ปกติและ Val อักษรไทย / 5 |
| Optimizer, LR, Weight decay, Scheduler | `auto` (Ultralytics), lr0 0.01 | AdamW, 1e-3, 1e-4, cosine + warmup 1 รอบ |
| Batch size (Effective) | 16 | 256 |
| Augmentation (Train เท่านั้น) | ปรับสี หมุนเล็กน้อย เลื่อน ขยาย; **ปิด** flip, mosaic, mixup, cutmix, copy-paste, perspective (ผังปุ่มต้องไม่เพี้ยน §5.6) | ขยาย ±10% เลื่อน ±8% หมุน ±4° ความสว่าง/คอนทราสต์ ±25% สีเทา 10% เบลอ 20% อักษรไทยสังเคราะห์ 50% |
| Seeds | 0 (seed เดียว) | 0 (seed เดียว) |
| Hardware ฝึก | Local: RTX 4060 Laptop 8 GB, RAM 14 GB | Local: RTX 4060 Laptop 8 GB |
| เวลาฝึก / ขนาดไฟล์โมเดล / Peak memory | 22.5 นาที / 5.4 MB / ไม่ได้วัด | 23.7 นาที / 44.8 MB / ไม่ได้วัด |

ข้อมูลฝึกของตัวอ่าน: ครอปจากชุด Train 103,020 ภาพ (ตัวอักษร 79,099 + OTHER 23,921) ประเมินด้วยครอปของ Validation 7,679 ภาพ (ตัวอักษร 5,876 + OTHER 1,803)

## 5. ผลประเมิน

> Test split (§5.1–§5.6) **ยังไม่ได้รัน** (Q7 ล็อกไว้) · Convention เมื่อตัวหารเป็นศูนย์: **N/A พร้อม Counts** (§9.2)

### 5.0 Validation — ใช้เลือกโมเดลและ Threshold (Spec §8.1, §8.3; Plan P4.D) · Proxy

ใช้ S2 (สลับ Y↔Z จริงบนภาพ, ภาพละ 2 ช่องที่ผิด) สำหรับ P/R/F1 ของ `incorrect` และ S1 (ภาพที่เรียงถูกต้อง) สำหรับ Coverage, Uncertain rate, Strict full-board และ False-alarm (ภาพที่ถูกปฏิเสธไม่นับในตัวหารของ Strict และ False-alarm)

| ระบบ | กลุ่ม | ภาพ / ช่อง | `incorrect` P (TP/(TP+FP)) | R (TP/(TP+FN)) | F1 | Coverage | Uncertain rate | Strict full-board acc. | False-alarm image rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | Validation ทั้งหมด | 430 / 11,180 | 0.981 (740/754) | 0.860 (740/860) | 0.917 | 0.880 | 0.120 | 0.448 (190/424) | 0.028 (12/424) |
| Baseline | Held-out 2 ยี่ห้อ | 74 / 1,924 | 0.968 (122/126) | 0.824 (122/148) | 0.891 | 0.832 | 0.168 | 0.400 (28/70) | 0.043 (3/70) |
| **YOLO11n** | Validation ทั้งหมด | 430 / 11,180 | 0.979 (802/819) | 0.933 (802/860) | **0.955** | **0.955** | 0.045 | **0.656 (277/422)** | **0.019 (8/422)** |
| **YOLO11n** | Held-out 2 ยี่ห้อ | 74 / 1,924 | 0.945 (137/145) | 0.926 (137/148) | 0.935 | 0.893 | 0.107 | 0.569 (41/72) | 0.028 (2/72) |

- **Threshold ที่เลือก:** ตาม §1 เลือกด้วย coordinate descent บนฟังก์ชันเป้าหมาย = F1 เฉลี่ยของ S2/S3 + 0.25 × อัตรา `LAYOUT_MISMATCH` ของ S4a + 0.1 × Coverage ของ S1 − 10 × (ส่วนที่เกินเกณฑ์ false alarm 2%, false rejection 2% และพื้น S4a 80%)
- **การปฏิเสธ (fit/mismatch):** S4a (จุดอ้างอิงเลื่อนหนึ่งช่อง) ถูกปฏิเสธ 213/215 (0.991) · False rejection บนภาพมาตรฐาน S1 8/430 (0.019)
- **S3 (สลับจำลอง 860 ภาพ):** YOLO11n P 0.996 (2,507/2,518) R 0.965 (2,507/2,597) F1 0.980 · Baseline F1 0.981
- **คำแนะนำการสลับ:** precision 1.000 ทุกระบบ · recall ของ YOLO11n 0.884 (S2) และ 0.943 (S3)
- ผลราย `keyboard_id`: N/A (Kaggle ไม่มีรหัสคีย์บอร์ดรายตัว มีเฉพาะการแยก Seen/Held-out ยี่ห้อด้านบน)

### 5.1 เปรียบเทียบทั้งระบบ (Test, ชุดมาตรฐาน) — Spec §9.1, §9.3

**N/A** — ยังไม่ได้รัน Test (Q7) ตัวเลขเปรียบเทียบทั้งระบบบน Validation อยู่ใน §5.0 และ [`report/04-experiments.md`](./report/04-experiments.md) ตารางที่ 20–22 (Faster R-CNN: objective 1.201, S2 F1 0.962, S1 false rejection 13/430 จึงไม่ถูกเลือก)

### 5.2 Seen vs Unseen keyboards และ `legend_style` (§9.1, P8)

**N/A สำหรับ Test** — ผลบน Validation (YOLO11n, Proxy):

| ระบบ | กลุ่ม | ภาพ / ช่อง | `incorrect` F1 (S2) | Coverage | Strict full-board | False-alarm image rate |
| --- | --- | --- | --- | --- | --- | --- |
| YOLO11n | Seen (Validation) | 356 / 9,256 | 0.960 (TP 665, FP 9, FN 47) | 0.968 | 0.674 (236/350) | 0.017 (6/350) |
| YOLO11n | Held-out 2 ยี่ห้อ (Validation) | 74 / 1,924 | 0.935 (TP 137, FP 8, FN 11) | 0.893 | 0.569 (41/72) | 0.028 (2/72) |
| YOLO11n | `en_only` | — | N/A: ทุกภาพใน Proxy เป็น `en_only` จึงเท่ากับแถวด้านบน | | | |
| YOLO11n | `th_en` (ภาพจริง, ไม่ใช่ Test) | 4 / 104 | N/A: ไม่มีช่องที่ผิดจริง (คีย์บอร์ดเรียงถูก) · ช่องที่ตัดสินผิด 0/104 | 0.942 (98/104) | 0/4 ภาพ | 0.000 (0/4) |

ช่องว่าง Seen–Held-out: F1 ลดลง 0.025, Coverage ลดลง 0.075 ชี้ว่าความมั่นใจของตัวอ่านลดลงกับยี่ห้อใหม่ (ระบบงดตอบมากขึ้นมากกว่าตอบผิด) แต่ Held-out มีเพียง 2 ยี่ห้อ จึงยังสรุปไม่ได้

### 5.3 รายโมดูล (§9.1) · Validation, Proxy

| ระดับ | Metric | ค่า (Counts) |
| --- | --- | --- |
| Detection | mAP@0.5 / mAP@0.5:0.95 / Precision / Recall | 0.991 / 0.854 / 0.986 / 0.980 (215 ภาพ, 11,222 กรอบ) |
| OCR แยกโมดูล (ตัวจำแนก) | Character accuracy บน GT crops | 0.983 (ตัวอักษร 5,876 ครอป) · ทั้ง 27 คลาส 0.985 (7,679) · OTHER ถูกอ่านเป็นตัวอักษร 0.007 (1,803) |
| OCR บน `th_en` | อักษรไทยถูกอ่านเป็นละตินผิด | ภาพจริง 0/104 ช่อง · Val อักษรไทยสังเคราะห์: ตัวอักษรถูก 0.992, OTHER ถูกอ่านเป็นตัวอักษร 0.004 |
| OCR ปลายทาง | Label accuracy บน Crop จาก Pipeline | 0.994 (S2 ช่องที่ยืนยันแล้ว) · 0.9996 (S3) |
| Mapping | Slot assignment accuracy | 0.997 (S1) · 0.9996 (S3) |

### 5.4 Robustness และการปฏิเสธ (§9.1, §9.2)

**N/A สำหรับ Test** — ผลบน Validation (ใช้ตั้งเกณฑ์):

| ชนิด | ภาพ | ผลที่คาด | Rejection rate / ผล (Counts) |
| --- | ---: | --- | --- |
| `ortholinear_split` | 0 | `LAYOUT_MISMATCH` | N/A (ไม่มีภาพใน Proxy) · Unit test แสดงว่า Ortholinear ที่แตะจุดถูกต้อง **ไม่ถูกปฏิเสธ** (xfail) |
| `wrong_reference` (S4a เลื่อนหนึ่งช่อง) | 215 | `LAYOUT_MISMATCH` | 0.991 (213/215) · Baseline 1.000 (215/215) |
| ภาพหมุนผิดทิศ (S4c) | 11 | Reject หรือไม่ให้ผลผิด | ปลอดภัย 10/11 · แจ้งผิด 1/11 · ปฏิเสธ 0/11 |
| ปุ่มมองไม่เห็นบางส่วน (S4b) | 0 | `uncertain` | N/A (ไม่มีรายการใน Validation) |

### 5.5 Latency และทรัพยากร (§8.3, §9.1)

Hardware: เครื่องพัฒนา (ไม่ใช่เครื่อง Worker จริง) Intel Core i7-13700HX, RAM 14 GB, Linux 6.14 · PyTorch CPU 8 threads · `OCR_DEVICE` = `cpu` · จำนวนภาพที่วัด 60 (Validation หลังอุ่นเครื่อง 1 ภาพ)

| ขั้น | Median (ms) | P95 (ms) |
| --- | ---: | ---: |
| rectify | 2 | 2 |
| detect | 13 | 20 |
| read (ตัวจำแนก ≤ 26 ครอป) | 22 | 36 |
| match | 2 | 2 |
| End-to-end (`Inspector`) | 39 | 58 |
| Cold start (โหลด Bundle) | 1,700 | — |

Peak memory: 711 MB (RSS ของโปรเซส) · ผ่าน HTTP API (สร้างงาน → คิว → ผล) ประมาณ 200 ms ต่อภาพ

### 5.6 Error analysis (§16.4) · Validation S1, YOLO11n (11,180 ช่อง)

- **สาเหตุของ `uncertain`/การปฏิเสธ:** ความมั่นใจต่ำกว่าเกณฑ์ 266 ช่อง (2.4%) · ภาพถูกปฏิเสธ 8 ภาพ (208 ช่อง) · จับคู่กำกวม 137 (1.2%) · ตัวอ่านตอบ OTHER 82 (0.7%) · ตรวจไม่พบปุ่ม 7 (0.06%)
- **False alarm 22 ช่องใน 8 ภาพ:** คู่ที่พบบ่อย T↔R (6), T↔Z (6), Z↔U (4), E→R (2) เป็นปุ่มติดกันในแถวบน → ต้นเหตุหลักคือการจับคู่ปุ่มเข้าช่องข้างเคียง ไม่ใช่การอ่าน
- **ชนิดการสลับ (S3 recall):** คู่ติดกัน 0.960 · คู่ต่างแถว 0.970 · วน 3 0.972 · หลายคู่ 0.962 (ใกล้เคียงกัน)
- **คำใบ้ (`candidate_label`, ความมั่นใจ ≥ 0.80):** ถูก 154/179 (0.86) จึงแสดงเป็นสีเหลือง ไม่นับเป็นผลยืนยัน
- **ฟอนต์/ไฟ:** ภาพ corsair14 (ฟอนต์เกมมิ่ง ไฟ RGB) ได้ 26/0/0 (PP-OCRv5 เดิม 14/0/12)
- Letter confusion matrix: ไม่มีไฟล์แนบ (ตัวอ่านผิดน้อยเกินกว่าจะสร้าง matrix ที่มีความหมาย; ตัวอักษรที่อ่านถูกน้อยที่สุด A 0.956, Q 0.969)
- Error มาจากขั้นใดมากที่สุด: **Matching** (การแจ้งผิดที่เหลือ) และ **ความมั่นใจของตัวอ่าน** (สาเหตุหลักของ `uncertain`) ส่วน Detection มีผลน้อยมาก

### 5.7 ผลบนข้อมูล Proxy

"Proxy: Kaggle QWERTZ, ภาพสินค้า/เว็บ" — ตาราง §5.0–§5.6 ทั้งหมด และ `outputs/pipeline/qwertz_v1/q6_eval/val_report.md` (รอบที่ 4) ยังไม่มี `q7_test/test_report.md`

ภาพถ่ายคีย์บอร์ดไทย-อังกฤษจริง (ไม่ใช่ Test, จุดอ้างอิงกำหนดโดยผู้จัดทำ, คีย์บอร์ดเรียงถูก): Logitech 3 ภาพ ได้ 23/0/3, 25/0/1, 25/0/1 และคีย์บอร์ดแบบกลไกสีขาว 1 ภาพ (รุ่นที่ไม่เคยฝึก) ได้ 25/0/1 (ถูก/ผิด/ไม่แน่ใจ)

## 6. เหตุผลการเลือกโมเดล (P4.D)

เลือก **YOLO11n + ตัวจำแนก ResNet18** เพราะได้คะแนนเป้าหมายบน Validation สูงสุด (1.311 เทียบกับ Baseline 1.204 และ Faster R-CNN 1.201) Faster R-CNN ได้ F1 สูงกว่าเล็กน้อย (S2 0.962) แต่ปฏิเสธภาพที่ถูกต้อง 13/430 (3.0%) เกินเกณฑ์ 2% ส่วน Baseline ได้ F1 ของ S3 ใกล้เคียงกัน (0.981) แต่ Coverage ต่ำกว่าชัดเจน (0.880 เทียบกับ 0.955) และ Strict full-board ต่ำกว่า (0.448 เทียบกับ 0.656) YOLO11n ยังเล็กที่สุด (5.4 MB) และตรวจจับบน CPU ได้ใน 13 ms (มัธยฐาน) ความต่างของคะแนนระหว่าง Detector อยู่ที่ 0.1 ขณะที่การเปลี่ยนตัวอ่านจาก PP-OCRv5 เป็นตัวจำแนกเพิ่มคะแนนกว่า 0.7 (ตารางที่ 20 ในรายงาน)

## 7. ข้อจำกัดที่ทราบ

- [x] Generic letter-block: ร้อยละ 2.8 ของภาพมีปุ่มอย่างน้อยหนึ่งปุ่มที่ตำแหน่งทำนายจาก 4 จุดคลาดเกิน 0.25u (ค่าคลาดสูงสุดต่อภาพ: มัธยฐาน 0.042u, P90 0.098u, n = 1,594 ภาพ)
- [x] ผลอ้างได้เฉพาะลักษณะคีย์บอร์ดใน Proxy (ภาพสินค้า QWERTZ หลายยี่ห้อ) และภาพไทยจริง 4 ภาพ ยังไม่มีข้อมูลกล้องมือถือ/แสงจริงที่เป็นระบบ
- [x] Held-out มีเพียง 2 ยี่ห้อ (74 ภาพ) — ช่วงความไม่แน่นอนของผลข้ามรุ่นกว้าง
- [x] Baseline ตรวจ layout fit ไม่ได้ (§7.8) แต่ปฏิเสธ S4a ได้ด้วยเงื่อนไขผิดพร้อมกันส่วนใหญ่และ `ref_invalid_max`
- [x] ขึ้นกับความแม่นของจุดอ้างอิงที่ผู้ใช้แตะ: การแจ้งผิดที่เหลือส่วนใหญ่มาจากการจับคู่เข้าช่องข้างเคียง
- [x] ไม่ตรวจปุ่มหาย/กลับหัว; "ตรวจไม่พบ" ไม่ได้แปลว่าปุ่มหาย (§3.3)
- [x] Score ไม่ Calibrate (§6.2) — `ocr_score_min` 0.99 สูงมาก
- [x] Ortholinear ที่แตะจุดถูกต้องไม่ถูกปฏิเสธ (unit test xfail)
- [x] `bundle_id` เดิมถูกใช้ซ้ำหลังฝึกตัวอ่านใหม่ด้วยอักษรไทย (hash ตัวอ่านเปลี่ยนจาก `5ff0e741…` เป็น `e6f4f927…`) — Bundle ถัดไปควรเปลี่ยนเวอร์ชัน
- [x] ผลรอบก่อนหน้าของ Q6 ถูกเขียนทับ (ดูรายงานตารางที่ 20)

## 8. ความเป็นส่วนตัวและการใช้ข้อมูล (§12.5, §13)

- ภาพผู้ใช้เว็บไม่ถูกนำไปเพิ่ม Dataset อัตโนมัติ; ภาพหมดอายุ 24 ชม. Metadata 168 ชม. (7 วัน) ตาม `backend/.env.sample`
- Dataset ใน Bundle นี้เป็นภาพสินค้าสาธารณะจาก Kaggle ไม่มีข้อมูลส่วนตัว · ภาพถ่ายคีย์บอร์ดไทยจริง 4 ภาพเป็นของผู้จัดทำ เก็บใน `data/pilot_uploads/` (ไม่อยู่ใน git) และไม่ได้ใช้ฝึก

## 9. License และ Attribution

> ตรวจซ้ำก่อนเผยแพร่ทุกครั้ง (§13, P9.A) — ข้อมูลด้านล่างอ้างอิงตาม [`model-card-template.md`](./model-card-template.md) §9 และไม่ใช่คำปรึกษาทางกฎหมาย

| ส่วนประกอบ | License | ผลต่อ KeyCheck | แหล่งตรวจ |
| --- | --- | --- | --- |
| Ultralytics YOLO (โค้ด + `yolo11n.pt`) | **AGPL-3.0** หรือ Enterprise License | Bundle นี้ใช้ YOLO → ถ้าเผยแพร่/ให้บริการผ่านเครือข่าย ต้องเปิดซอร์สภายใต้ AGPL-3.0 หรือซื้อ Enterprise License | [ultralytics.com/license](https://www.ultralytics.com/license) |
| Torchvision (โค้ด) | BSD-3-Clause | คงข้อความ Copyright/License | [github.com/pytorch/vision](https://github.com/pytorch/vision/blob/main/LICENSE) |
| ResNet18 `IMAGENET1K_V1` (ตั้งต้นของตัวอ่าน) | ไม่มี License เฉพาะของ Weights; ฝึกบน ImageNet-1K | ใช้เพื่อการศึกษาที่ไม่ใช่เชิงพาณิชย์ได้ ห้ามใช้เชิงพาณิชย์โดยไม่ตรวจสิทธิ์เพิ่ม | [image-net.org](https://image-net.org/download) |
| PaddleOCR / PP-OCRv5 | Apache-2.0 | **ไม่ได้ใช้ใน Bundle นี้** (ใช้ในการทดลอง Q3 เท่านั้น) | [github.com/PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) |
| ฟอนต์ Noto Thai (สังเคราะห์ข้อมูลฝึก) | SIL Open Font License 1.1 | ใช้สร้างภาพฝึกเท่านั้น ไม่แจกจ่ายฟอนต์ | [fonts.google.com/noto](https://fonts.google.com/noto) |
| OpenCV / SciPy / NumPy | Apache-2.0 / BSD-3-Clause / BSD-3-Clause | — | หน้า License ของแต่ละโครงการ |
| Kaggle QWERTZ dataset (Proxy) | `<ต้องตรวจจากหน้า Dataset และแหล่ง Roboflow>` | ใช้ได้ตามเงื่อนไขนั้น ห้ามแจกจ่ายภาพถ้าไม่อนุญาต | `<URL>` |
| Dataset ของ KeyCheck | ยังไม่มี | — | — |
| โค้ด KeyCheck | `<ยังไม่ได้กำหนด>` (ต้องเข้ากันได้กับ AGPL-3.0 เพราะใช้ YOLO) | — | — |

**Attribution ที่ต้องแสดง:** Ultralytics YOLO11; Torchvision ResNet18 (ImageNet-1K, ใช้เพื่อการวิจัย/การศึกษาที่ไม่ใช่เชิงพาณิชย์); Noto Thai fonts (SIL OFL 1.1); Kaggle QWERTZ keyboard dataset (ตามเงื่อนไขของแหล่ง)

## 10. ประวัติการแก้ไข

| วันที่ | เวอร์ชัน | สิ่งที่เปลี่ยน |
| --- | --- | --- |
| 2026-10-05 | dev_v1 (ตัวอ่าน `5ff0e741…`) | YOLO11n + ตัวจำแนก ResNet18 (Q6 รอบที่ 3) แทน PP-OCRv5 |
| 2026-10-05 | dev_v1 (ตัวอ่าน `e6f4f927…`) | ฝึกตัวจำแนกใหม่ด้วยอักษรไทยสังเคราะห์ (Q6 รอบที่ 4); เพิ่ม `candidate_label` ในผลรายช่อง |
| 2026-10-07 | model card | เขียน Model card ฉบับแรกจากผลรอบที่ 4 |
