# KeyCheck — รูปแบบ Dataset QWERTY ของเรา

**อ้างอิง:** [`keycheck-technical-specification.md`](./keycheck-technical-specification.md) §5, §7.2, §9 · [`implementation-plan.md`](./implementation-plan.md) P1.B–P1.D, P2.A–P2.D, การตัดสินใจ D6 และ D10
**โค้ด:** `ai/data/keyboard_dataset/` (Tooling ของ Dataset) และ `ai/evaluation/pilot.py` (Pilot report)
**สถานะ:** Tooling พร้อมใช้และทดสอบแล้วด้วยข้อมูลจำลอง (`tests/ai/test_keyboard_dataset*.py`, `tests/ai/test_pilot.py`) แต่ยังไม่มีภาพจริง

> เอกสารนี้กำหนดรูปแบบไฟล์ของ Dataset ที่เราถ่ายเอง เป็นคนละชุดกับ Kaggle QWERTZ ที่ใช้เป็น Proxy (`docs/qwertz-notebook-pipeline-plan.md`) ตัวอย่างทุกตัวในเอกสารนี้สร้างจากโค้ดจริง (`python -m ai.data.keyboard_dataset demo`) ไม่ได้พิมพ์เอง

---

## 1. โครงสร้างไดเรกทอรี

```
data/keyboard_qwerty_v1/                 ← dataset root (อยู่นอก Git ตาม .gitignore: data/*)
├── images/                              ← ภาพต้นฉบับตามที่ถ่าย (เก็บ EXIF ไว้ ไม่ต้องหมุนเอง)
│   └── kb01/kb01_s01_arr_0001_0.jpg      ← แนะนำแยกโฟลเดอร์ตาม keyboard_id
├── metadata/
│   ├── images.csv                       ← Metadata ระดับภาพ (§3)
│   ├── keyboards.csv                    ← Metadata ระดับคีย์บอร์ด (§4)
│   ├── slots.csv                        ← Ground truth รายช่อง 26 แถวต่อภาพ (§5)
│   └── arrangements.csv                 ← แผนการจัดวาง/สลับปุ่ม (§6)
├── annotations/
│   └── keycaps_coco.json                ← กรอบคีย์แคปทุกปุ่มที่มองเห็น (COCO, §7)
└── manifests/
    ├── manifest.json                    ← SHA-256 + Perceptual hash + รายงานภาพซ้ำ (§8)
    └── split_manifest.json              ← ผลแบ่ง Split + split_manifest_hash (§9)
```

- ไฟล์ใน `manifests/` และ `metadata/keyboards.csv` / `metadata/arrangements.csv` เมื่อล็อกแล้ว ให้คัดลอกไปไว้ที่ `data/manifests/<dataset_version>/` ซึ่ง **Commit เข้า Git** (Exit criteria ของ P2: Hash ใน Git)
- `dataset_version` ตั้งชื่อแบบ `keyboard_qwerty_v1` และเปลี่ยนเลขทุกครั้งที่เพิ่ม/ลบภาพหรือแก้ Label หลังล็อก Split
- เริ่มโครงว่างได้ด้วย `python -m ai.data.keyboard_dataset init data/keyboard_qwerty_v1` ซึ่งสร้าง CSV ที่มีเฉพาะ Header และ COCO เปล่าที่มีคลาส `keycap` (ไม่เขียนทับไฟล์เดิม)

## 2. ระบบพิกัด (D6)

| ชื่อ | ความหมาย | ใช้ที่ไหน |
| --- | --- | --- |
| `original_oriented` | ภาพหลังแก้ EXIF orientation (`PIL.ImageOps.exif_transpose`) หน่วย Pixel | จุดอ้างอิง 4 จุด, กรอบ COCO, `width`/`height` |
| `rectified` | Canonical canvas จาก Homography ของ 4 จุด (`ai.preprocessing.geometry`) ช่วง u ∈ [-1.5, 10.5] × [-1.5, 3.5] ที่ `px_per_unit` | ชุด YOLO สำหรับฝึก, Crop สำหรับ OCR |
| `u` | หน่วยปุ่ม (Key pitch = 1u) ของ Generic letter-block | Layout, การวัดความคลาดเคลื่อน |

