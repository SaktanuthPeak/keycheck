# KeyCheck — Model Card Template

**อ้างอิง:** [`keycheck-technical-specification.md`](./keycheck-technical-specification.md) v1.1 §3, §5, §6, §8, §9, §12.4, §13, §14.2, §16.4, §20 · [`implementation-plan.md`](./implementation-plan.md) P2.D, P4.D, P8, P9.A · [`annotation-guide.md`](./annotation-guide.md) · [`capture-guide.md`](./capture-guide.md) · [`dataset-format.md`](./dataset-format.md)
**เวอร์ชันแม่แบบ:** 0.2 — 5 ตุลาคม 2026

> **วิธีใช้:** Copy ไฟล์นี้เป็น `docs/model-card-<bundle_id>.md` หนึ่งไฟล์ต่อ Model bundle แล้วเติมทุก `<…>` ห้ามลบหัวข้อ — ถ้าไม่มีข้อมูลให้เขียน "ไม่มี" หรือ "N/A" พร้อมเหตุผล (Spec §9.2: ไม่แทนด้วยค่าเงียบ ๆ)
>
> **กฎตัวเลข:** ทุก Metric ต้องมี **Counts** (เช่น TP/FP/FN, จำนวนช่อง/ภาพ) ไม่ใช่แค่ % (P8) · ผลบน Validation (§5.0) กับผล Test (§5.1–§5.4) แยกตารางกัน · ผล Proxy (Kaggle QWERTZ) แยกจากผล Test หลักและติดป้าย "Proxy" เสมอ · ห้ามใส่ตัวเลขจำลอง (§17.3)

---

## 1. ข้อมูลโมเดล

| รายการ | ค่า |
| --- | --- |
| `bundle_id` | `<…>` |
| สถานะ | `<dev / proxy / candidate / final>` |
| Detector | `<baseline (fixed layout crops) / yolo11n / fasterrcnn_resnet50_fpn_v2 / ssdlite320_mobilenet_v3_large>` |
| Detector config | `<imgsz / min_size–max_size / 320>` (§8.2: Input ต่างกัน = เปรียบเทียบ Configuration ไม่ใช่ Architecture ล้วน) |
| Pretrained weights ตั้งต้น | `<yolo11n.pt / FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1 / …>` |
| `checkpoint_hash` (SHA-256) | `<…>` |
| `ocr_model_id` | `<เช่น PP-OCRv5_server_rec + ภาษา/Det model ถ้ามี>` |
| Recognizer สำรอง | `<ไม่มี / YOLO11n-cls …>` (Gate G1, §6.3) |
| `preprocessing_version` | `<…>` (`px_per_unit`, `crop_mode`, Canvas extent) |
| Layout | `<layout_id>` v`<version>` |
| `thresholds` | `<ไฟล์/ค่า: OCR score, Gating, Unmatched cost, Ambiguity, fit_thresholds>` — เลือกบน Validation เท่านั้น |
| `dataset_version` / `split_manifest_hash` | `<…>` / `<…>` |
| `validation_metrics` | `<ค่าที่บันทึกใน Bundle (Spec §12.4, Plan P4.D) — ต้องตรงกับตาราง §5.0>` |
| `library_versions` | `<python, torch, torchvision, ultralytics, paddlepaddle, paddleocr, opencv, numpy, scipy>` |
| Commit | `<git sha>` |
| ผู้จัดทำ / วันที่ | `<…>` / `<YYYY-MM-DD>` |

## 2. วัตถุประสงค์และขอบเขต (Spec §1, §3)

**ใช้เพื่อ:** ตรวจว่าคีย์แคป A–Z บนคีย์บอร์ด QWERTY แถวเยื้อง (ANSI/ISO) อยู่ถูกช่องหรือไม่ จากภาพนิ่งหนึ่งภาพ + จุดอ้างอิงสี่จุดที่ผู้ใช้แตะ ผลรายช่อง `correct` / `incorrect` / `uncertain`

