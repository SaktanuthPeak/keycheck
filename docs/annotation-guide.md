# KeyCheck — Annotation Guide

**อ้างอิง:** [`keycheck-technical-specification.md`](./keycheck-technical-specification.md) v1.1 §5.1–§5.5, §6.2, §7.2, §7.8, §9.2, §19 · [`implementation-plan.md`](./implementation-plan.md) P2.A–P2.D, D6, D7, D10 · [`dataset-format.md`](./dataset-format.md) · [`capture-guide.md`](./capture-guide.md) · [`api-contract.md`](./api-contract.md) · Dataset tooling: `ai/data/keyboard_dataset/` (`schema.py`, `arrangement.py`, `split.py`, `validate.py`)
**เวอร์ชัน:** 0.2 (ฉบับร่าง P2.A) — 5 ตุลาคม 2026
**สถานะ:** ร่างก่อน Pilot pipeline 50–80 ภาพ — ทุกข้อที่ระบุว่า "ยืนยันใน Pilot" ต้องตัดสินก่อน Annotate ชุดหลัก แล้วออกฉบับสุดท้ายใน P9.A

> เอกสารนี้กำหนด **ว่าจะ Label อะไรและอย่างไร** ส่วนรูปแบบไฟล์ คำสั่ง (`init`, `schedule`, `prefill-slots`, `manifest`, `split`, `validate`, `to-yolo`) และ Converter อยู่ใน [`dataset-format.md`](./dataset-format.md) ชื่อไฟล์ ชื่อคอลัมน์ และค่า Enum ทุกตัวในเอกสารนี้คัดลอกมาจาก `ai/data/keyboard_dataset/schema.py` ซึ่ง Validator ใช้จริง ถ้าเอกสารใดขัดกับ `schema.py` ให้ถือ `schema.py` เป็นหลัก แล้วแจ้งแก้เอกสารก่อน Annotate ต่อ

---

## 0. สิ่งที่ต้อง Label ต่อหนึ่งภาพ (สรุป)

| # | สิ่งที่ Label | ไฟล์ | ที่มา | Spec |
| ---: | --- | --- | --- | --- |
| 1 | Metadata ภาพ (`image_id`, `keyboard_id`, `capture_session_id`, `arrangement_id`, …) | `metadata/images.csv` | Capture log | §5.4 |
| 2 | จุดอ้างอิงสี่จุด TL/TR/BR/BL + ขนาดภาพหลังแก้ EXIF | คอลัมน์ `ref_*`, `width`, `height` ใน `metadata/images.csv` | Annotator (CVAT → §6.3) | §5.4, §7.2 |
| 3 | กรอบ **ทุกคีย์แคปที่มองเห็น** คลาส `keycap` + Flags | `annotations/keycaps_coco.json` | Assist model → Annotator | §5.4 |
| 4 | ตาราง GT รายช่อง 26 แถว (`actual_label`, `readable`, `ground_truth_status`) | `metadata/slots.csv` | Arrangement schedule → Annotator ยืนยัน | §5.4, §9.2 |

Metadata ระดับคีย์บอร์ดอยู่ใน [`data/keyboards.csv`](../data/keyboards.csv) ไฟล์เดียว บันทึกครั้งเดียวต่อคีย์บอร์ด ไม่ทำซ้ำต่อภาพ (Spec §5.2; รายละเอียดใน §5.2 ด้านล่าง)

### 0.1 โครงสร้าง Dataset root (สรุปจาก [`dataset-format.md`](./dataset-format.md) §1)

```text
<dataset_root>/                      # สร้างด้วย: python -m ai.data.keyboard_dataset init <dataset_root>
  images/                            # ภาพที่ Normalize EXIF แล้ว (§1); file_name ใน images.csv นับจากโฟลเดอร์นี้
  metadata/images.csv                # หนึ่งแถวต่อภาพ (§5.1)
  metadata/keyboards.csv             # Symlink ไปที่ data/keyboards.csv ห้ามแก้ที่นี่ (§5.2)
  metadata/slots.csv                 # 26 แถวต่อภาพ (§4)
  metadata/arrangements.csv          # Arrangement schedule ที่ Generate (§5.3)
  annotations/keycaps_coco.json      # กรอบ keycap (§3, §6.3)
  manifests/                         # manifest.json, split_manifest.json (P2.D)
```

- วาง Dataset root ไว้ใต้ `data/` เช่น `data/keyboard_qwerty_v1/` ภาพจะไม่ถูก Commit เพราะ `.gitignore` มี `data/*` เมื่อล็อก Split แล้ว ให้คัดลอก `manifests/*`, `metadata/keyboards.csv`, `metadata/arrangements.csv` ไป `data/manifests/<dataset_version>/` แล้ว Commit ([`dataset-format.md`](./dataset-format.md) §13)
- คำสั่ง `init` สร้าง `metadata/keyboards.csv` เปล่ามาให้ ให้แทนด้วย Symlink ทันที: `ln -sfn ../../keyboards.csv data/keyboard_qwerty_v1/metadata/keyboards.csv` (Path สัมพัทธ์จาก `metadata/`) — `role` จึงมีแหล่งเดียวคือ `data/keyboards.csv` (D10)
- **Pilot pipeline ใช้ Dataset root และ Schedule แยกจากชุดหลัก** เพราะ Schedule ทุกชุดออก ID `arr_0001…` เหมือนกัน ถ้าปนกัน Validator จะเทียบภาพกับ Arrangement ผิดชุด

---

## 1. ระบบพิกัด: Annotate บนภาพ `original_oriented` (D6)