- **Annotate บนภาพ `original_oriented` เสมอ** แล้วให้สคริปต์สร้างชุด Rectified เอง (ไม่ผูก Annotation กับ Canvas version) — เครื่องมืออย่าง CVAT/Label Studio แสดงภาพตาม EXIF อยู่แล้ว ให้ตรวจว่า `width`/`height` ใน COCO ตรงกับภาพหลังหมุน (Validator ตรวจให้)
- จุดอ้างอิงเรียง **TL, TR, BR, BL = กึ่งกลางช่อง Q, P, M, Z ตามตำแหน่ง** (`r0c0`, `r0c9`, `r2c6`, `r2c0`) ไม่ใช่ตามตัวอักษรที่เห็น เพราะปุ่มอาจถูกสลับอยู่

## 3. `metadata/images.csv` — ระดับภาพ

| คอลัมน์ | บังคับ | ค่า | หมายเหตุ |
| --- | --- | --- | --- |
| `image_id` | ✔ | ข้อความไม่ซ้ำ | แนะนำ `<keyboard_id>_<session>_<arrangement>_<shot>` |
| `file_name` | ✔ | path ใต้ `images/` | ต้องตรงกับ `file_name` ใน COCO |
| `keyboard_id` | ✔ (ภาพของเรา) | ต้องมีใน `keyboards.csv` | ว่างได้เฉพาะ `public_dataset`/`web_cc`/`augment` |
| `capture_session_id` | ✔ (ภาพของเรา) | **ไม่ซ้ำข้ามคีย์บอร์ด** เช่น `kb01_s02` | หนึ่งรอบถ่าย = ย้ายกล้อง/คีย์บอร์ด/แสงจริง |
| `arrangement_id` | ✔ (ภาพของเรา) | ต้องมีใน `arrangements.csv` | ภาพถูกทั้งหมดก็ต้องมี id ของแถว `correct` |
| `device` | | ข้อความ | เช่น `iphone13`, `pixel7` |
| `lighting` | | `daylight` `indoor_warm` `indoor_cool` `mixed` `low` `flash` `other` | ค่าอื่นได้ Warning |
| `split` | | `train` `val` `test` `excluded` หรือว่าง | **อย่ากรอกเอง** ให้คำสั่ง `split --write-csv` เติม |
| `source` | ✔ | ดูตารางด้านล่าง | |
| `source_url` | ✔ เมื่อ `web_cc`/`public_dataset` | URL | |
| `license` | ✔ เมื่อ `web_cc`/`public_dataset` | เช่น `own`, `CC-BY-4.0` | |
| `width`, `height` | | ขนาดภาพ `original_oriented` | ว่างได้ Manifest วัดให้ ถ้ากรอกต้องตรงกับไฟล์ |
| `ref_tl_x` … `ref_bl_y` | ✔ (ภาพของเรา) | 8 ตัวเลข: `ref_tl_x, ref_tl_y, ref_tr_x, ref_tr_y, ref_br_x, ref_br_y, ref_bl_x, ref_bl_y` | Pixel บน `original_oriented` ต้องอยู่ในภาพ นูน ไม่ไขว้ |
| `subset` | | `main` (ค่าเริ่มต้น) หรือ `robustness` | ภาพเบลอ/สะท้อน/บัง/Ortholinear/แตะผิดช่อง (Spec §5.2) รายงานแยก |
| `note` | | ข้อความ | |

ค่า `source`:

| `source` | ความหมาย | Split ที่อนุญาต |
| --- | --- | --- |
| `own_capture` | คีย์บอร์ดที่ถอดปุ่มได้ (มีภาพสลับและ Ground truth รายช่อง) | ทุก Split ตามกฎ §9 |
| `own_capture_fixed` | คีย์บอร์ดที่ถอดปุ่มไม่ได้ เช่น ห้องแล็บ (ภาพถูกทั้งหมดเท่านั้น) | ทุก Split ตามกฎ §9 |
| `own_pilot` | ภาพ Pilot (P1.B) | Train เท่านั้น; ห้ามเป็น Unseen test (Spec §5.2) |
| `public_dataset`, `web_cc`, `augment` | ข้อมูลเสริมสำหรับ Detector | **Train เท่านั้น** (Spec §5.1) |

