# Scripts

สคริปต์ในโฟลเดอร์นี้ใช้สำหรับรันแอปและงานดูแลระบบพื้นฐาน ส่วนการสร้าง module ใหม่ให้ใช้ Forge CLI แทน

## การรันแอป

```bash
# Development mode พร้อม auto-reload
./scripts/run-dev

# Production mode
./scripts/run-prod

# Worker process
./scripts/run-worker

# Controller process
./scripts/run-controller
```

## การสร้าง Module

ใช้คำสั่ง `forge generate` จาก root directory ของโปรเจกต์:

```bash
poetry run forge generate products
```

คำสั่งนี้จะสร้างไฟล์ใน `apiapp/modules/products/`:

- `__init__.py`
- `model.py` - SQLModel Model
- `schemas.py` - Pydantic schemas (DTOs)
- `use_case.py` - Business Logic และ Data Access ผ่าน SQLModel
- `router.py` - API endpoints

## โครงสร้าง Module

### Model

- SQLModel Model
- PostgreSQL table/index settings
- Indexes configuration

### Schemas (DTOs)

- `{Feature}Base` - base schema with common fields
- `Create{Feature}` - request schema สำหรับสร้างข้อมูล
- `Update{Feature}` - request schema สำหรับแก้ไขข้อมูล
- `{Feature}Response` - response schema

### Use Case

- Business logic
- Validation
- CRUD พื้นฐานผ่าน `BaseUseCase`
- Custom query methods ผ่าน SQLModel โดยตรง
- Dependency injection provider

### Router

- REST API endpoints (GET, POST, PUT, DELETE)
- Authentication dependencies ตามที่ module ต้องการ
- Proper HTTP status codes
- Error handling

## หลังจากสร้าง Module

1. **ปรับแต่งไฟล์ตามความต้องการ**

   - แก้ไข fields ใน `model.py` และ `schemas.py`
   - เพิ่ม business logic ใน `use_case.py`
   - ปรับแต่ง API endpoints ใน `router.py`

2. **ระบบจะทำการโหลด SQLModel Model และ Router อัตโนมัติ**

   - **Model:** ระบบจะทำการสแกนหาและโหลด SQLModel models ทั้งหมดจากทุก module มารันโดยอัตโนมัติผ่านฟังก์ชัน `_gather_models` ใน [database.py](../apiapp/infrastructure/database.py)
   - **Router:** ระบบจะทำการค้นหา Router ทั้งหมดและเพิ่มเข้าสู่ระบบโดยอัตโนมัติ ไม่จำเป็นต้องลงทะเบียนเอง

## ข้อกำหนด

- รันจาก root directory ของโปรเจกต์
- Python 3.12+
- โปรเจกต์ต้องมี `apiapp` directory
