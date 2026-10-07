# ภาคผนวก

## ภาคผนวก ก เอกสารอ้างอิง

**วิธีการและโมเดล**

1. J. Redmon, S. Divvala, R. Girshick, A. Farhadi, "You Only Look Once: Unified, Real-Time Object Detection," *CVPR*, 2016.
2. Ultralytics, "YOLO11" documentation. https://docs.ultralytics.com/models/yolo11/
3. S. Ren, K. He, R. Girshick, J. Sun, "Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks," *NeurIPS*, 2015.
4. T.-Y. Lin, P. Dollár, R. Girshick, K. He, B. Hariharan, S. Belongie, "Feature Pyramid Networks for Object Detection," *CVPR*, 2017.
5. PyTorch/torchvision, "fasterrcnn_resnet50_fpn_v2." https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.detection.fasterrcnn_resnet50_fpn_v2.html
6. K. He, X. Zhang, S. Ren, J. Sun, "Deep Residual Learning for Image Recognition," *CVPR*, 2016.
7. X. Li et al., "Generalized Focal Loss: Learning Qualified and Distributed Bounding Boxes for Dense Object Detection," *NeurIPS*, 2020. (DFL)
8. Y. Du et al., "PP-OCR: A Practical Ultra Lightweight OCR System," arXiv:2009.09941, 2020; PaddleOCR documentation. https://www.paddleocr.ai/
9. I. Loshchilov, F. Hutter, "Decoupled Weight Decay Regularization," *ICLR*, 2019. (AdamW)
10. P. Micikevicius et al., "Mixed Precision Training," *ICLR*, 2018. (AMP)
11. T.-Y. Lin et al., "Microsoft COCO: Common Objects in Context," *ECCV*, 2014.
12. M. Everingham et al., "The PASCAL Visual Object Classes (VOC) Challenge," *IJCV*, 2010.

**เรขาคณิตและอัลกอริทึม**

13. R. Hartley, A. Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., Cambridge University Press, 2004. (Homography)
14. H. W. Kuhn, "The Hungarian method for the assignment problem," *Naval Research Logistics Quarterly*, 2(1–2), 83–97, 1955.
15. SciPy, "scipy.optimize.linear_sum_assignment." https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
16. OpenCV, "Geometric Image Transformations." https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html
17. J. L. Pech-Pacheco et al., "Diatom autofocusing in brightfield microscopy: a comparative study," *ICPR*, 2000. (Variance of Laplacian เป็นตัวชี้วัดความคมชัด)

**ระบบและเว็บ**

18. FastAPI documentation. https://fastapi.tiangolo.com/
19. Beanie ODM (MongoDB) documentation. https://beanie-odm.dev/
20. SvelteKit / Svelte 5 documentation. https://svelte.dev/
21. MDN, "MediaDevices.getUserMedia()." https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
22. TanStack Query; openapi-typescript / openapi-fetch; Playwright documentation.

**ข้อมูล**

23. Kaggle, "keyboard-key-detection" (Pascal VOC, German QWERTZ) — ชุดข้อมูลที่ใช้เป็น proxy (ตรวจสอบเงื่อนไขการใช้งานและ license ก่อนเผยแพร่)

> หมายเหตุ: เอกสารอ้างอิงด้านเครื่องมือระบุสิ่งที่เครื่องมือทำ ไม่ได้ยืนยันความแม่นยำบนข้อมูลของงานนี้ ซึ่งต้องอ้างผลจากบทที่ 4 เท่านั้น ควรตรวจรูปแบบการอ้างอิง (ปี หน้า หมายเลข arXiv) ให้ตรงตามรูปแบบของสถาบันก่อนส่ง

## ภาคผนวก ข วัสดุและอุปกรณ์

> **หมายเหตุ:** โครงงานนี้เป็นโครงงานซอฟต์แวร์ ไม่ได้บันทึกราคาอุปกรณ์ไว้ในรีโป ตารางนี้ระบุรายการที่ใช้จริง ส่วนราคาและจำนวนที่ไม่ทราบทำเครื่องหมาย `[กรอก]` เพื่อให้ผู้จัดทำกรอกก่อนส่ง