ตัวอย่าง (สร้างจากโค้ด):

```csv
image_id,file_name,keyboard_id,capture_session_id,arrangement_id,device,lighting,split,source,source_url,license,width,height,ref_tl_x,ref_tl_y,ref_tr_x,ref_tr_y,ref_br_x,ref_br_y,ref_bl_x,ref_bl_y,subset,note
kb01_s01_arr_0001_0,kb01/kb01_s01_arr_0001_0.png,kb01,kb01_s01,arr_0001,synthetic,indoor_cool,test,own_capture,,own,800,400,106.97,72.41,636.68,121.47,489.16,230.02,145.83,194.98,main,
```

## 4. `metadata/keyboards.csv` — ระดับคีย์บอร์ด (Spec §5.4)

| คอลัมน์ | บังคับ | ค่า |
| --- | --- | --- |
| `keyboard_id` | ✔ | ไม่ซ้ำ เช่น `kb01` |
| `form_factor` | | `ANSI` หรือ `ISO` ตามด้วย `-60` `-65` `-75` `-TKL` `-Full` `-laptop` `-other` เช่น `ISO-TKL` |
| `legend_style` | ✔ | `en_only` หรือ `th_en` |
| `legend_position` | | `center` `top_left` `top_center` `bottom_left` `other` |
| `keycap_color`, `legend_color` | | ข้อความ เช่น `black`, `white` |
| `profile` | | ข้อความ เช่น `OEM`, `Cherry`, `SA`, `low_profile` |
| `removable_keycaps` | | `1`/`0` |
| `role` | ✔ | `train` · `heldout_val` · `unseen_test` (D10) |
| `note` | | ข้อความ |

```csv
keyboard_id,form_factor,legend_style,legend_position,keycap_color,legend_color,profile,removable_keycaps,role,note
kb01,ANSI-TKL,en_only,top_left,black,white,OEM,1,train,
```

**D10 — ต้องล็อก `role` ก่อนถ่ายจริง:** `unseen_test` 2–3 ตัว (มี `th_en` อย่างน้อยหนึ่งตัว) และ `heldout_val` 1 ตัวถ้ามีคีย์บอร์ดพอ Validator เตือนเมื่อไม่ครบ

## 5. `metadata/slots.csv` — Ground truth รายช่อง

ภาพ `own_capture`, `own_capture_fixed`, `own_pilot` ต้องมี **26 แถวต่อภาพ** ครบทุก `slot_id` ของ `qwerty_stagger_letters_v1`

| คอลัมน์ | ค่า | หมายเหตุ |
| --- | --- | --- |
| `image_id` | ตาม `images.csv` | |
| `slot_id` | `r<row>c<col>` เช่น `r0c0` | ตำแหน่ง ไม่ใช่ตัวอักษร |
| `expected_label` | ตาม Layout | Validator ตรวจว่าตรงกับ Layout |
| `actual_label` | A–Z ตัวเดียว | ตัวอักษรของคีย์แคปที่อยู่ในช่องนั้นจริง **ปุ่มไทย-อังกฤษให้ใส่เฉพาะตัวอังกฤษ** |
| `readable` | `1`/`0` | `0` = มองไม่เห็น/อ่านไม่ได้ในภาพนี้ (ไม่ใช้ประเมิน OCR) |
| `ground_truth_status` | `verified` · `pending_review` · `disputed` | แถวที่เติมอัตโนมัติจากแผนเป็น `pending_review` จนกว่าคนตรวจกับภาพ |
| `note` | ข้อความ | หมายเหตุผู้ตรวจ |

```csv
image_id,slot_id,expected_label,actual_label,readable,ground_truth_status,note
kb01_s01_arr_0001_0,r0c0,Q,Q,1,verified,
```