**ข้อตกลง:** กรอบและจุดอ้างอิงทั้งหมดอยู่บนภาพ `original_oriented` (ภาพหลังแก้ EXIF orientation) ไม่ Annotate บนภาพ Rectified (Plan P2.A, D6)

เหตุผล:

- Annotation ไม่ผูกกับ `px_per_unit` / Canvas version — เปลี่ยนความละเอียด Canonical canvas ได้โดยไม่ต้อง Label ใหม่
- ชุด Rectified สำหรับฝึก Detector สร้างด้วยสคริปต์ (`to-yolo`: H จากจุดอ้างอิง → แปลงมุมกรอบทั้งสี่ → กรอบแกนตรง) และ Jitter จุดอ้างอิงเพื่อจำลองความคลาดเคลื่อนตอนผู้ใช้แตะ
- ตรงกับสิ่งที่ Worker เห็นจริง: ภาพหลัง EXIF transpose + จุดที่ผู้ใช้แตะ (§7.2, §10.4)

**ขั้นตอนบังคับก่อนอัปโหลดเข้าเครื่องมือ** (เข้มกว่า [`dataset-format.md`](./dataset-format.md) §1 ที่อนุญาตให้เก็บ EXIF เดิมไว้; ภาพที่ Normalize แล้วก็ผ่าน Validator เหมือนกัน): Normalize ภาพด้วย `PIL.ImageOps.exif_transpose` แล้วบันทึกโดย **ไม่มี Orientation tag** (และลบ GPS) เพราะเครื่องมือ Annotation, OpenCV และ Browser อาจตีความ EXIF orientation ต่างกัน ถ้าไม่ Normalize ก่อน พิกัดจะผิดทั้งภาพโดยไม่มีใครเห็น (Unit test §16.1 "ภาพ EXIF หมุน") บันทึก `width`, `height` หลัง Normalize ลง `metadata/images.csv` ส่วน SHA-256 สร้างด้วยคำสั่ง `manifest` (Plan P2.D)

---

## 2. จุดอ้างอิงสี่จุด

| ลำดับ | ชื่อ Label (CVAT) | คอลัมน์ใน `images.csv` | ตำแหน่ง | พิกัด u |
| ---: | --- | --- | --- | --- |
| 1 | `ref_TL` | `ref_tl_x`, `ref_tl_y` | กึ่งกลางหน้าปุ่มของช่องซ้ายสุด แถวบน (ช่อง Q ตามตำแหน่ง) | (0, 0) |
| 2 | `ref_TR` | `ref_tr_x`, `ref_tr_y` | กึ่งกลางช่องขวาสุด แถวบน (ช่อง P) | (9, 0) |
| 3 | `ref_BR` | `ref_br_x`, `ref_br_y` | กึ่งกลางช่องขวาสุด แถวล่าง (ช่อง M) | (6.75, 2) |
| 4 | `ref_BL` | `ref_bl_x`, `ref_bl_y` | กึ่งกลางช่องซ้ายสุด แถวล่าง (ช่อง Z) | (0.75, 2) |

- หน่วยเป็น Pixel บนภาพ `original_oriented`
- วางตาม **ตำแหน่งช่อง** ไม่ใช่ตามตัวอักษรที่เห็น ถ้าภาพนั้นสลับ Q กับ W ไว้ `ref_TL` ยังอยู่ที่ช่องซ้ายสุด (§7.2)
- วางที่ **กึ่งกลางหน้าบนของปุ่ม** (ไม่ใช่กึ่งกลางกรอบที่รวม Skirt ด้านข้าง) ให้ใกล้กับที่ผู้ใช้จะแตะจริง
- ช่องอ้างอิงถูกบังบางส่วนแต่ยังประมาณกึ่งกลางได้ → วางจุด แล้วติดภาพเป็น Robustness `occlusion`
- กึ่งกลางช่องอ้างอิงตกขอบภาพหรือมองไม่เห็นเลย → ไม่วางจุดเดา และไม่ใส่ภาพนั้นใน Dataset เพราะ Validator ต้องการจุดครบสี่จุดในภาพ (`missing_ref_points`) ([`capture-guide.md`](./capture-guide.md) B.5)
- Validator (`validate_reference_points`) จับได้เฉพาะจุดไขว้กัน อยู่นอกภาพ หรือพื้นที่เล็กเกิน **ถ้าวางครบสี่จุดแต่เริ่มผิดมุมหรือวนกลับทิศ** (เช่น `ref_TL` อยู่ที่ช่อง P) Validator ของ Dataset ไม่เตือน ต้องเปิดภาพ Rectified จากคำสั่ง `to-yolo` ดูด้วยตา: บล็อกตัวอักษรต้องตั้งตรง และช่อง Q ต้องอยู่มุมซ้ายบน
- การตรวจอัตโนมัติว่ากึ่งกลางกรอบหลัง Rectify อยู่ใกล้ Generic layout (เกณฑ์ `fit_thresholds.gating_u` ของ Layout, Plan P1.A) **ยังไม่มีใน Validator** ระหว่างนี้ใช้การดูด้วยตาข้างบน

---

## 3. กรอบคีย์แคป (Detector GT)

### 3.1 กฎหลัก