| ลำดับ | รายการ | จำนวน | ราคาต่อหน่วย (บาท) | รวม (บาท) |
| --- | --- | --- | --- | --- |
| 1. | เครื่องคอมพิวเตอร์โน้ตบุ๊ก (GPU NVIDIA GeForce RTX 4060 Laptop 8 GB) | 1 | [กรอก] | [กรอก] |
| 2. | อุปกรณ์ถ่ายภาพคีย์บอร์ด (กล้องมือถือหรือเว็บแคม) | [กรอก] | [กรอก] | [กรอก] |
| 3. | คีย์บอร์ดสำหรับเก็บข้อมูลจริงในอนาคต (ยืม 8–12 รุ่นตามแผน Tier 2) | [กรอก] | [กรอก] | [กรอก] |
| 4. | ซอฟต์แวร์ทั้งหมด (Python, PyTorch, Ultralytics, FastAPI, SvelteKit ฯลฯ) | — | 0 (โอเพนซอร์ส) | 0 |
| | รวมทั้งหมด | | | [กรอก] |

ตารางที่ 29 แสดง รายการวัสดุและอุปกรณ์ที่ใช้ในโครงงาน

## ภาคผนวก ค การวิเคราะห์ต้นทุน NRE (Non-Recurring Engineering)

การวิเคราะห์ต้นทุนแยกเป็น 2 ส่วน คือ ต้นทุน NRE ซึ่งเป็นค่าใช้จ่ายด้านวิศวกรรมที่จ่ายเพียงครั้งเดียว คำนวณจากจำนวนชั่วโมงคูณอัตราค่าแรง กับต้นทุนต่อหน่วย (unit cost) ซึ่งเป็นต้นทุนวัสดุและค่าให้บริการต่อหนึ่งชุดระบบ

> **หมายเหตุ:** รีโปไม่ได้บันทึกจำนวนชั่วโมงทำงานจริง ตารางต่อไปนี้ระบุรายการงานที่ทำจริงและให้กรอกชั่วโมงและอัตราค่าแรงเอง (ตัวอย่างต้นแบบกำหนดอัตรา 250 บาทต่อชั่วโมง)

### ค.1 รายละเอียดต้นทุน NRE

| ลำดับ | รายการ NRE | งานที่ทำ | ชั่วโมง | อัตรา (บาท/ชม.) | รวม (บาท) |
| --- | --- | --- | --- | --- | --- |
| 1. | ออกแบบระบบและสัญญา API | ออกแบบสถาปัตยกรรม 3 ชั้น ระบบพิกัด u layout และ API contract | [กรอก] | [กรอก] | [กรอก] |
| 2. | ท่อข้อมูลและชุดประเมิน | นำเข้า Kaggle VOC, audit, แบ่งชุด leave-brand-out, สร้างข้อมูล rectified และชุด S1–S4 | [กรอก] | [กรอก] | [กรอก] |
| 3. | อัลกอริทึมแกนกลาง | homography, ตรวจจุด, Hungarian matching, decide, suggest, objective | [กรอก] | [กรอก] | [กรอก] |
| 4. | ฝึกและประเมินโมเดล | ฝึก YOLO11n, Faster R-CNN, ตัวจำแนก, ทดลอง OCR, จูน threshold | [กรอก] | [กรอก] | [กรอก] |
| 5. | Backend | FastAPI, session, อัปโหลด, คิวงาน, worker, retention | [กรอก] | [กรอก] | [กรอก] |
| 6. | Frontend | กล้อง, ตัวแตะจุด, state machine, overlay, ข้อความไทย | [กรอก] | [กรอก] | [กรอก] |
| 7. | ทดสอบและจัดทำเอกสาร | pytest, Playwright, รายงาน | [กรอก] | [กรอก] | [กรอก] |
| 8. | รวม | | [กรอก] | | [กรอก] |

ตารางที่ 30 แสดง รายละเอียดต้นทุน NRE

### ค.2 ต้นทุนต่อชุดระบบ

ต้นทุนต่อชุดคำนวณจาก (ต้นทุน NRE ÷ จำนวนที่ผลิตหรือติดตั้ง) + ต้นทุนต่อหน่วย โดยต้นทุนต่อหน่วยของซอฟต์แวร์ในโครงงานนี้คือค่าเครื่องเซิร์ฟเวอร์ที่ใช้รัน Backend และ Worker (CPU เพียงพอสำหรับ baseline และ YOLO11n)

$$\text{ต้นทุนต่อชุด}=\frac{\text{NRE}}{N}+\text{ต้นทุนต่อหน่วย}$$

[กรอกตัวอย่างการคำนวณเมื่อ N = 1, 5, 10, 50 หลังทราบค่า NRE และต้นทุนต่อหน่วย]

## ภาคผนวก ง ภาพบรรยากาศการทำงาน

> **[ใส่ภาพ]** ภาพบรรยากาศการพัฒนาและการทดสอบระบบ (เช่น การประชุมทีม การทดสอบถ่ายภาพคีย์บอร์ดและแตะจุดบนมือถือ การรัน Notebook)