**ไม่ได้ออกแบบมาสำหรับ (§3.3):** Ortholinear/Split/Alice, AZERTY/QWERTZ/Dvorak, การอ่านอักษรไทย, Laptop/Chiclet, Side-print/Artisan, ปุ่มหาย/กลับหัว/Profile ผิดแถว, สวิตช์เสีย, Real-time, การรันบนมือถือ

**ผู้ใช้เป้าหมาย:** ผู้ที่ถอดคีย์แคปทำความสะอาดหรือเปลี่ยนชุดคีย์แคป · Private demo (§13)

**คำเตือนการตีความ:** Detector confidence และ OCR score ไม่ใช่ความน่าจะเป็นที่ Calibrate แล้ว และไม่ใช่ "ความแม่นยำ" ของภาพนั้น (§6.2, §10.5)

## 3. ข้อมูลฝึก (Spec §5)

### 3.1 แหล่งข้อมูล

| แหล่ง (`source`) | ใช้ใน | จำนวนภาพ | License | หมายเหตุ |
| --- | --- | ---: | --- | --- |
| `own_capture` (คีย์บอร์ดยืม ถอดปุ่มได้) | Train/Val/Test | `<n>` | `own` | แหล่งหลัก |
| `own_capture_fixed` (ถอดปุ่มไม่ได้ เช่น ห้องแล็บ) | Train/Val/Test (ภาพถูกทั้งหมด) | `<n>` | `<ได้รับอนุญาตจาก …>` | False-alarm |
| `own_pilot` (ภาพ Pilot P1.B) | Train (ภาพของคีย์บอร์ด `unseen_test` = `excluded`) | `<n>` | `own` | §5.2 |
| `public_dataset` / `augment` | Train เท่านั้น | `<n>` | `<ตามแหล่ง>` | การทดลองเสริม (P2.B′) |
| `web_cc` | Train เท่านั้น | `<n>` | `<CC …>` | บันทึก `source_url` รายภาพ |
| Kaggle QWERTZ (Proxy) | `<เฉพาะ Dev bundle>` | `<n>` | `<ตรวจจากหน้า Dataset>` | ไม่ใช่ข้อมูลของขอบเขตสินค้า |

### 3.2 Split และคีย์บอร์ด (Leave-keyboard-out, §5.5)

| Split | ภาพ | คีย์บอร์ด | `en_only` / `th_en` | ถูกทั้งหมด / สลับ 1 คู่ / สลับ 2–3 คู่ |
| --- | ---: | ---: | --- | --- |
| Train | `<n>` | `<n>` | `<n>/<n>` | `<n>/<n>/<n>` |
| Validation (รวม Held-out `<kb_id>`) | `<n>` | `<n>` | `<n>/<n>` | `<n>/<n>/<n>` |
| Test — Seen keyboards | `<n>` | `<n>` | `<n>/<n>` | `<n>/<n>/<n>` |
| Test — Unseen keyboards (`<kb_id, …>`) | `<n>` | `<n>` | `<n>/<n>` | `<n>/<n>/<n>` |
| Robustness — Validation (ตั้งเกณฑ์) | `<n>` | `<n>` | — | แยกตามชนิด (`robustness=<ชนิด>` ใน `note`) |
| Robustness — Test (รายงาน §5.4) | `<n>` | `<n>` | — | แยกตามชนิด |

- ภาพ Robustness ไม่อยู่ใน Train: ถ่ายเฉพาะบนคีย์บอร์ด `unseen_test` / `heldout_val` ([`capture-guide.md`](./capture-guide.md) B.5) ยืนยันจาก `split_manifest.json`: `<ใช่/ไม่ — ระบุภาพที่หลุด>`
- Annotation: ตาม [`annotation-guide.md`](./annotation-guide.md) v`<…>`, เครื่องมือ `<CVAT/Label Studio>`, `assist_model_id` = `<…/ไม่มี>` (จาก `metadata/annotation_log.csv`), สัดส่วน Review `<…>`
- ลักษณะคีย์บอร์ดที่มีใน Train (สี, ฟอนต์, `legend_position`, `profile`): `<สรุป>` — อ้างได้เฉพาะลักษณะที่มีใน Dataset (§3.1)