- คลาสเดียว: **`keycap`** (§5.4, §8.1) ใน COCO ต้องเป็น `category_id = 1` และห้ามมีคลาสอื่น (Validator: `bad_categories`) ขั้นตอน §6.3 ตัด Label `ref_*` ออกให้
- กรอบ **ทุกคีย์แคปที่มองเห็น** ไม่ใช่แค่ A–Z: ตัวเลข, F-keys, Modifier, Space, ปุ่มลูกศร, Numpad ปุ่มที่ไม่ได้กรอบจะกลายเป็น Background และสอน Detector ผิด (§5.4)
- กรอบสี่เหลี่ยม **แกนตรงบนภาพ `original_oriented`** ครอบ **ขอบนอกของคีย์แคปที่มองเห็น** (หน้าปุ่ม + ผนังข้างที่เห็นจากมุมกล้อง) ชิดขอบ ไม่เผื่อช่องว่าง — *ยืนยันใน Pilot* ว่าจะใช้ "ขอบนอก" หรือ "เฉพาะหน้าปุ่ม" แล้วใช้แบบเดียวตลอด Dataset
- ไม่กรอบ: Switch ที่ไม่มีปุ่ม, Knob/Encoder, LED, โลโก้, ปุ่มบนคีย์บอร์ดอื่นที่หลุดเข้ามาในภาพ (ให้หลีกเลี่ยงตอนถ่าย) ถ้ามีคีย์บอร์ดที่สองในภาพ ให้เขียน `multiple_keyboards` ใน `note` ของภาพแล้วส่งตรวจ
- ปุ่มยาว (Space, Shift, Enter แบบ ISO รูปตัว L): กรอบเดียวครอบทั้งปุ่ม

### 3.2 Flags ต่อกรอบ

| Attribute | ค่า | ความหมาย |
| --- | --- | --- |
| `truncated` | `true`/`false` | ปุ่มถูกขอบภาพตัด — กรอบเฉพาะส่วนที่เห็น |
| `occluded` | `true`/`false` | ถูกวัตถุบัง (นิ้ว, สาย, แสงสะท้อนจ้าจนไม่เห็นขอบ) — กรอบตามขอบที่ประมาณได้ของปุ่ม |

CVAT ส่งออกทั้งสองค่าไว้ใน `attributes` ของ Annotation ใน COCO

### 3.3 นโยบายปุ่มโดนตัดขอบหรือถูกบัง (Plan P2.A)

| กรณี | การ Label |
| --- | --- |
| เห็น ≥ ~50% ของปุ่ม | กรอบส่วนที่เห็น + `truncated`/`occluded = true` |
| เห็น < ~50% แต่ยังรู้ว่าเป็นคีย์แคป | **ยังต้องกรอบ** + Flag (ไม่ปล่อยเป็น Background ตาม §5.4) — *เกณฑ์ว่าจะใช้ฝึกหรือไม่ ยืนยันใน Pilot* (Converter ปัจจุบันใช้ทุกกรอบ `keycap`) |
| เห็นน้อยจนบอกไม่ได้ว่าเป็นปุ่ม (เศษขอบไม่กี่ Pixel) | ไม่กรอบ |
| ปุ่มใน **26 ช่อง A–Z** ถูกตัดหรือบัง | ภาพนั้นไม่เข้าเงื่อนไขชุดมาตรฐาน → ย้ายเป็นชุด Robustness (`partial` / `occlusion`) ([`capture-guide.md`](./capture-guide.md) B.5) |

---

## 4. ตาราง Ground Truth รายช่อง — `metadata/slots.csv` (26 แถวต่อภาพ)

| Column | ค่า | หมายเหตุ |
| --- | --- | --- |
| `image_id` | ID ภาพ | ตรงกับ `images.csv` |
| `slot_id` | `r<row>c<col>` เช่น `r0c0` = ช่อง Q | ตาม [`api-contract.md`](./api-contract.md) และ `layouts/qwerty_stagger_letters_v1.json` (ตำแหน่ง ไม่ใช่ตัวอักษร) |
| `expected_label` | A–Z ตาม Layout | เติมโดย `prefill-slots` ห้ามแก้มือ (Validator: `expected_label_mismatch`) |
| `actual_label` | A–Z ตัวพิมพ์ใหญ่ หรือว่าง | ตัวอักษร **อังกฤษ** บนปุ่มที่อยู่ในช่องนั้นจริง |
| `readable` | `1` / `0` | คนอ่านตัวอักษรอังกฤษ **จากภาพนี้** ได้ชัดเจนหรือไม่ (ซูมได้) |
| `ground_truth_status` | `verified` / `pending_review` / `disputed` | ดู 4.2 |
| `note` | ข้อความ | หมายเหตุผู้ตรวจ |

### 4.1 กฎ `actual_label` และ `readable`

- ใช้ตัวอักษร **อังกฤษ A–Z ตัวพิมพ์ใหญ่เท่านั้น** แม้ปุ่มจะมีอักษรไทยร่วม (`th_en`) ห้ามใส่อักษรไทย สัญลักษณ์ หรือหลายตัว (§3.1, §6.2; Validator: `bad_actual_label`)
- ค่ามาจาก **การจัดวางจริง** (Arrangement schedule + Capture log) ไม่ใช่จากผล OCR
- มองไม่ชัด → `readable = 0` แต่ `actual_label` ยังเป็นตัวที่อยู่จริงตาม Log ส่วน `readable = 1` ต้องมี `actual_label` เสมอ (Validator: `missing_actual_label`)
- ช่องที่ `readable = 0` ไม่ถูกนับในชุดมาตรฐาน (§9.2) ภาพที่มีช่องแบบนี้ต้องติด `subset = robustness` (§5.1)
- ปุ่มที่ไม่ใช่ A–Z ถูกวางในช่อง (เช่น ปุ่ม `;`) หรือช่องว่างไม่มีปุ่ม → อยู่นอกขอบเขต (§3.3) ปล่อย `actual_label` ว่าง, `readable = 0` + `note` แล้วภาพนั้นอยู่ชุด Robustness เท่านั้น
- ห้ามแปลง `0`→`O` / `1`→`I` หรือเติมตามตัวที่ Layout คาดหวัง (§6.2)