*รูปภาพที่ 20 ภาพบรรยากาศการพัฒนาระบบ*

> **[ใส่ภาพ]** ภาพการทดสอบการทำงานของระบบเว็บบนมือถือกับคีย์บอร์ดจริง

*รูปภาพที่ 21 ภาพบรรยากาศการทดสอบการทำงานของระบบ*

---

> **หมายเหตุ:** ภาคผนวก จ–ซ เป็นข้อมูลอ้างอิงเสริมของโครงงานนี้ (ตารางไม่ลำดับเลข)

## ภาคผนวก จ ค่าตั้งของการทดลอง (`experiments/configs/qwertz/pipeline.yaml`)

### จ.1 ข้อมูลและการแบ่งชุด

| พารามิเตอร์ | ค่า | ความหมาย |
| --- | --- | --- |
| `dataset_version` | `kaggle_qwertz_v1` | |
| `layout_id` | `qwertz_letters_eval_v1` | layout ของ S1/S3/S4 |
| `swap_layout_id` | `qwerty_stagger_letters_v1` | layout ของ S2 |
| `q1.seed` | 20261001 | เปลี่ยนค่านี้ทำให้ `split_manifest_hash` เปลี่ยน |
| `q1.test_fraction` / `val_fraction` | 0.15 / 0.15 | สัดส่วนของต้นฉบับ `eval` |
| `q1.n_heldout_val_groups` | 2 | กลุ่มยี่ห้อที่อยู่ใน Validation เท่านั้น |
| `q1.heldout_min_eligible` / `max_eligible` | 8 / 40 | ขนาดกลุ่มที่เป็นผู้สมัคร held-out |
| `q2.train_jitter_variants` | 2 | สำเนา jitter ต่อภาพฝึก นอกเหนือจากสำเนาตรง |
| `q2.jitter_sigmas_u` | [0.05, 0.10, 0.20] | σ ของ jitter ในหน่วยระยะปุ่ม (สำเนาที่ 1, 2 ใช้ 0.05, 0.10) |
| `q2.eval_jitter_sigma_u` | 0.10 | σ ของชุดจุด `jit` ของ Val/Test (คงที่) |
| `q2.min_visible` | 0.5 | สัดส่วนที่ต้องมองเห็นของกรอบหลังตัดขอบ canvas |
| `q2.swap_kinds` | adjacent, cross_row, multi_pairs, cycle3 | ชนิดการสลับใน S3 |
| `q2.ppus` | 64, 96, 128 | ความละเอียดที่สร้าง |

### จ.2 Q3 — OCR sweep

| พารามิเตอร์ | ค่า |
| --- | --- |
| `max_items` | 40 ภาพต่อ ppu |
| `max_reject_rate` | 0.10 |
| `device` | cpu |
| `crop_modes` | `key_full`, `key_full_pad0.1`, `key_center_0.7`, `key_center_0.55` |
| ตัวรู้จำ | `rec_server` (PP-OCRv5_server_rec, pad 8), `rec_en_mobile` (en_PP-OCRv5_mobile_rec, pad 0), `rec_latin_mobile` (latin_PP-OCRv5_mobile_rec, pad 8), `auto_server` (PP-OCRv5_server_det + server_rec, pad 8) |

### จ.3 Q3b — ตัวจำแนกปุ่ม

| พารามิเตอร์ | ค่า |
| --- | --- |
| `arch` / `pretrained` | resnet18 / true (ImageNet) |
| `input` | 64 px |
| `other_per_image` | 10 |
| `jitter_sigmas_u` | [0.05, 0.10] (สำเนาตรงเพิ่มอัตโนมัติ) |
| `min_visible` | 0.5 |
| `epochs` / `patience` | 20 / 5 |
| `batch` / `workers` | 256 / 6 |
| `lr` / `weight_decay` | 0.001 / 0.0001 (AdamW) |
| `label_smoothing` | 0.0 |
| `amp` | true |
| `monitor` | `acc_with_thai` |
| augment | scale 0.10, aspect 0.05, shift 0.08, rotate 4°, brightness 0.25, contrast 0.25, gray_p 0.1, blur_p 0.2, thai_p 0.5 |

### จ.4 Q4 — YOLO11n

| พารามิเตอร์ | ค่า |
| --- | --- |
| น้ำหนักเริ่มต้น | `yolo11n.pt` |
| `epochs` / `patience` | 100 / 15 |
| `imgsz` / `batch` / `workers` | 640 / 16 / 4 |
| `rect` / `optimizer` / `cos_lr` | true / auto / false |
| `amp` / `deterministic` | true / true |
| `max_det` | 300 |
| augment ที่เปิด | `hsv_h` 0.015, `hsv_s` 0.4, `hsv_v` 0.3, `degrees` 1.5, `translate` 0.03, `scale` 0.1 |
| augment ที่ปิดบังคับ | fliplr, flipud, mosaic, mixup, cutmix, copy_paste, erasing, shear, perspective, bgr; `close_mosaic=0` |