## 4. การฝึก (Spec §8)

| รายการ | ค่า |
| --- | --- |
| Epochs (สูงสุด / ที่หยุดจริง) | `<…>` |
| Early stopping (Metric / Patience) | `<…>` |
| Optimizer, LR, Weight decay, Scheduler | `<…>` |
| Batch size (Effective) | `<…>` |
| Augmentation (Train เท่านั้น) | `<Brightness/Contrast, Noise, Blur, Scale/มุมเล็กน้อย>`; ไม่ Flip / ไม่หมุนแรง; Mosaic/MixUp `<ปิด/เปิด + เหตุผล>` (§5.6) |
| Seeds | `<…>` (เป้า 3 สำหรับโมเดลหลัก) |
| Hardware ฝึก | `<GPU, RAM / Colab / Local>` |
| เวลาฝึก / ขนาดไฟล์โมเดล / Peak memory | `<…>` |

## 5. ผลประเมิน

> Test split (§5.1–§5.6) รัน **ครั้งเดียว** หลังล็อก Config (P8) วันที่รัน `<…>` Commit `<…>` · Convention เมื่อตัวหารเป็นศูนย์: **N/A พร้อม Counts** (§9.2)

### 5.0 Validation — ใช้เลือกโมเดลและ Threshold (Spec §8.1, §8.3; Plan P4.D)

ตัวเลขชุดนี้คือ `validation_metrics` ใน Bundle และเป็นหลักฐานของ §6 ห้ามใช้ผล Test (§5.1–§5.4) เลือกโมเดลหรือ Threshold

| ระบบ | กลุ่ม | ภาพ / ช่อง | `incorrect` P (TP/(TP+FP)) | R (TP/(TP+FN)) | F1 | Coverage | Uncertain rate | Strict full-board acc. | False-alarm image rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | Validation ทั้งหมด | `<n>/<n>` | `<x (a/b)>` | `<x (a/b)>` | `<x>` | `<x (a/b)>` | `<x (a/b)>` | `<x (a/b)>` | `<x (a/b)>` |
| Baseline | Held-out `<kb_id>` | `<n>/<n>` | | | | | | | |
| `<detector>` | Validation ทั้งหมด | `<n>/<n>` | | | | | | | |
| `<detector>` | Held-out `<kb_id>` | `<n>/<n>` | | | | | | | |

- Threshold ที่เลือก (OCR score, Gating, Unmatched cost, Ambiguity, `fit_thresholds`) และเกณฑ์การเลือก: `<…>`
- `fit_thresholds` ตั้งจากภาพมาตรฐาน Validation + Robustness ส่วน Validation (`ortholinear_split`, `wrong_reference` จากภาพ Validation): Rejection rate `<x (a/b)>`, False rejection บนภาพมาตรฐาน `<x (a/b)>`
- ผลราย `keyboard_id` บน Validation: `<ตารางหรือไฟล์แนบ>`

### 5.1 เปรียบเทียบทั้งระบบ (Test, ชุดมาตรฐาน) — Spec §9.1, §9.3

| ระบบ | `incorrect` P (TP/(TP+FP)) | R (TP/(TP+FN)) | F1 | Coverage | Uncertain rate | Strict full-board acc. | False-alarm image rate | Observed-label acc. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | `<x (a/b)>` | `<x (a/b)>` | `<x>` | `<x (a/b)>` | `<x (a/b)>` | `<x (a/b)>` | `<x (a/b)>` | `<x (a/b)>` |
| YOLO11n `<imgsz>` | | | | | | | | |
| Faster R-CNN R50-FPN v2 | | | | | | | | |
| SSDLite320 (ถ้ามี) | | | | | | | | |