`python -m ai.data.keyboard_dataset prefill-slots <root>` เติม 26 แถวให้ภาพที่ยังไม่มี โดยใช้ `actual_label` จาก `arrangements.csv` (สถานะ `pending_review`) Validator เตือนเมื่อ `actual_label` ไม่ตรงกับแผน หรือไม่เป็น Permutation ของ A–Z

## 6. `metadata/arrangements.csv` — แผนการจัดวาง (P2.A)

สร้างด้วย `python -m ai.data.keyboard_dataset schedule --out <root>/metadata/arrangements.csv --seed <seed> [--keyboards <root>/metadata/keyboards.csv]`

- สัดส่วนตาม Spec §5.2: `correct` 100 · `one_pair` 200 · กลุ่มสลับ 2–3 คู่ 100 (= `multi_pair` 75 + `cycle` 25 โดย `cycle` = วนสามช่อง + หนึ่งคู่ ผิด 5 ช่อง) ปรับจำนวนด้วย `--n-correct --n-one-pair --n-multi` (หน่วยเป็นแถวการจัดวาง ถ้าถ่ายหลายภาพต่อการจัดวาง ให้หารด้วย `--shots`)
- เลือกคู่แบบ Greedy ให้ช่องที่ถูกย้ายน้อยที่สุดก่อน → **ทุกตัวอักษรอยู่นอกตำแหน่งหลายครั้ง** ทั้ง `adjacent` (ข้างกันในแถว) และ `cross_row` (คนละแถว) สัดส่วนประมาณ 50/50 (ค่าเริ่มต้น: ทุกช่องถูกย้าย ≥ 30 ครั้ง)
- **กันบางรูปแบบไว้ให้ Test เท่านั้น:** สุ่มคู่สงวน (`--reserved-pairs`, ค่าเริ่มต้น 8) ที่ไม่ใช้ในแถวอื่นเลย แถวที่ใช้คู่สงวนมี `test_only=1` (≈10%) และคำสั่ง `split` บังคับให้ไป Test; ไม่จัดให้คีย์บอร์ด `heldout_val`
- Deterministic ตาม `--seed` (บันทึก Seed ไว้กับ Dataset)

| คอลัมน์ | ความหมาย |
| --- | --- |
| `arrangement_id` | เช่น `arr_0001` |
| `kind` | `correct` · `one_pair` · `multi_pair` · `cycle` |
| `n_incorrect` | จำนวนช่องที่ผิด |
| `perm` | `dst=src;…` = ช่อง `dst` มีคีย์แคปของช่อง `src` (ใช้คำนวณ `actual_label`) |
| `instructions` | คำสั่งสำหรับคนจัดปุ่ม เช่น `C<->V` หรือ `U->B->H->U` |
| `pair_types` | ประเภทของแต่ละคู่ |
| `test_only` | `1` = ห้ามอยู่ใน Train/Validation |
| `keyboard_id` | คีย์บอร์ดที่วางแผนให้ (ถ้าให้ `--keyboards`) |
| `planned_shots` | จำนวนภาพที่ตั้งใจถ่าย |

```csv
arrangement_id,kind,n_incorrect,perm,instructions,pair_types,test_only,keyboard_id,planned_shots
arr_0001,one_pair,2,r2c2=r2c3;r2c3=r2c2,C<->V,adjacent,0,kb01,1
arr_0008,cycle,5,r0c1=r2c1;r0c6=r1c5;r1c5=r2c4;r2c1=r0c1;r2c4=r0c6,W<->X; U->B->H->U,cross_row;cycle,0,kb02,1
```

## 7. `annotations/keycaps_coco.json` — กรอบคีย์แคป

- COCO มาตรฐาน: `bbox = [x, y, w, h]` เป็น Pixel ของภาพ **`original_oriented`**, `images[].width/height` = ขนาดหลังแก้ EXIF
- **คลาสเดียว:** `categories = [{"id": 1, "name": "keycap"}]` ห้ามมีคลาสอื่น (ใน YOLO เป็นคลาส `0`, ใน Torchvision เป็น Label `1` เพราะ `0` คือ Background)
- กรอบ **ทุกคีย์แคปที่มองเห็น** ไม่ใช่แค่ A–Z (Spec §5.4) ปุ่มโดนตัดขอบให้กรอบเฉพาะส่วนที่เห็นในภาพ
- (ไม่บังคับ) Attribute `slot_id` บนกรอบของปุ่ม A–Z (`"attributes": {"slot_id": "r0c0"}` — CVAT/Label Studio export ได้) ถ้าไม่มี สคริปต์จะจับคู่กรอบกับช่องจากระยะกึ่งกลางหลัง Rectify ให้เอง (≤ 1u)