### จ.5 Q5 — Faster R-CNN ResNet50-FPN V2

| พารามิเตอร์ | ค่า |
| --- | --- |
| โมเดล | COCO_V1 pretrained, หัวทำนาย 2 คลาส |
| `min_size` / `max_size` | 480 / 1152 |
| `box_score_thresh` / `box_nms_thresh` / `box_detections_per_img` | 0.05 / 0.5 / 300 |
| `epochs` / `patience` | 50 / 10 |
| `batch` × `accumulate` | 2 × 4 (effective 8) |
| optimizer | SGD, lr 0.01, momentum 0.9, weight decay 0.0005 |
| `warmup_iters` / `grad_clip` | 100 / 10.0 |
| `amp` / `monitor` / `val_score_thr` | true / `map50_95` / 0.25 |
| augment | brightness 0.25, contrast 0.25, noise_std 0.02, blur_prob 0.2, scale 0.08, translate 0.03, rotate 1.5° |

### จ.6 Q6 — การประเมินและจูน

| พารามิเตอร์ | ค่าเริ่มต้น (`default_params`) | grid |
| --- | --- | --- |
| `det_score_min` | 0.25 | 0.10, 0.25, 0.40, 0.55 |
| `ocr_score_min` | 0.50 | 0.30, 0.50, 0.70, 0.85, 0.90, 0.95, 0.98, 0.99 |
| `gating_u` | 0.50 | 0.40, 0.50, 0.60, 0.70 |
| `unmatched_cost` | 0.60 | 0.50, 0.60, 0.80 |
| `ambiguity_margin_u` | 0.10 | 0.05, 0.10, 0.15 |
| `fit_min_matched_fraction` | null (ใช้ค่าของ layout = 0.7) | 0.60, 0.70, 0.80 |
| `fit_max_mean_residual_u` | null (ใช้ค่าของ layout = 0.3) | 0.15, 0.20, 0.30 |
| `ref_invalid_max` | 2 | null, 1, 2, 3 |
| `mismatch_min_wrong` | 3 | 2, 3, 4 |
| `mismatch_wrong_fraction` | 0.5 | (ไม่จูน) |

พารามิเตอร์ระดับ Q6: `recognizer: keycls`, `evidence_gating_u: 0.75`, `evidence_det_floor: 0.05`, `max_combos: 400`, `max_false_alarm: 0.02`, `max_false_rejection: 0.02`, `w_layout: 0.25`, `min_layout_mismatch: 0.80` จำนวนชุดใน grid เต็ม $4\cdot8\cdot4\cdot3\cdot3\cdot3\cdot3\cdot4\cdot3=124{,}416$ จึงใช้ coordinate descent ส่วน baseline จูนเพียง `ocr_score_min`, `ref_invalid_max`, `mismatch_min_wrong` ($8\cdot4\cdot3=96$ ชุด)

### จ.7 Threshold ที่ commit (`thresholds.yaml`)

| พารามิเตอร์ | baseline | YOLO11n (เลือก) | Faster R-CNN |
| --- | --- | --- | --- |
| `det_score_min` | 0.25 | 0.10 | 0.25 |
| `ocr_score_min` | 0.99 | 0.99 | 0.98 |
| `gating_u` | 0.5 | 0.6 | 0.7 |
| `unmatched_cost` | 0.6 | 0.6 | 0.6 |
| `ambiguity_margin_u` | 0.1 | 0.15 | 0.05 |
| `fit_min_matched_fraction` | null | 0.6 | 0.6 |
| `fit_max_mean_residual_u` | null | 0.3 | 0.3 |
| `ref_invalid_max` | 2 | null | 2 |
| `mismatch_min_wrong` | 2 | 3 | 3 |
| `mismatch_wrong_fraction` | 0.5 | 0.5 | 0.5 |
| `skip_layout_fit` | true | false | false |
| objective | 1.2038 | **1.3110** | 1.2014 |

ค่าอื่นของ bundle: `px_per_unit: 64`, `crop_mode: key_full`, ตัวอ่าน `keycls` (`weights_sha256: e6f4f927eddbfc3d9c5277442b0c891efc22080348943fe47373fe0360414def`)

### จ.8 Backend (ตัวแปรสภาพแวดล้อม)