TP/FP/FN นิยามตาม §9.2: FN รวมช่องที่ผิดจริงแต่ได้ `correct` **หรือ** `uncertain`

### 5.2 Seen vs Unseen keyboards และ `legend_style` (§9.1, P8)

| ระบบ | กลุ่ม | ภาพ / ช่อง | `incorrect` F1 | Coverage | Strict full-board | False-alarm image rate |
| --- | --- | --- | --- | --- | --- | --- |
| `<…>` | Seen | `<n>/<n>` | | | | |
| `<…>` | Unseen | `<n>/<n>` | | | | |
| `<…>` | `en_only` | `<n>/<n>` | | | | |
| `<…>` | `th_en` | `<n>/<n>` | | | | |

ผลราย `keyboard_id`: `<ตารางหรือไฟล์แนบ>` · ช่องว่าง Seen–Unseen: `<สรุปและสาเหตุที่คาด>`

### 5.3 รายโมดูล (§9.1)

| ระดับ | Metric | ค่า (Counts) |
| --- | --- | --- |
| Detection | mAP@0.5 / mAP@0.5:0.95 / Precision / Recall | `<…>` |
| OCR แยกโมดูล | Character accuracy บน GT crops | `<x (a/b)>` |
| OCR บน `th_en` | อักษรไทยถูกอ่านเป็นละตินผิด | `<x (a/b)>` |
| OCR ปลายทาง | Label accuracy บน Crop จาก Pipeline | `<x (a/b)>` |
| Mapping | Slot assignment accuracy | `<x (a/b)>` |

### 5.4 Robustness และการปฏิเสธ (§9.1, §9.2)

ใช้เฉพาะภาพ Robustness ที่อยู่ใน Test และ `wrong_reference` ที่สร้างจากภาพมาตรฐานใน Test ([`capture-guide.md`](./capture-guide.md) B.5) ส่วน Validation ใช้ตั้งเกณฑ์ใน §5.0 เท่านั้น

| ชนิด (`robustness=<ชนิด>`) | ภาพ | ผลที่คาด | Rejection rate / Uncertain rate (Counts) |
| --- | ---: | --- | --- |
| `ortholinear_split` | `<n>` | `LAYOUT_MISMATCH` | `<…>` |
| `wrong_reference` (เลื่อนหนึ่งช่อง / เริ่มผิดมุม) | `<n>` | `LAYOUT_MISMATCH` (Baseline ตรวจไม่ได้) | `<…>` |
| `blur` / `glare` / `occlusion` / `partial` | `<n>` | `uncertain` / Reject | `<…>` |
| ช่อง GT อ่านไม่ได้ (`readable = false`) | `<n>` ช่อง | `uncertain` | `<…>` |

Baseline: Layout fit check ใช้ไม่ได้ (คำเตือน `layout_fit_not_checked`, §7.8) — รายงานเป็นข้อจำกัด ไม่ใช่ 0%

### 5.5 Latency และทรัพยากร (§8.3, §9.1; วัดบนเครื่อง Worker ไม่ใช่ Colab)

Hardware: `<CPU/GPU, RAM, OS>` · `OCR_DEVICE` = `<cpu>` · จำนวนภาพที่วัด `<n>`

| ขั้น | Median (ms) | P95 (ms) |
| --- | ---: | ---: |
| rectify | | |
| detect | | |
| read (OCR) | | |
| match | | |
| End-to-end (Worker) | | |
| Cold start (โหลด Bundle) | | — |

Peak memory: `<MB>`

### 5.6 Error analysis (§16.4)