### 4.2 `ground_truth_status`

ค่านี้บอก **สถานะการตรวจ** ของ `actual_label` เท่านั้น ส่วนการอ่านออกบันทึกแยกใน `readable`

| ค่า | ใช้เมื่อ | ใช้ใน Train/Val/Test |
| --- | --- | --- |
| `pending_review` | ค่าที่ `prefill-slots` เติมจาก Schedule แต่ยังไม่มีคนตรวจ (ค่าตั้งต้น) | **ไม่ได้** — Validator เตือน `gt_not_verified` ต้องไม่เหลือก่อนล็อก Split |
| `verified` | คนตรวจแล้ว: ถ้า `readable = 1` ตัวอักษรในภาพตรงกับ Schedule/Log; ถ้า `readable = 0` Log ระบุชัดและไม่ขัดกับภาพอื่นใน Arrangement เดียวกัน | ได้ (ช่อง `readable = 0` ใช้ในรายงาน Robustness เท่านั้น §9.2) |
| `disputed` | Log กับภาพไม่ตรงกัน หรือผู้ตรวจสองคนเห็นต่าง | ไม่ได้ จนกว่าจะแก้เป็น `verified` |

ภาพเข้าชุดมาตรฐาน (`subset = main`) ได้เมื่อทั้ง 26 ช่องเป็น `verified` และ `readable = 1`

---

## 5. Metadata

### 5.1 ระดับภาพ — `metadata/images.csv` (§5.4, Plan P2.C)

ลำดับคอลัมน์ตาม `IMAGE_COLS` ใน `schema.py` คอลัมน์ที่ไม่อยู่ในรายการนี้จะได้คำเตือน `unknown_column`

| Column | ค่า / ตัวอย่าง |
| --- | --- |
| `image_id` | ID ถาวร ไม่ขึ้นกับชื่อไฟล์กล้อง (บังคับ) |
| `file_name` | Path ของภาพนับจาก `images/` เช่น `kb01/kb01_20261010_01_0001.jpg` — ชื่อไฟล์ (basename) ต้องไม่ซ้ำกันทั้ง Dataset (§6.3) (บังคับ) |
| `keyboard_id` | ตรงกับ `data/keyboards.csv` |
| `capture_session_id` | `<keyboard_id>_<YYYYMMDD>_<nn>` ([`capture-guide.md`](./capture-guide.md) B.3) |
| `arrangement_id` | **คัดลอกจาก `metadata/arrangements.csv`** เช่น `arr_0042` (§5.3) — ห้ามตั้งชื่อเอง; ภาพจาก Arrangement เดียวกันในรอบเดียวกันอยู่ Split เดียวกัน (§5.5) |
| `device` | รุ่นมือถือหรือกล้อง |
| `lighting` | `daylight` / `indoor_warm` / `indoor_cool` / `mixed` / `low` / `flash` / `other` |
| `split` | `train` / `val` / `test` / `excluded` — เติมโดย `split --write-csv` (P2.D) **ห้ามแก้มือ** |
| `source` | ดูตารางถัดไป (บังคับ) |
| `source_url`, `license` | `license` เช่น `own`; ภาพ `public_dataset` / `web_cc` ต้องมีทั้งสองค่า (§5.1) |
| `width`, `height` | หลัง EXIF normalize |
| `ref_tl_x` … `ref_bl_y` | จุดอ้างอิงแปดค่า (§2) — บังคับสำหรับภาพของเราเอง (Validator: `missing_ref_points`) |
| `subset` | `main` (ชุดมาตรฐาน) / `robustness` |
| `note` | หมายเหตุ; ภาพ Robustness ให้ขึ้นต้นด้วย `robustness=<ชนิด>` เช่น `robustness=glare` (ชนิดตาม [`capture-guide.md`](./capture-guide.md) B.5) |

| `source` | ใช้เมื่อ | Split |
| --- | --- | --- |
| `own_capture` | คีย์บอร์ดยืมที่ถอดปุ่มได้ (มีการสลับและ GT รายช่อง) | ตาม Leave-keyboard-out + Group split |
| `own_capture_fixed` | คีย์บอร์ดห้องแล็บถอดปุ่มไม่ได้ ภาพถูกทั้งหมดเท่านั้น (Validator: `fixed_keyboard_swapped`) | เหมือน `own_capture` |
| `own_pilot` | ภาพ Pilot (P1.B) | Train ได้ ห้ามอยู่ Unseen test (§5.2) — ภาพ Pilot ของคีย์บอร์ด `unseen_test` จะเป็น `excluded` |
| `public_dataset` / `web_cc` / `augment` | ข้อมูลเสริม (P2.B′) | Train เท่านั้น |

`annotator`, `reviewer` และ `assist_model_id` ไม่ใช่คอลัมน์ของ `images.csv` ให้บันทึกแยกใน `metadata/annotation_log.csv` (`image_id`, `annotator`, `reviewer`, `assist_model_id`, `review_date`) Validator ไม่อ่านไฟล์นี้ แต่ Model card ใช้ค่า `assist_model_id` จากไฟล์นี้

### 5.2 ระดับคีย์บอร์ด — `data/keyboards.csv` (§5.4, Plan P1.A, D10)

