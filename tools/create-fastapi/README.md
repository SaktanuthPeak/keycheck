# 🚀 Create FastAPI Starter CLI

เครื่องมือ CLI อัตโนมัติสำหรับการ Bootstrap โปรเจกต์ **FastAPI ระดับ Production** ที่ออกแบบตามแนวทาง **Vertical Slice Architecture + Pragmatic Clean Architecture** รองรับทั้ง **PostgreSQL (SQLModel)** และ **MongoDB (Beanie)** พร้อมระบบจัดการแพ็กเกจสมัยใหม่ด้วย **`uv`**

---

## ✨ คุณสมบัติเด่น

- 🎯 **Interactive CLI** - เลือกระบบฐานข้อมูลและฟีเจอร์ที่ต้องการผ่าน Interactive Menu ใน Terminal
- 🗄️ **Dual Database Architecture**:
  - 🐘 **PostgreSQL**: SQLModel + SQLAlchemy AsyncSession + Alembic Migrations + AsyncPG
  - 🍃 **MongoDB**: Beanie ODM + PyMongo Async + Active Record Pattern
- ⚡ **Powered by `uv`** - Package Management ที่เร็วที่สุดในยุคนี้ พร้อมโครงสร้างมาตรฐาน PEP 621
- 🔐 **Enterprise Auth** - JWT Access Token + HTTP-Only Refresh Cookie Strategy + Role-Based Authorization
- ⚙️ **Background Worker** - Asynchronous task queue ด้วย `arq` + Redis
- ⚡ **Auto Router & Model Discovery** - สแกนหาโมดูลและเราเตอร์อัตโนมัติ ไม่ต้องคอย import เพิ่มใน `main.py`
- 🛠️ **Fast CLI Scaffolder** - คำสั่งสร้างโมดูลใหม่อัตโนมัติ (`uv run fast generate <name>`)
- 🐳 **Multi-Stage Dockerfile** - พร้อมใช้งานสำหรับการ Deploy ขึ้น Cloud และ Kubernetes

---

## 🚀 เริ่มต้นใช้งาน

### 1. วิธีใช้งานทันที (แนะนำ)

ใช้ผ่าน `uvx` (รันได้ทันทีโดยไม่ต้องติดตั้งล่วงหน้า):

```bash
# รัน interactive mode (pin เวอร์ชัน)
uvx --from git+https://github.com/importstar/create-fastapi.git@v0.2.0 create-fastapi

# หรือระบุชื่อโปรเจกต์
uvx --from git+https://github.com/importstar/create-fastapi.git@v0.2.0 create-fastapi my-api-service
```

หรือติดตั้งผ่าน `pipx` / `pip`:

```bash
pipx install git+https://github.com/importstar/create-fastapi.git@v0.2.0
# หรือ
pip install git+https://github.com/importstar/create-fastapi.git@v0.2.0

# จากนั้นเรียกใช้ได้ทุกที่ในเครื่อง
create-fastapi my-api-service
create-fastapi --version
```

### 2. ใช้งานในโหมด Local Development (ภายใน Repo นี้)

```bash
# ติดตั้ง dependencies ของ CLI
uv sync

# รันคำสั่งสร้างโปรเจกต์
uv run create-fastapi my-new-app

# ตรวจเวอร์ชัน
uv run create-fastapi --version
```

---

## 📋 ตัวเลือกคำสั่ง (CLI Options)

นอกจากโหมดถาม-ตอบ (Interactive) คุณสามารถส่ง Flags เพื่อสร้างโปรเจกต์อัตโนมัติใน CI/CD หรือ Script ได้:

```bash
# สร้างโปรเจกต์ PostgreSQL แบบสมบูรณ์
uv run create-fastapi my-sql-app --db sqlmodel --worker --cookie-auth --examples

# สร้างโปรเจกต์ MongoDB แบบ Minimal Clean Core
uv run create-fastapi my-mongo-app --db beanie --no-worker --no-examples --git --install
```

### รายการ Flags ทั้งหมด:

| Flag | คำอธิบาย | ตัวเลือก / Default |
| :--- | :--- | :--- |
| `[PROJECT_NAME]` | ชื่อโปรเจกต์และโฟลเดอร์ปลายทาง | `my-fastapi-app` |
| `-d, --db` | ประเภทฐานข้อมูลและ ORM | `sqlmodel` (Postgres) หรือ `beanie` (MongoDB) |
| `--worker / --no-worker` | รวม Background Task Worker (`arq` + Redis) | `True` |
| `--cookie-auth / --no-cookie-auth` | เปิดใช้งาน HTTP-Only Cookie strategy | `True` |
| `--examples / --no-examples` | รวมตัวอย่างโมดูล CRUD (`pet`, `hospital`) | `False` |
| `-g, --git / --no-git` | ทำการ `git init` อัตโนมัติ | `True` |
| `-i, --install / --no-install` | สั่ง `uv sync` ติดตั้ง dependencies ทันที | `True` |

---

## 📁 โครงสร้างโปรเจกต์ที่ถูกสร้างขึ้น (Generated Structure)

```text
my-api-app/
├── Dockerfile                  # Multi-stage Docker build with uv
├── pyproject.toml              # PEP 621 dependencies (uv-first)
├── .env.sample / .env          # Environment configuration พร้อม auto-generated secret key
├── alembic.ini                 # (มีเฉพาะฝั่ง PostgreSQL)
├── migrations/                 # (มีเฉพาะฝั่ง PostgreSQL) Auto-detect models
│
├── apiapp/
│   ├── main.py / run.py        # Application Lifespan & Initialization
│   │
│   ├── core/                   # Shared Kernel
│   │   ├── base_use_case.py    # Generic CRUD BaseUseCase[Model, Create, Update, Response]
│   │   ├── base_schemas.py     # Base Pydantic Models & Mixins
│   │   ├── config.py           # Pydantic Settings
│   │   ├── security.py         # JWT Token & Password Hashing
│   │   └── router.py           # Auto Discovery Routers
│   │
│   ├── infrastructure/         # External Drivers
│   │   ├── database.py         # Database Connection (AsyncSession / Beanie)
│   │   └── file_storage.py     # File storage utility
│   │
│   ├── middlewares/            # CORS, Timing, Security middlewares
│   │
│   ├── worker/                 # Background Task Worker (arq)
│   │   ├── server.py           # WorkerSettings
│   │   └── tasks.py            # Async jobs
│   │
│   └── modules/                # Vertical Slices (Feature Modules)
│       ├── auth/               # Login, Register, Refresh Token
│       ├── health/             # Health check probe
│       └── user/               # User management (Model, UseCase, Router, Schemas)
│
├── cli/                        # Scaffolding Tool
│   └── main.py                 # Fast CLI: `uv run fast generate <module>`
│
└── scripts/                    # Development scripts (uv-ready)
    ├── run-dev                 # รัน Development mode (auto-reload)
    ├── run-prod                # รัน Production mode
    ├── run-worker              # รัน Background worker
    └── init-admin              # สร้าง Admin user แรก
```

---

## 🛠️ การพัฒนาต่อยอดในโปรเจกต์ที่สร้างแล้ว

### 1. รัน Server ในโหมด Development
```bash
./scripts/run-dev
```
- API Docs: `http://localhost:9000/docs`
- ReDoc: `http://localhost:9000/redoc`

### 2. สร้าง Module ใหม่ด้วย Fast CLI
ไม่ต้องเขียน Boilerplate เองทุกครั้ง ระบบจะสร้าง Model, Schemas, UseCase, และ Router ให้ทันที:
```bash
uv run fast generate product
```

### 3. รัน Database Migrations (เฉพาะ PostgreSQL)
```bash
# สร้าง Migration script ใหม่จากการเปลี่ยนแปลง model
uv run alembic revision --autogenerate -m "create new table"

# สั่งอัปเดต Database
uv run alembic upgrade head
```

---

## 📄 License
MIT License