- แยกตามแสง มุม Blur ชนิดการสลับ (ข้างกัน/คนละแถว), `keyboard_id`, `legend_style`, สี ฟอนต์ ตำแหน่ง Legend, Profile: `<…>`
- Letter confusion matrix: `<ไฟล์แนบ>`
- ตัวอย่าง FP / FN พร้อมภาพจริง: `<…>`
- Error มาจากขั้นใดมากที่สุด (Geometry / Detection / OCR / Matching): `<…>`

### 5.7 ผลบนข้อมูล Proxy (ถ้ามี — ไม่ใช่ผล Test หลัก)

"Proxy: Kaggle QWERTZ, ภาพสินค้า/เว็บ" — `<ตาราง/ลิงก์ q6_eval/val_report.md, q7_test/test_report.md>`

## 6. เหตุผลการเลือกโมเดล (P4.D)

`<เลือกจากผล Validation ทั้งระบบใน §5.0 (รวมแถว Held-out keyboard) + ความเร็ว + ทรัพยากร; อ้างตัวเลขจาก §5.0 เท่านั้น; ถ้า Baseline ดีเท่ากันและเร็วกว่า ให้ระบุตามจริง (§6.4)>`

## 7. ข้อจำกัดที่ทราบ

- [ ] Generic letter-block: รุ่นที่คลาดจาก Layout เกิน Gating: `<…>` (§12.1)
- [ ] ผลอ้างได้เฉพาะลักษณะคีย์บอร์ดที่มีใน Dataset (`<n>` คีย์บอร์ด) และกล้อง/แสงที่เก็บ
- [ ] Unseen keyboards มีเพียง `<n>` ตัว — ช่วงความไม่แน่นอนของผลข้ามรุ่นกว้าง
- [ ] Baseline ตรวจ `LAYOUT_MISMATCH` ไม่ได้ (§7.8)
- [ ] ขึ้นกับความแม่นของจุดอ้างอิงที่ผู้ใช้แตะ: ผลเมื่อ Jitter จุด `<…>`
- [ ] ไม่ตรวจปุ่มหาย/กลับหัว; "ตรวจไม่พบ" ไม่ได้แปลว่าปุ่มหาย (§3.3)
- [ ] Score ไม่ Calibrate (§6.2)
- [ ] `<ข้อจำกัดอื่นจาก Error analysis>`

## 8. ความเป็นส่วนตัวและการใช้ข้อมูล (§12.5, §13)

- ภาพผู้ใช้เว็บไม่ถูกนำไปเพิ่ม Dataset อัตโนมัติ; ภาพหมดอายุ `<24>` ชม. Metadata `<7>` วัน
- ภาพใน Dataset ลบ GPS แล้ว ไม่มีข้อมูลส่วนตัว; คีย์บอร์ดยืม/ห้องแล็บได้รับอนุญาต: `<…>`

## 9. License และ Attribution

> ตรวจซ้ำก่อนเผยแพร่ทุกครั้ง (§13, P9.A) — ข้อมูลด้านล่างตรวจจากเอกสารของแต่ละโครงการวันที่ 5 ต.ค. 2026 และไม่ใช่คำปรึกษาทางกฎหมาย