ไฟล์เดียวสำหรับทั้งโปรเจกต์ ใช้ทั้งตอนวางแผนถ่าย (เป็นต้นทางของไฟล์ `--keyboards` ใน `schedule` §5.3) และใน Dataset ผ่าน Symlink `metadata/keyboards.csv` (§0.1) คอลัมน์ตาม `KEYBOARD_COLS` ใน `schema.py`:

| Column | ค่า |
| --- | --- |
| `keyboard_id` | เช่น `kb01` — ไม่ใส่ชื่อเจ้าของ (บังคับ) |
| `form_factor` | `ANSI` หรือ `ISO` ต่อด้วยขนาด: `ANSI-60` / `ANSI-65` / `ANSI-75` / `ANSI-TKL` / `ANSI-Full` / `ISO-…` / `…-laptop` / `…-other` (รวมตาม Spec §5.4) |
| `legend_style` | `en_only` / `th_en` (บังคับ) |
| `legend_position` | `center` / `top_left` / `top_center` / `bottom_left` / `other` |
| `keycap_color`, `legend_color` | เช่น `black`, `white` |
| `profile` | `OEM` / `Cherry` / `SA` / `XDA` / `DSA` / `unknown` |
| `removable_keycaps` | `1` / `0` (ถอดไม่ได้ = ภาพ `own_capture_fixed` ถูกทั้งหมดเท่านั้น) |
| `role` | `train` / `heldout_val` / `unseen_test` (บังคับ) — ล็อกก่อนถ่ายจริง (D10) |
| `note` | ยี่ห้อ/รุ่น ผิวปุ่ม และที่มา ในรูป `key=value` คั่นด้วย `;` เช่น `model=Keychron K2; finish=glossy; from=lab` (ไม่ใส่ข้อมูลส่วนตัว) และหมายเหตุ เช่น Layout คลาดจาก Generic มาก |

- `finish=matte|glossy|unknown` ใน `note` ใช้วิเคราะห์ Glare ตอนทำ Error analysis
- `role` ใช้โดย Leave-keyboard-out split (P2.D): `unseen_test` → Test ทั้งหมด, `heldout_val` → Validation ทั้งหมด, `train` → Group split 70/15/15
- **ล็อกใน Git (P2 Exit criteria):** ตอนนี้ `.gitignore` มี `data/*` จึงไม่รวมไฟล์นี้ จนกว่าจะเพิ่ม `!data/keyboards.csv` ให้ใช้ `git add -f data/keyboards.csv` เมื่อ Commit ครั้งแรก (หลังจากนั้น Git ติดตามการแก้ไขต่อเอง) การเปลี่ยน `role` หลังเริ่มถ่ายจริงต้องบันทึกเหตุผลใน Commit message

### 5.3 Arrangement schedule — `metadata/arrangements.csv` (Plan P2.A)

Schedule สร้างด้วยสคริปต์ ไม่ต้องคิดคู่สลับเอง:

```bash
python -m ai.data.keyboard_dataset schedule --seed <seed> \
  --keyboards <keyboards ที่ถอดปุ่มได้>.csv --shots 2 \
  --out data/keyboard_qwerty_v1/metadata/arrangements.csv
```

- ผลลัพธ์ **คงที่ต่อ `--seed`** บันทึก Seed และคำสั่งไว้ใน Capture log เพื่อสร้างซ้ำได้จาก `data/keyboards.csv` ใน Git
- `--keyboards` ใช้สำเนาของ `data/keyboards.csv` ที่มีเฉพาะแถว `removable_keycaps = 1` เพราะสคริปต์แจกทุกชนิดการสลับแบบ Round-robin ให้ทุกคีย์บอร์ดที่ได้รับ
- ค่าตั้งต้นคือ 100 ถูกทั้งหมด / 200 สลับหนึ่งคู่ / 100 สลับหลายคู่ (§5.2) สำหรับ Pilot ให้ลดด้วย `--n-correct`, `--n-one-pair`, `--n-multi`

| Column | ความหมาย |
| --- | --- |
| `arrangement_id` | ID ที่ต้องคัดลอกลง Capture log และ `images.csv` (`arr_0001`, `arr_0002`, …) |
| `kind` | `correct` / `one_pair` / `multi_pair` / `cycle` |
| `instructions` | **คำสั่งสำหรับคนถ่าย** เช่น `Q<->W; A->S->D->A` (`-` = ถูกทั้งหมด) |
| `perm` | `dst=src` ตาม `slot_id` ที่สคริปต์ใช้เติม `actual_label` — ไม่ต้องอ่านเอง |
| `n_incorrect`, `pair_types` | จำนวนช่องที่ผิด และชนิดคู่ (`adjacent` / `same_row` / `cross_row` / `cycle`) |
| `test_only` | `1` = ใช้คู่สลับที่สงวนไว้ให้ Test; Splitter บังคับเข้า Test และไม่แจกให้คีย์บอร์ด `heldout_val` |
| `keyboard_id` | คีย์บอร์ดที่ต้องถ่าย Arrangement นี้ |
| `planned_shots` | จำนวนภาพที่ถ่ายต่อ Arrangement (§5.5: ทั้งหมดอยู่ Split เดียวกัน) |