| ตัวแปร | ค่าเริ่มต้น |
| --- | --- |
| `MONGODB_URI` | ว่าง (โหมด in-memory) |
| `STORAGE_ROOT` | `../var/storage` |
| `MODEL_BUNDLE_DIR` | `../bundles/baseline_dev_v0` |
| `OCR_DEVICE` | `cpu` |
| `MAX_UPLOAD_BYTES` | 15,728,640 (15 MiB) |
| `MAX_IMAGE_PIXELS` | 24,000,000 |
| `QUEUE_CAPACITY` / `MAX_ACTIVE_JOBS_PER_SESSION` | 8 / 2 |
| `IMAGE_RETENTION_HOURS` / `METADATA_RETENTION_HOURS` | 24 / 168 |
| `WORKER_LEASE_SECONDS` / `WORKER_MAX_RETRIES` | 120 / 1 |
| `WORKER_POLL_SECONDS` / `RETENTION_INTERVAL_SECONDS` / `ORPHAN_GRACE_SECONDS` | 1.0 / 300 / 600 |
| `SESSION_SECRET` | ต้องตั้ง |
| `COOKIE_SECURE` / `ALLOWED_ORIGINS` | false / [] |
| `DISALLOW_AGENTS` | `zgrab`, `wget` |


## ภาคผนวก ฉ แผนผังไฟล์และหน้าที่

```
keycheck/
├── ai/                          # แพ็กเกจ keycheck-ai (แกนของระบบ)
│   ├── preprocessing/           # geometry.py (homography, IoU, validate), quality.py (blur/exposure)
│   ├── layouts.py               # โหลด layout JSON → Layout
│   ├── detection/               # detectors.py (YOLO, Faster R-CNN), fixed_layout.py (baseline)
│   ├── recognition/ocr.py       # PaddleReader, normalize_label, crop_box_px
│   ├── classification/          # keycls.py (ResNet18 27 คลาส), thai_legend.py (อักษรไทยสังเคราะห์)
│   ├── matching/                # assign.py (Hungarian), decision.py (Evidence, Params, decide, suggest)
│   ├── pipeline/                # stage.py (stage cache), stages.py (Q1–Q7), evidence.py, show.py
│   ├── data/                    # kaggle_voc, audit, split, q1_ingest, rectify_dataset, synthetic_swap
│   │   └── keyboard_dataset/    # เครื่องมือชุดข้อมูลที่ถ่ายเอง (schema, validate, split, convert, CLI)
│   ├── training/                # train_yolo, train_frcnn, train_keycls
│   ├── evaluation/              # detection_metrics, metrics, pipeline_eval, ocr_eval, q6_eval, pilot
│   ├── inference/               # inspector.py, demo.py, images.py
│   ├── bundle.py                # build_bundle
│   └── colab/bootstrap.py       # ตั้งค่า/ล้างหน่วยความจำ (Colab/Local)
├── backend/apiapp/              # FastAPI: core, middlewares, infrastructure, modules, worker
├── frontend/src/                # SvelteKit: routes, lib/features/inspection, components/ui
├── layouts/                     # qwerty_stagger_letters_v1.json, eval/qwertz_letters_eval_v1.json
├── bundles/                     # baseline_dev_v0/, keycheck_qwertz_dev_v1/ (bundle.json; weights ไม่อยู่ใน git)
├── experiments/configs/qwertz/  # pipeline.yaml, thresholds.yaml
├── data/manifests/kaggle_qwertz_v1/  # split_manifest.json, frozen_hashes.json
├── notebooks/                   # keycheck_qwertz_pipeline.ipynb (Notebook หลัก), 00_env_check.ipynb
├── tests/ai/                    # pytest ของ ai/
├── docs/                        # spec, plans, api-contract, guides, report/
└── outputs/                     # ผลรัน (ไม่ขึ้น git ยกเว้น smoke บางส่วน)
```

### ตารางโมดูลหลัก