```json
{"id": 1, "file_name": "kb01/kb01_s01_arr_0001_0.png", "width": 800, "height": 400}
{"id": 1, "image_id": 1, "category_id": 1, "bbox": [82.81, 44.80, 48.62, 55.10], "area": 2678.86, "iscrowd": 0, "attributes": {"slot_id": "r0c0"}}
```

## 8. Manifest และภาพซ้ำ (P2.D)

`python -m ai.data.keyboard_dataset manifest <root> --version keyboard_qwerty_v1`

- ต่อภาพ: `sha256` ของไฟล์, ขนาดไฟล์, `width`/`height` หลังแก้ EXIF, ค่า EXIF orientation, `dhash` และ `phash` (64 บิต คำนวณด้วย numpy + PIL)
- `exact_duplicates`: ไฟล์ที่ SHA-256 เหมือนกัน · `near_duplicates`: คู่ที่ dHash ≤ 10 **และ** pHash ≤ 8 (ปรับด้วย `--dhash-max/--phash-max`) พร้อม `cross_split` เมื่อมี Split แล้ว
- คู่ใกล้เคียงที่เป็นคนละคีย์บอร์ดมักเป็นภาพ Layout เดียวกันมุมคล้ายกัน (False positive) จึงแสดงใน Manifest เท่านั้น ส่วนคู่คีย์บอร์ดเดียวกันถูกรวมกลุ่มตอนแบ่ง Split และ Validator เตือนถ้าอยู่คนละ Split — **ควรเปิดดูด้วยตาทุกคู่ก่อนล็อก**

## 9. การแบ่ง Split — Leave-keyboard-out (D10, Spec §5.5)

`python -m ai.data.keyboard_dataset split <root> --version keyboard_qwerty_v1 --seed <seed> [--write-csv]`

กฎตามลำดับ (ข้อแรกที่ตรงชนะ):

1. `public_dataset` / `web_cc` / `augment` → `train`
2. คีย์บอร์ด `unseen_test` → `test` ทั้งหมด (`test_subset = unseen_keyboard`); ภาพ Pilot ของคีย์บอร์ดนี้ → `excluded`
3. คีย์บอร์ด `heldout_val` → `val` ทั้งหมด
4. ภาพ Pilot ของคีย์บอร์ด `train` → `train`
5. ที่เหลือจัดกลุ่มตาม (`capture_session_id`, `arrangement_id`) — ภาพ Burst/จัดวางเดียวกันในรอบเดียวกันอยู่ Split เดียวกัน; ภาพซ้ำ (SHA เดียวกัน) และภาพใกล้เคียงของคีย์บอร์ดเดียวกันถูกรวมเป็นกลุ่มเดียว (ถ้ากลุ่มนั้นมีภาพที่ถูกบังคับ Split ตามข้อ 1–4 ทั้งกลุ่มตามไป)
6. กลุ่มที่ใช้การจัดวาง `test_only` → `test`
7. กลุ่มที่เหลือแบ่ง **70/15/15** ตามจำนวนภาพ ด้วย Seed ที่บันทึกไว้ (Test ส่วนนี้ = `seen_keyboard`)

ผลลัพธ์ `manifests/split_manifest.json`:

```json
{"dataset_version": "kq_demo", "seed": 42, "fractions": {"train": 0.7, "val": 0.15, "test": 0.15},
 "group_keys": ["capture_session_id", "arrangement_id"], "unseen_test_keyboards": ["kb06", "kb07"],
 "heldout_val_keyboards": ["kb05"], "test_only_arrangements": ["arr_0006"], "image_manifest_sha256": "4101…",
 "counts": {"test": {"images": 32, "groups": 16, "keyboards": ["kb01", "…"]}, "…": {}},
 "images": {"kb01_s01_arr_0001_0": {"split": "test", "reason": "group_split", "test_subset": "seen_keyboard",
            "group": "kb01_s01|arr_0001", "keyboard_id": "kb01", "sha256": "ceb0…"}},
 "split_manifest_hash": "0648…"}
```