| ส่วนประกอบ | License | ผลต่อ KeyCheck | แหล่งตรวจ |
| --- | --- | --- | --- |
| Ultralytics YOLO (โค้ด `ultralytics` + Pretrained `yolo11n.pt`) | **AGPL-3.0** หรือ Ultralytics Enterprise License | Ultralytics ระบุว่าโมเดลที่ฝึก/Fine-tune ด้วย Ultralytics อยู่ภายใต้ AGPL-3.0 โดยปริยาย → ถ้า Bundle ใช้ YOLO และเผยแพร่/ให้บริการผ่านเครือข่าย ต้องเปิดซอร์สโปรเจกต์ภายใต้ AGPL-3.0 หรือซื้อ Enterprise License | [ultralytics.com/license](https://www.ultralytics.com/license) |
| Torchvision (โค้ด) | BSD-3-Clause | ต้องคงข้อความ Copyright/License | [github.com/pytorch/vision](https://github.com/pytorch/vision/blob/main/LICENSE) |
| Torchvision pretrained weights (`FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1`, `SSDLite320_MobileNet_V3_Large_Weights.COCO_V1`) | Torchvision ไม่ได้ระบุ License เฉพาะของ Weights — เอกสารระบุว่า Weights "may have their own licenses or terms … derived from the dataset used for training" และผู้ใช้ต้องตรวจสิทธิ์เอง | Weights ได้มาจาก **สองชุดข้อมูล**: (1) Backbone pretrained บน **ImageNet-1K** (`weights_backbone` = `ResNet50_Weights.IMAGENET1K_V1` / `MobileNet_V3_Large_Weights.IMAGENET1K_V1` ใน Reference recipe ของ Torchvision) — ข้อตกลงของ ImageNet อนุญาตเฉพาะ **การวิจัยและการศึกษาที่ไม่ใช่เชิงพาณิชย์** (ตรวจที่ [image-net.org](https://image-net.org/download)); (2) Detection head ฝึกบน **COCO**: Annotations ใช้ CC BY 4.0, ภาพเป็นของเจ้าของบน Flickr ตาม Flickr Terms of Use (ตรวจที่ [cocodataset.org](https://cocodataset.org/#termsofuse)) → ใช้ในโครงงานการศึกษาได้ ระบุ Attribution ทั้งสองชุด **ห้ามใช้เชิงพาณิชย์โดยไม่ตรวจสิทธิ์เพิ่ม** | [docs.pytorch.org/vision/stable/models.html](https://docs.pytorch.org/vision/stable/models.html) · [Reference recipes](https://github.com/pytorch/vision/tree/main/references/detection) |
| PaddleOCR (โค้ด) | Apache-2.0 | คง NOTICE/License, ระบุการแก้ไข (ถ้ามี) | [github.com/PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) |
| PP-OCRv5 weights (`<PP-OCRv5_server_rec>`) | Apache-2.0 (ตาม Model card บน Hugging Face) | เช่นเดียวกับโค้ด | [huggingface.co/PaddlePaddle/PP-OCRv5_server_rec](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec) |
| PaddlePaddle | Apache-2.0 | — | [github.com/PaddlePaddle/Paddle](https://github.com/PaddlePaddle/Paddle) |
| OpenCV (≥ 4.5) / SciPy / NumPy | Apache-2.0 / BSD-3-Clause / BSD-3-Clause | — | หน้า License ของแต่ละโครงการ |
| Kaggle QWERTZ dataset (Proxy) | `<ตรวจจากหน้า Dataset และแหล่ง Roboflow ที่รวมไว้>` | ใช้ได้เฉพาะตามเงื่อนไขนั้น; ห้ามแจกจ่ายภาพถ้าไม่อนุญาต | `<URL>` |
| Public dataset / ภาพ CC อื่น | `<รายแหล่ง>` | Train เท่านั้น; Attribution รายภาพ | `<URL>` |
| Dataset ของ KeyCheck | `<…>` | `<เผยแพร่หรือไม่>` | — |
| โค้ด KeyCheck | `<…>` (ต้องเข้ากันได้กับ AGPL-3.0 ถ้าใช้ YOLO) | — | — |

**Attribution ที่ต้องแสดง:** `<Ultralytics YOLO11; Torchvision Faster R-CNN ResNet50-FPN V2 / SSDLite320 MobileNetV3 (COCO, Backbone ImageNet-1K); PaddleOCR PP-OCRv5; COCO dataset; ImageNet-1K (ใช้เพื่อการวิจัย/การศึกษาที่ไม่ใช่เชิงพาณิชย์); แหล่งข้อมูลเสริม>`

## 10. ประวัติการแก้ไข

| วันที่ | เวอร์ชัน | สิ่งที่เปลี่ยน |
| --- | --- | --- |
| `<…>` | `<…>` | `<…>` |