- ถ่ายตาม `instructions` ทุกตัวอักษร ห้ามสลับคู่อื่นเพิ่มหรือเปลี่ยนคู่เอง โดยเฉพาะแถว `test_only = 1` เพราะคู่นั้นต้องไม่ปรากฏใน Train
- ภาพ `own_capture_fixed` (ถอดปุ่มไม่ได้) ใช้ `arrangement_id` ของแถว `kind = correct` แถวแรกใน Schedule (ตาม [`dataset-format.md`](./dataset-format.md) §3: ภาพถูกทั้งหมดก็ต้องมี ID ของแถว `correct`) เพื่อให้ `prefill-slots` เติม `actual_label` = `expected_label` ให้เอง แถวนั้นถูกแจกให้คีย์บอร์ดอื่น Validator จึงเตือน `arrangement_keyboard` สำหรับภาพเหล่านี้ ซึ่งเป็นที่คาดไว้ ส่วนการตรวจว่าถูกทั้งหมดทำโดย `fixed_keyboard_swapped` ห้ามส่งคีย์บอร์ดที่ถอดปุ่มไม่ได้เข้า `--keyboards` เพราะสคริปต์จะแจกแถวสลับปุ่มที่ถ่ายไม่ได้ให้ด้วย
- เมื่อใช้ ID จาก Schedule Validator จะเทียบ `actual_label` กับ `perm` ให้อัตโนมัติ (`actual_vs_arrangement`) ถ้าตั้ง ID เอง การตรวจนี้จะถูกข้ามไป เหลือเพียงคำเตือน `arrangement_unknown`

---

## 6. เครื่องมือ Annotation (D7)

| เกณฑ์ | CVAT Community | Label Studio Community |
| --- | --- | --- |
| License | MIT | Apache-2.0 |
| กรอบ + Attributes ต่อกรอบ | ได้ (`occluded` เป็นค่า Built-in ของ Shape) | ได้ (`Choices` ต่อ Region) |
| จุดอ้างอิง | Shape `points` | `KeyPointLabels` |
| COCO export | **COCO 1.0** รองรับกรอบ/Polygon/Mask และเก็บ Attributes ใน `attributes`; **ไม่ส่งออก `points`** | COCO export ได้ แต่ KeyPoint ต้องผูกเป็นลูกของ Rectangle และมี `model_index` |
| Export ที่มีครบทุกอย่าง | **CVAT for images 1.1** (XML) | JSON (Full) |
| Import Pre-annotation | COCO 1.0 / CVAT XML | JSON Predictions |
| Self-host | Docker Compose | `pip`/Docker |

**ข้อเสนอ: CVAT** — Attribute ต่อกรอบและ `points` ใช้ตรงไปตรงมา และ Import COCO สำหรับ Assist annotation ได้ ส่วนจุดอ้างอิงที่ COCO 1.0 ไม่ส่งออก ให้ Export เพิ่มเป็น CVAT XML แล้วเขียนลง `images.csv` ตาม §6.3

> ถ้าใช้ CVAT แบบ Self-host บนเครื่องนี้ ให้ตั้งชื่อ Container ขึ้นต้น `keycheck-` และอย่าใช้พอร์ต 9000 (มีโปรเจกต์อื่นใช้อยู่)

### 6.1 ขั้นตอน CVAT

1. สร้าง **Project** `keycheck_<dataset_version>` ด้วย Labels ตามลำดับนี้ (`keycap` ต้องเป็น Label แรก):
   - `keycap` — Type `rectangle`, Attribute `truncated` (checkbox, default false)
   - `ref_TL`, `ref_TR`, `ref_BR`, `ref_BL` — Type `points` (หนึ่งจุดต่อ Label)
2. สร้าง **Task ต่อ `capture_session_id`** ใน Project นั้น (ปล่อยช่อง Subset ว่าง) อัปโหลดภาพที่ Normalize EXIF แล้ว (§1) ด้วยชื่อไฟล์เดียวกับ `file_name` และไม่ผสมหลายคีย์บอร์ดใน Task เดียว
3. (ถ้ามี) Import Pre-annotation: Actions → Upload annotations → **COCO 1.0** (§7)
4. Annotate ตาม §2–§3 ใช้ค่า Built-in `occluded` ของ CVAT สำหรับปุ่มที่ถูกบัง
5. Review ตาม §7–§8 แล้วตั้ง Job state = `completed`
6. Export **ระดับ Project** (ไฟล์เดียวรวมทุก Task): Project → Export dataset
   - **COCO 1.0** → ได้ `annotations/instances_default.json` (กรอบ `keycap` + Attributes)
   - **CVAT for images 1.1** → ได้ `annotations.xml` (จุดอ้างอิงสี่จุด)
   - ปิด "Save images" (ภาพต้นฉบับมีอยู่แล้วพร้อม SHA-256)
7. รวมเข้า Dataset ตาม §6.3 แล้วรัน `manifest` → `split` → `validate` (P2.D)

### 6.2 ถ้าเลือก Label Studio

Labeling config: `RectangleLabels` (`keycap`) + `KeyPointLabels` (`ref_TL` … `ref_BL`) + `Choices` ต่อ Region (`truncated`, `occluded`) Export เป็น **JSON (Full)** ใน `ai/` ยังไม่มีตัวแปลงรูปแบบนี้ จึงต้องเขียนเพิ่มก่อนใช้ ไม่ควรใช้ COCO export ของ Label Studio สำหรับจุดอ้างอิง เพราะต้องจัด Hierarchy ด้วยมือทีละจุด

### 6.3 รวม Export ของ CVAT เข้า Dataset