| ไฟล์ | หน้าที่ | จุดเด่นเชิงเทคนิค |
| --- | --- | --- |
| `ai/preprocessing/geometry.py` | homography, canvas, IoU, ตรวจจุด | cross product / shoelace / signed area |
| `ai/preprocessing/quality.py` | คุณภาพภาพ | Var(Laplacian) ปรับตาม ppu |
| `ai/matching/assign.py` | จับคู่ one-to-one | Hungarian + dummy + gating + ambiguity |
| `ai/matching/decision.py` | `decide`, `suggest` | การตัดสินหลายชั้น, swap/cycle |
| `ai/classification/keycls.py` | ตัวจำแนก 27 คลาส | ResNet18 transfer learning |
| `ai/classification/thai_legend.py` | อักษรไทยสังเคราะห์ | Kedmanee + Noto Thai |
| `ai/pipeline/stage.py` | stage cache | fingerprint (config+upstream+code) |
| `ai/evaluation/pipeline_eval.py` | ประเมินและจูน | objective, grid/coordinate descent |
| `ai/inference/inspector.py` | จุดเรียกเดียวของ Backend | โหลดครั้งเดียว, OCR เฉพาะกรอบที่จับคู่ |
| `backend/apiapp/worker/runner.py` | คิว/lease/heartbeat | atomic claim, requeue, drop ผลเมื่อ lease หาย |
| `backend/apiapp/core/session.py` | session/ownership | HMAC ของ token, ตรวจ Origin |
| `frontend/.../machine.ts` | state machine | pure function 10 สถานะ |
| `frontend/.../geometry.ts` | geometry ฝั่ง UI | validateQuad, homography (Gaussian elimination) |


## ภาคผนวก ช API และความปลอดภัย

### ช.0 รายการ API และมาตรการด้านความปลอดภัย

API ทั้งหมดอยู่ภายใต้ `/api/v1` ดังตารางที่ 31 และมาตรการด้านความปลอดภัยสรุปไว้ในตารางที่ 32

| Method | Path | ผลสำเร็จ | หมายเหตุ |
| --- | --- | --- | --- |
| GET | `/health` | 200 | สถานะของ API ฐานข้อมูล และโมเดล |
| GET | `/layouts` | 200 | ผังปุ่มที่รองรับ |
| POST | `/uploads` | 201 | อัปโหลดภาพ |
| GET / DELETE | `/uploads/{id}[/image]` | 200 / 204 | เรียกดูหรือลบภาพ (เฉพาะเจ้าของ) |
| POST | `/inspections` | **202** | ส่งงานตรวจเข้าคิว |
| GET / DELETE | `/inspections/{id}` | 200 / 204 | เรียกดูสถานะและผล หรือลบ |
| GET | `/inspections` | 200 | ประวัติการตรวจ |

ตารางที่ 31 แสดง API endpoint ของระบบ (prefix `/api/v1`)

| ภัยคุกคาม | มาตรการป้องกัน |
| --- | --- |
| การเข้าถึงข้อมูลของผู้อื่น | จัดเก็บรหัสในรูปแบบเข้ารหัส ตรวจสอบความเป็นเจ้าของทุกครั้ง และตอบกลับเสมือนไม่มีข้อมูลดังกล่าว |
| การปลอมแปลงคำขอข้ามเว็บไซต์ (CSRF) | ตรวจสอบว่าคำขอมาจากหน้าเว็บของระบบ |
| ไฟล์อัปโหลดที่เป็นอันตราย | ตรวจสอบเนื้อหาไฟล์ เปิดภาพเพื่อยืนยัน จำกัดขนาด และลบข้อมูลแฝง |
| การส่งงานจำนวนมากจนระบบทำงานเกินกำลัง | จำกัดจำนวนงานต่อผู้ใช้งานและทั้งระบบ |
| ไฟล์โมเดลที่เป็นอันตราย | ไม่รับไฟล์โมเดลจากผู้ใช้งาน ใช้เฉพาะโมเดลที่สร้างขึ้นเอง |
| การรั่วไหลของข้อมูลส่วนบุคคล | ไม่บันทึกภาพหรือรหัสลงในไฟล์บันทึกการทำงาน และลบภาพโดยอัตโนมัติ |

ตารางที่ 32 แสดง ภัยคุกคามและมาตรการด้านความปลอดภัย


### ช.1 ลำดับการเรียก

```text
POST /api/v1/uploads                 (multipart: image)         → 201 {image_id, width, height, ...}
POST /api/v1/inspections             {image_id, layout_id,      → 202 {inspection_id, status:"queued", status_url}
                                      reference_points_normalized, client_request_id}
GET  /api/v1/inspections/{id}        (poll)                     → 200 {status:"processing", stage:"reading"}
GET  /api/v1/inspections/{id}        (poll)                     → 200 {status:"completed", summary, slots[26], suggestions}
```

### ช.2 Request สร้างงานตรวจ

```json
{
  "image_id": "img_...",
  "layout_id": "qwerty_stagger_letters_v1",
  "reference_points_normalized": [[0.21, 0.34], [0.78, 0.33], [0.66, 0.66], [0.27, 0.67]],
  "client_request_id": "b3f1…"
}
```

ลำดับจุด: TL (Q), TR (P), BR (M), BL (Z)

### ช.3 Response เมื่อเสร็จ (ย่อ)