`split_manifest_hash` = SHA-256 ของรายการ (`image_id`, `split`, `test_subset`, `sha256` ของภาพ) — เปลี่ยนเมื่อย้ายภาพข้าม Split หรือไฟล์ภาพเปลี่ยน Validator ตรวจว่า Hash ตรงกับเนื้อหา (กันแก้ด้วยมือ)

## 10. Validator (P2.D)

`python -m ai.data.keyboard_dataset validate <root> [--strict]` — พิมพ์รายการปัญหา (error/warning) และ **Exit code 1 เมื่อมี error** (`--strict` ให้ Warning ทำให้ Fail ด้วย)

| ตรวจ | ระดับ |
| --- | --- |
| คอลัมน์/ค่า Enum ใน CSV, `image_id`/`keyboard_id` ซ้ำ, จุดอ้างอิงไม่ครบ/ไขว้/นอกภาพ | error |
| ไฟล์ภาพหาย, `width`/`height` ไม่ตรงกับภาพหลังแก้ EXIF | error |
| COCO: คลาสต้องเป็น `keycap` id 1 เท่านั้น, `category_id` ถูก, กรอบอยู่ในภาพ (±1px) และมีพื้นที่, ขนาดภาพใน COCO ตรง, `file_name` ไม่ซ้ำ, `slot_id` attribute ถูกและไม่ซ้ำ | error |
| 26 Slots ครบทุกภาพที่ต้องมี, `expected_label` ตรง Layout, คีย์บอร์ดถอดปุ่มไม่ได้ต้องถูกทั้งหมด | error |
| ไม่มีภาพซ้ำ (SHA-256) ข้าม Split | error |
| `keyboard_id` ของ `unseen_test` ไม่อยู่ใน Train/Validation; `heldout_val` ไม่อยู่ใน Train | error |
| ข้อมูลเสริมจากเว็บ/Public/Augment ไม่อยู่ใน Validation/Test; Pilot ไม่เป็น Unseen test | error |
| การจัดวาง `test_only` ไม่อยู่ใน Train/Validation; กลุ่มรอบถ่ายเดียวกันไม่แตกข้าม Split; `split_manifest_hash` ตรง | error |
| ภาพใกล้เคียง (คีย์บอร์ดเดียวกัน) ข้าม Split, `actual_label` ไม่ตรงแผน/ไม่เป็น Permutation, GT ยังไม่ `verified`, D10 ไม่ครบ, ยังไม่ Annotate | warning |

## 11. Converter

- **COCO → YOLO (Rectified):** `python -m ai.data.keyboard_dataset to-yolo <root> --out <dir> [--ppu 96] [--train-jitter gt:0,j1:0.08,j2:0.15]` — Warp ภาพด้วย H จาก 4 จุด (`original_to_canvas_H`) แปลงมุมกรอบทั้งสี่ผ่าน H แล้วใช้กรอบล้อมรอบ ตัดกรอบที่เหลือในภาพ < 50% เขียน `images/<split>/`, `labels/<split>/` (คลาส `0`), `data.yaml`, `index.json` (เก็บ H ต่อภาพ) — Jitter จุดอ้างอิง (σ เป็นหน่วย u) ใช้กับ Train เท่านั้น Validation/Test ใช้จุดที่ Annotate
- **COCO → Torchvision:** `coco_to_torchvision(ds, layout=None|layout)` คืน `boxes` (xyxy float32), `labels` (= 1 ทุกกรอบ, 0 = Background), `area`, `iscrowd` บนภาพ `original_oriented` หรือบน Canvas ถ้าส่ง `layout`; `TorchvisionKeycaps(items)` เป็น Dataset สำหรับ Detection models ของ Torchvision (import torch เมื่อใช้งานเท่านั้น)
- ย้อนกลับ: `canvas_box_to_original(H, box)` คืน Polygon 4 มุมบนภาพต้นฉบับ (Spec §7.2)