ใน `ai/` ยังไม่มีคำสั่งนำเข้า CVAT (บันทึกเป็นงานค้างของเจ้าของ `ai/data/keyboard_dataset`) ระหว่างนี้ใช้สคริปต์ด้านล่าง สคริปต์นี้ทำสองอย่าง (1) เขียนจุด `ref_TL…ref_BL` จาก `annotations.xml` ลงคอลัมน์ `ref_*` และ `width`/`height` ของ `metadata/images.csv` โดยจับคู่ตามชื่อไฟล์ (2) แปลง `instances_default.json` เป็น `annotations/keycaps_coco.json` ที่มีคลาสเดียว `keycap = 1` ให้บันทึกเป็นไฟล์นอก repo แล้วรันจาก root ของ repo ด้วย Python environment ของ `ai/`:

```bash
python cvat_import.py annotations.xml instances_default.json data/keyboard_qwerty_v1
```

```python
# cvat_import.py — usage (repo root, ai/ env): python cvat_import.py <annotations.xml> <instances_default.json> <dataset_root>
import json, sys
import xml.etree.ElementTree as ET
from pathlib import Path
from ai.data.keyboard_dataset.schema import (COCO_JSON, COCO_KEYCAP_ID, COCO_KEYCAP_NAME, IMAGE_COLS, IMAGES_CSV,
                                             read_csv, write_csv)

xml_path, coco_path, root = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
CORNERS = ("tl", "tr", "br", "bl")

# 1) ref_TL..ref_BL points (CVAT for images 1.1) -> ref_*_x/y columns of metadata/images.csv
refs = {}
for im in ET.parse(xml_path).getroot().iter("image"):
    pts = {p.get("label"): p.get("points") for p in im.iter("points")}
    got = [c for c in CORNERS if f"ref_{c.upper()}" in pts]
    if not got:
        continue                                   # no ref points: image must not be in the dataset
    bad = [c for c in CORNERS if c not in got or ";" in pts[f"ref_{c.upper()}"]]
    if bad:
        sys.exit(f"{im.get('name')}: need exactly one point for each of ref_{'/'.join(c.upper() for c in bad)}")
    refs[Path(im.get("name")).name] = ({c: pts[f"ref_{c.upper()}"].split(",") for c in CORNERS},
                                       im.get("width"), im.get("height"))
rows = read_csv(root / IMAGES_CSV)
n = 0
for r in rows:
    hit = refs.get(Path(r["file_name"]).name)
    if hit is None:
        continue
    xy, w, h = hit
    if (r.get("width") or w) != w or (r.get("height") or h) != h:
        sys.exit(f"{r['file_name']}: CVAT size {w}x{h} != images.csv {r['width']}x{r['height']} (EXIF not normalized?)")
    r["width"], r["height"] = w, h
    for c in CORNERS:
        r[f"ref_{c}_x"], r[f"ref_{c}_y"] = xy[c]
    n += 1
cols = list(IMAGE_COLS) + [k for k in (rows[0] if rows else {}) if k not in IMAGE_COLS]
write_csv(root / IMAGES_CSV, cols, rows)
print(f"ref points written for {n}/{len(rows)} images; CVAT images not in images.csv: "
      f"{sorted(set(refs) - {Path(r['file_name']).name for r in rows})}")

# 2) COCO 1.0 export -> annotations/keycaps_coco.json with the single class keycap = 1 (ref_* labels dropped)
coco = json.loads(coco_path.read_text(encoding="utf-8"))
kid = next(c["id"] for c in coco["categories"] if c["name"] == COCO_KEYCAP_NAME)
coco["annotations"] = [{**a, "category_id": COCO_KEYCAP_ID} for a in coco["annotations"] if a["category_id"] == kid]
coco["categories"] = [{"id": COCO_KEYCAP_ID, "name": COCO_KEYCAP_NAME, "supercategory": "key"}]
(root / COCO_JSON).parent.mkdir(parents=True, exist_ok=True)
(root / COCO_JSON).write_text(json.dumps(coco, ensure_ascii=False), encoding="utf-8")
print(f"{len(coco['annotations'])} keycap boxes -> {root / COCO_JSON}")
```

- จับคู่ภาพด้วย **ชื่อไฟล์ (basename)** จึงต้องตั้งชื่อไฟล์ไม่ซ้ำกันทั้ง Dataset เช่นขึ้นต้นด้วย `capture_session_id`
- สคริปต์หยุดโดยไม่เขียนไฟล์ ถ้าภาพใดมีจุดไม่ครบสี่ Label หรือมีหลายจุดใน Label เดียว และหยุดเมื่อขนาดภาพใน CVAT ไม่ตรงกับ `images.csv` (มักเกิดจากไม่ได้ Normalize EXIF)
- ทุกครั้งที่ Export ใหม่ ให้รันสคริปต์ซ้ำได้ ค่า `ref_*` จะถูกเขียนทับด้วยค่าล่าสุด

---

## 7. Assist annotation + การตรวจโดยคน (§19, Plan P2.C)

| ขั้น | ใครทำ | ใช้อะไร |
| --- | --- | --- |
| 1. Pre-label กรอบ `keycap` | สคริปต์ | Detector จาก Pilot (หรือ Dev bundle ที่ฝึกจาก Kaggle proxy) Export เป็น COCO 1.0 แล้ว Import |
| 2. Pre-fill ตาราง GT | สคริปต์ | `python -m ai.data.keyboard_dataset prefill-slots <dataset_root>` เติม 26 แถวต่อภาพ โดย `actual_label` มาจาก `perm` ใน Schedule และ `ground_truth_status = pending_review` |
| 3. วางจุดอ้างอิง | Annotator | ทำด้วยมือทุกภาพ (การหาจุดอัตโนมัติเป็น Should-have §3.2) |
| 4. แก้กรอบ | Annotator | ลบกรอบเกิน เพิ่มปุ่มที่ขาด ปรับขอบ ตั้ง Flags |
| 5. ยืนยันตาราง GT | Annotator | เทียบตัวอักษรในภาพกับ Schedule ทีละช่อง ตั้ง `readable` แล้วเปลี่ยนสถานะเป็น `verified` / `disputed` |
| 6. Review | ผู้ตรวจคนที่สอง | ตามสัดส่วนใน §8 |