```json
{
  "inspection_id": "ins_...",
  "status": "completed",
  "model_bundle_id": "keycheck_qwertz_dev_v1",
  "coordinate_system": "original_oriented_normalized",
  "summary": { "total_slots": 26, "correct": 24, "incorrect": 2, "uncertain": 0 },
  "slots": [
    { "slot_id": "r1c0", "row": 1, "col": 0, "expected_label": "A", "observed_label": "S",
      "candidate_label": null, "status": "incorrect", "reason": "label_mismatch",
      "reason_codes": ["label_mismatch"], "detector_score": 0.91, "ocr_score": 0.998,
      "assignment_distance": 0.07,
      "polygon": [[0.31, 0.52], [0.36, 0.52], [0.36, 0.58], [0.31, 0.58]],
      "polygon_source": "detection", "is_reference": false }
  ],
  "suggestions": [ { "type": "swap_pair", "slots": ["r1c0", "r1c1"] } ],
  "warnings": ["proxy_model"],
  "timings_ms": { "rectify": 12, "detect": 3, "read": 80, "match": 2, "total": 100 }
}
```

(ตัวเลขในตัวอย่างเป็นภาพประกอบรูปแบบข้อมูล ไม่ใช่ผลจากการรันจริง)

### ช.4 Response เมื่อถูกปฏิเสธ

```json
{ "status": "rejected",
  "error": { "code": "LAYOUT_MISMATCH", "message": "…ให้แตะจุด Q, P, M, Z ใหม่", "retryable": true } }
```

### ช.5 รหัสข้อผิดพลาด