## 12. Pilot report (P1.C–P1.D)

`CUDA_VISIBLE_DEVICES="" python -m ai.evaluation.pilot --root <pilot_root> --out <dir> [--rec-model PP-OCRv5_server_rec] [--ppu 96] [--crop-mode key_full]`

ใช้ไฟล์รูปแบบเดียวกับข้อ 3–7 (ภาพ Pilot ต้องมีจุดอ้างอิง + `slots.csv`; COCO ไม่บังคับแต่ควรมี) แล้วรันสองแบบ:

| โหมด | Crop จาก | วัดอะไร |
| --- | --- | --- |
| `manual` | กรอบคีย์แคปที่ Annotate (แปลงไป Canvas) | Character accuracy ของ OCR บน Crop ที่ถูกต้อง (แยกโมดูล, Spec §9.1) |
| `fixed` | Fixed layout crop (Baseline, Spec §6.4) | สิ่งที่ Pipeline อ่านได้จริง |

ความผิดพลาดของ `fixed` ถูกแยกเป็น: `geometry` (กึ่งกลางปุ่มจริงคลาดจากช่องใน Generic layout เกิน tol = `gating_u` ของ Layout) · `crop` (คลาดไม่เกิน tol แต่ Crop จากกรอบจริงอ่านถูก → ปรับ Crop mode/ขนาด) · `ocr_wrong` (อ่านเป็นตัวอื่น) · `ocr_reject` (อ่านไม่ออก/คะแนน < `--ocr-score-min`/ไม่ใช่ A–Z ตัวเดียว) รายงานแยก **รายคีย์บอร์ด** และ **ตาม `legend_style`** (`en_only` vs `th_en`) พร้อมตัวอักษรที่สับสนบ่อย และ **Generic-layout fit residual ต่อคีย์บอร์ด** (mean/p90/max ของระยะคลาด, สัดส่วนที่เกิน tol, ช่องที่คลาดมากสุด — แผน 1.A) ผลลัพธ์: `pilot_report.md`, `pilot_report.json`, `pilot_slots.csv`

ตัวอ่านเป็นแบบ Inject ได้ (`read_labels(crops) -> [(label|None, score, raw)]` เหมือน `PaddleReader`) — ในเทสต์ใช้ตัวอ่านจำลอง รายงานให้เฉพาะตัวเลข การตัดสินใจ Gate G1 ยังเป็นของผู้ทำโครงงาน

> **ข้อควรระวังเครื่องที่ฝึกโมเดลอยู่:** รัน OCR จริงด้วย `nice -n 19` และ `CUDA_VISIBLE_DEVICES=""` ทีละ Process

## 13. ลำดับการใช้งานเมื่อมีภาพจริง

1. `init` → กรอก `keyboards.csv` (ล็อก `role` ตาม D10) → `schedule --keyboards …`
2. ถ่ายภาพตาม `arrangements.csv` → กรอก `images.csv` (รวมจุดอ้างอิง 4 จุด) → `prefill-slots` → ตรวจ `slots.csv` กับภาพแล้วเปลี่ยนเป็น `verified`
3. Annotate กรอบใน CVAT/Label Studio → Export COCO เป็น `annotations/keycaps_coco.json`
4. `manifest` → ดูคู่ภาพซ้ำ → `split --seed … --write-csv` → `validate` จนไม่มี error
5. คัดลอก `manifest.json`, `split_manifest.json`, `keyboards.csv`, `arrangements.csv` ไป `data/manifests/<dataset_version>/` แล้ว Commit (ล็อก Test)
6. `to-yolo` สำหรับฝึก Detector; ห้ามแตะ Test จนถึง Phase 8

ทดลองทั้งเส้นทางโดยไม่ต้องมีภาพจริง: `python -m ai.data.keyboard_dataset demo --out <dir>` (สร้างข้อมูลจำลอง → manifest → split → validate → YOLO → pilot ด้วย OCR จำลอง)