กฎ:

- **ห้ามใช้ OCR เติม `actual_label`** เพราะ OCR คือสิ่งที่ถูกประเมิน ถ้าใช้เป็น GT จะเป็นการวัดตัวเองกับตัวเอง (§6.2, §7.5) ใช้ OCR ได้เฉพาะช่วยหา Log ที่จดผิด โดยแสดงคู่กันแล้วให้คนตัดสิน
- บันทึก `assist_model_id` ใน `metadata/annotation_log.csv` สำหรับทุกภาพที่ใช้ Pre-label เพื่อรายงานใน Model card
- Pre-label ไม่ลดมาตรฐาน: ภาพ Test ต้องผ่าน Review ครบ 100% (§8)
- ข้อมูลเสริมจาก Public dataset หรือเว็บ (P2.B′) ไม่ต้องมีตาราง GT รายช่อง แต่ต้องแปลงคลาสเป็น `keycap`, บันทึก `source`, `source_url`, `license` และอยู่ใน Train เท่านั้น (§5.1)

---

## 8. QA Checklist

### 8.1 ต่อภาพ (Annotator)

- [ ] ภาพ Normalize EXIF แล้ว ขนาดตรงกับ `width`/`height`
- [ ] จุดอ้างอิงครบ 4 จุด ลำดับ TL→TR→BR→BL อยู่ที่กึ่งกลางช่องตาม **ตำแหน่ง** และภาพ Rectified ตั้งตรงโดยมีช่อง Q อยู่ซ้ายบน (§2)
- [ ] ทุกคีย์แคปที่มองเห็นมีกรอบ `keycap` (นับปุ่มรอบบล็อก A–Z ด้วย)
- [ ] ไม่มีกรอบซ้ำซ้อนบนปุ่มเดียว ไม่มีกรอบบนสิ่งที่ไม่ใช่คีย์แคป
- [ ] ปุ่มที่ถูกตัด/บังมี Flag ถูกต้อง
- [ ] ตาราง GT 26 แถว `actual_label` เป็น A–Z อังกฤษเท่านั้น ไม่เหลือ `pending_review`
- [ ] `arrangement_id` คัดลอกจาก `metadata/arrangements.csv` (`own_capture_fixed` ใช้แถว `kind = correct` แถวแรก §5.3)
- [ ] ภาพที่มีช่อง `readable = 0` ติด `subset = robustness` และมี `robustness=<ชนิด>` ใน `note`

### 8.2 ผู้ตรวจคนที่สอง

| ชุด | สัดส่วน Review | หมายเหตุ |
| --- | --- | --- |
| Test (Unseen + Seen) | 100% | ห้ามมีข้อสงสัยค้าง |
| Validation | 100% ของตาราง GT, สุ่ม ≥ 20% สำหรับกรอบ | ใช้เลือก Threshold |
| Train | สุ่ม ≥ 10% ต่อ `capture_session_id` | ถ้าพบ Error > 5% ของภาพที่สุ่ม → Review ทั้ง Session |

*สัดส่วนเป็นค่าตั้งต้น ปรับหลัง Pilot pipeline*

### 8.3 อัตโนมัติ (`python -m ai.data.keyboard_dataset validate <dataset_root>`, Plan P2.D)

Validator หยุดด้วย Exit code 1 เมื่อมี Error และใช้ `--strict` ให้ Warning ทำให้ล้มด้วย

- [ ] กรอบอยู่ในขอบภาพ, กว้าง/สูง > 0, `category_id = 1` คลาสเดียว
- [ ] 26 ช่องครบทุกภาพของเราเอง; `expected_label` ตรงกับ Layout; ไม่เหลือ `gt_not_verified`
- [ ] จุดอ้างอิงผ่าน `validate_reference_points` (นูน ไม่ไขว้ อยู่ในภาพ พื้นที่พอ) — จุดที่เริ่มผิดมุมต้องตรวจด้วยตา (§2)
- [ ] ไม่มี `actual_vs_arrangement`: ทุกช่องตรงกับ `perm` ของ Arrangement ใน Schedule (ต้องใช้ `arrangement_id` จาก Schedule §5.3 การตรวจนี้จึงจะทำงาน)
- [ ] ไม่มีภาพซ้ำหรือใกล้ซ้ำข้าม Split (SHA-256 + Perceptual hash จาก `manifest`)
- [ ] ไม่มี `keyboard_id` ของ `unseen_test` ใน Train/Val และของ `heldout_val` ใน Train; Arrangement `test_only` ไม่อยู่ใน Train/Val
- [ ] ข้อมูลเสริมจากเว็บหรือ Public dataset ไม่อยู่ใน Validation/Test
- [ ] ภาพ `subset = robustness` ไม่อยู่ใน Train (ตามนโยบายใน [`capture-guide.md`](./capture-guide.md) B.5 — Validator ยังไม่ตรวจข้อนี้ ต้องดูจาก `split_manifest.json`)
- [ ] บันทึก `dataset_version` และ `split_manifest_hash` แล้ว (Plan P2.D)