`UNSUPPORTED_IMAGE` (415), `IMAGE_TOO_LARGE` (413), `IMAGE_DECODE_FAILED` (422), `INVALID_CORNERS` (422), `LAYOUT_NOT_FOUND` (422), `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `IMAGE_EXPIRED` (410), `IMAGE_IN_USE` / `INSPECTION_IN_PROGRESS` (409), `QUEUE_FULL` (429), `ORIGIN_FORBIDDEN` (403), `MODEL_UNAVAILABLE` (503), `LAYOUT_MISMATCH` (ใน `error` ของงาน), `PROCESSING_FAILED` (ใน `error` ของงาน), `INTERNAL_ERROR` (500)

### ช.6 รูปแบบ `bundle.json` (ย่อ)

```json
{
  "bundle_id": "keycheck_qwertz_dev_v1",
  "detector": "yolo", "weights_file": "weights_yolo.pt", "detector_config": { "imgsz": 640 },
  "px_per_unit": 64, "crop_mode": "key_full",
  "ocr": { "id": "keycls", "mode": "keycls", "weights": "recognizer_keycls.pt", "weights_sha256": "e6f4f927…" },
  "thresholds": { "det_score_min": 0.1, "ocr_score_min": 0.99, "gating_u": 0.6, "…": "…" },
  "layouts": ["qwertz_letters_eval_v1", "qwerty_stagger_letters_v1"],
  "proxy": "Kaggle QWERTZ (dev bundle, not a production model)",
  "split_manifest_hash": "4fd3990958a69265afeac12c9b021e1f3879761732085b1f43c54450f41b8e99"
}
```


## ภาคผนวก ซ อภิธานศัพท์

| คำ | ความหมาย |
| --- | --- |
| **Keycap (คีย์แคป)** | ฝาครอบปุ่มบนคีย์บอร์ดที่มีตัวอักษรพิมพ์อยู่ |
| **QWERTY / QWERTZ** | ผังตัวอักษรของคีย์บอร์ด QWERTZ (เยอรมัน) สลับตำแหน่ง Y กับ Z |
| **ANSI / ISO** | มาตรฐานรูปทรงคีย์บอร์ด (ปุ่ม Enter, Shift ซ้ายต่างกัน) |
| **u (key unit)** | หน่วยความยาวเท่าระยะปุ่มมาตรฐาน 1 ปุ่ม |
| **Row-staggered** | แถวปุ่มเยื้องกันเป็นสัดส่วนคงที่ |
| **Homography** | การแปลงเชิงฉายภาพ (perspective) 3×3 ระหว่างสองระนาบ ใช้ปรับภาพเอียงให้ตรง |
| **Rectify** | ปรับภาพให้เป็นมุมมองตรงจากด้านบนด้วย homography |
| **Canvas** | ภาพผลลัพธ์หลัง rectify ครอบพื้นที่ [−1.5, 10.5]×[−1.5, 3.5] u |
| **`px_per_unit` (ppu)** | จำนวนพิกเซลต่อ 1u ของ canvas |
| **Reference points** | 4 จุดที่ผู้ใช้แตะ: Q, P, M, Z |
| **Generic letter-block** | ผังตัวอักษร 3 แถวร่วมของ QWERTY ทุกรุ่น |
| **Slot** | ช่องตำแหน่งหนึ่งช่อง (26 ช่อง) ระบุด้วย `r<row>c<col>` |
| **Detector** | โมเดลตรวจจับวัตถุ ให้กรอบและคะแนน |
| **IoU** | Intersection over Union: $|A\cap B|/|A\cup B|$ วัดความซ้อนทับของกรอบ |
| **NMS** | Non-Maximum Suppression: ตัดกรอบซ้ำซ้อน เหลือกรอบคะแนนสูงสุด |
| **AP / mAP** | Average Precision (พื้นที่ใต้เส้น precision-recall) / ค่าเฉลี่ยของ AP; mAP50 ที่ IoU 0.5, mAP50-95 เฉลี่ย IoU 0.50–0.95 |
| **One-stage / Two-stage** | detector ที่ทำนายกรอบในรอบเดียว / ที่เสนอกรอบผู้สมัครแล้วปรับค่าอีกขั้น |
| **FPN** | Feature Pyramid Network: ผสมคุณลักษณะหลายสเกล |
| **Anchor-free** | ไม่ใช้กรอบอ้างอิง (anchor) ที่กำหนดล่วงหน้า |
| **Transfer learning / Fine-tune** | นำโมเดลที่ฝึกมาแล้วบนงานใหญ่ไปปรับกับงานของเรา |
| **OCR** | Optical Character Recognition: อ่านข้อความจากภาพ |
| **Closed-set classification** | จำแนกในกลุ่มคำตอบที่กำหนดไว้ (ที่นี่ 27 คลาส) |
| **Softmax / confidence** | การแปลงคะแนนเป็นความน่าจะเป็นรวม 1 / คะแนนสูงสุดที่ใช้เป็นความมั่นใจ |
| **Label smoothing** | เทคนิคลดความมั่นใจเกินจริงของ label (ในงานนี้ไม่ใช้) |
| **AMP** | Automatic Mixed Precision: คำนวณแบบ 16-bit บางส่วนเพื่อความเร็ว/หน่วยความจำ |
| **Gradient accumulation** | สะสม gradient หลาย mini-batch ก่อนอัปเดต เพื่อจำลอง batch ใหญ่ |
| **Early stopping** | หยุดฝึกเมื่อผล Validation ไม่ดีขึ้นต่อเนื่อง |
| **Hungarian algorithm** | อัลกอริทึมแก้ assignment problem หาการจับคู่ one-to-one ต้นทุนรวมต่ำสุด |
| **Gating** | ตัดคู่ที่ไกลเกินเกณฑ์ออกจากการจับคู่ |
| **Dummy (ใน assignment)** | แถว/คอลัมน์สมมติที่ให้ "ไม่จับคู่" เป็นตัวเลือกที่มีต้นทุน |
| **Ambiguity margin** | ส่วนต่างระยะที่ถือว่าจับคู่ไม่ชัดเจน |
| **Evidence** | ผลดิบของ detector + ตัวอ่าน ก่อนใช้ threshold |
| **Layout fit** | การตรวจว่าปุ่มที่พบเรียงตรงกับกริดของ layout |
| **Proxy dataset** | ข้อมูลตัวแทนที่ใช้แทนข้อมูลจริงที่ยังไม่มี |
| **Leave-brand-out** | แบ่งชุดโดยกันยี่ห้อทั้งกลุ่มออกจากการฝึก |
| **Data leakage** | ข้อมูลที่ควรแยกกันรั่วข้าม split ทำให้ผลสูงเกินจริง |
| **Optimism bias** | ผลที่วัดบนข้อมูลที่ใช้จูนสูงกว่าผลบนข้อมูลใหม่ |
| **False-alarm image rate** | สัดส่วนภาพถูกต้องที่ระบบแจ้งว่ามีปุ่มผิด |
| **Coverage** | สัดส่วนช่องที่ระบบตอบ (ถูกหรือผิด) ไม่ใช่ไม่แน่ใจ |
| **Lease / Heartbeat** | การจองงานชั่วคราวของ worker / สัญญาณต่ออายุว่ายังทำงานอยู่ |
| **Idempotency key** | คีย์ที่ทำให้ส่งคำขอซ้ำแล้วได้ผลเดิม (`client_request_id`) |
| **HMAC** | รหัสยืนยันข้อความด้วยคีย์ลับ ใช้เก็บ hash ของ session token |
| **EXIF** | metadata ของภาพถ่าย (ทิศทาง, GPS ฯลฯ) |
| **SPA** | Single-Page Application |

