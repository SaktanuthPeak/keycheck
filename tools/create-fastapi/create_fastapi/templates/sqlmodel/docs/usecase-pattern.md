# 📚 Use Case Pattern

## 🎯 ภาพรวม

Use Case Pattern เป็นใจความหลักส่วนสำคัญของ Clean Architecture ในโปรเจกต์นี้ ที่ช่วยรวบรวม Business Logic และการเข้าถึงข้อมูลผ่าน SQLModel ไว้ด้วยกัน ทำให้โค้ดดูแลง่าย โฟลว์การทำงานกระชับขึ้นและใช้ความสามารถของ SQLModel (PostgreSQL) ระดับ Model ได้เต็มความสามารถ

## 🏗️ โครงสร้างของ Pattern

```
modules/{feature}/
├── model.py        # Database BaseSQLModel (SQLModel) - โครงสร้างตารางต่างๆ
├── use_case.py     # Business Logic & SQLModel Data Access - ประมวลผลและต่อ DB
└── router.py       # Presentation Layer - รับ/ส่งข้อมูลผ่าน API
```

## 📊 Data Access ผ่าน SQLModel โดยตรง

### 🎯 ใช้ Active Record ของ SQLModel

SQLModel นำเสนอ Active Record Pattern ในตัวผ่านคลาส `BaseSQLModel` โปรเจกต์นี้จึงให้ **Use Case** เข้าถึงข้อมูลผ่าน SQLModel ได้โดยตรง:

- **รวบรัดโค้ดลง ลดความซ้ำซ้อน**
- **ได้ Type Safety สูงสุดจาก SQLModel Operators ทันที**
- **ไม่ต้องเขียน boilerplate methods ซ้ำไปมา**

### 🔧 ตัวอย่างการใช้งาน BaseUseCase สำหรับ CRUD พื้นฐาน

โปรเจกต์นี้มี `BaseUseCase` ที่ห่อหุ้มฟังก์ชัน CRUD พื้นฐานมาให้แล้ว:

```python
from apiapp.core.base_use_case import BaseUseCase
from typing import Optional
from fastapi_pagination import Page
from sqlmodel import And, Or
from .model import User
from .schemas import CreateUser, UpdateUser, UserResponse

class UserUseCase(BaseUseCase[User, CreateUser, UpdateUser, UserResponse]):
    model = User
    response_schema = UserResponse
    
    # สืบทอดฟังก์ชันพื้นฐานจาก BaseUseCase ให้ทันที:
    # - create(data)
    # - get_by_id(id)
    # - get_list()
    # - update(id, data)
    # - delete(id)
    
    # เพิ่มฟังก์ชันเฉพาะ Business หรือ Custom Queries
    async def get_by_email(self, email: str) -> Optional[User]:
        """หาผู้ใช้จาก email"""
        from sqlmodel import select
        statement = select(self.model).where(self.model.email == email)
        result = await self.session.exec(statement)
        return result.first()
    
    async def get_active_users(self) -> Page[UserResponse]:
        """หาผู้ใช้ที่ active เท่านั้น"""
        from sqlmodel import select
        from fastapi_pagination.ext.sqlalchemy import paginate
        
        query = select(self.model).where(
            self.model.is_active == True
        ).order_by(self.model.created_at.desc())
        
        return await paginate(self.session, query, transformer=self._page_to_response_transformer)
```

### 🔍 Query Patterns

#### 1. SQLModel SELECT Query (แนะนำ) ⭐

ใช้ `select` และ `where` ของ SQLModel สำหรับดึงข้อมูลและกรองข้อมูล:

```python
from sqlmodel import select, or_, and_

# 1. การกรองแบบง่าย (Simple Filter)
statement = select(self.model).where(self.model.age > 18)
results = await self.session.exec(statement)
adults = results.all()

# 2. การกรองหลายเงื่อนไข (Multiple AND Conditions)
# สามารถใช้ where() หลายค่า หรือ comma (,) เพื่อทำ AND query
statement = select(self.model).where(
    self.model.age >= 18,
    self.model.status == "active"
)
results = await self.session.exec(statement)
active_adults = results.all()

# 3. การกรองเงื่อนไขแบบ OR
statement = select(self.model).where(
    or_(
        self.model.role == "admin", 
        self.model.role == "premium"
    )
)
results = await self.session.exec(statement)
vip_users = results.all()

# 4. การกรองหลายค่าด้วย IN
statement = select(self.model).where(
    self.model.role.in_(["admin", "premium"])
)
results = await self.session.exec(statement)
```

### 📄 Pagination (SQLModel + FastAPI-Pagination)

```python
from sqlmodel import select
from fastapi_pagination.ext.sqlalchemy import paginate

# สร้าง Query ด้วย SQLModel select แบบปกติ
query = select(self.model).where(
    self.model.is_active == True,
).order_by(self.model.created_at.desc())

# เข้าสู่การ Paginate และแปลงผลลัพธ์ด้วย transformer
return await paginate(
    self.session, 
    query, 
    transformer=self._page_to_response_transformer
)
```

## 💼 Use Case Pattern

### 🎯 หน้าที่ของ Use Case

Use Case เป็นชั้นที่รับผิดชอบ Business Logic โดย:

- **ประมวลผลตามกฎธุรกิจ**
- **ควบคุม Transaction และ Data Consistency**
- **จัดการ Error Handling**
- **ทำหน้าที่เป็นตัวกลางระหว่าง Router และ SQLModel**

### 🔧 BaseUseCase

```python
from apiapp.core.base_use_case import BaseUseCase
from apiapp.core.exceptions import BusinessLogicError
from typing import Optional, Dict, Any
from fastapi_pagination import Page

class UserUseCase(BaseUseCase[User, CreateUser, UpdateUser, UserResponse]):
    model = User
    response_schema = UserResponse
    
    # สืบทอดฟังก์ชันพื้นฐานจาก BaseUseCase ให้ทันที:
    # - create(data)
    # - get_by_id(id)
    # - get_list()
    # - update(id, data)
    # - delete(id)
    
    async def register_user(self, user_data: Dict[str, Any]) -> UserResponse:
        """สมัครสมาชิกใหม่ พร้อม business logic"""
        
        # ตรวจสอบว่า email ซ้ำหรือไม่
        from sqlmodel import select
        statement = select(self.model).where(self.model.email == user_data["email"])
        result = await self.session.exec(statement)
        if result.first():
            raise BusinessLogicError("Email already registered")
        
        # เข้ารหัสรหัสผ่าน
        user_data["password"] = hash_password(user_data["password"])
        
        # บันทึกข้อมูลผ่านความสามารถ BaseUseCase
        return await self.create(CreateUser(**user_data))
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """เปลี่ยนรหัสผ่าน พร้อมตรวจสอบรหัสเก่า"""
        
        user = await self.get_by_id(user_id)
        if not user:
            raise BusinessLogicError("User not found")
        
        # ตรวจสอบรหัสผ่านเก่า
        if not verify_password(old_password, user.password):
            raise BusinessLogicError("Invalid old password")
        
        # เปลี่ยนรหัสผ่านใหม่
        hashed_password = hash_password(new_password)
        await self.update(user_id, UpdateUser(password=hashed_password))
        
        return True
    
    async def get_user_profile(self, user_id: str) -> Optional[UserResponse]:
        """ดูโปรไฟล์ผู้ใช้"""
        return await self.get_by_id(user_id)
    
    async def search_users(self, query: str) -> Page[UserResponse]:
        """ค้นหาผู้ใช้ตามคำค้น"""
        if len(query.strip()) < 2:
            raise BusinessLogicError("Search query must be at least 2 characters")
        
        from sqlmodel import select, or_
        from fastapi_pagination.ext.sqlalchemy import paginate
        
        # ค้นหาด้วย SQL ILIKE query ผ่าน session
        search_query = select(self.model).where(
            or_(
                self.model.full_name.ilike(f"%{query}%"),
                self.model.email.ilike(f"%{query}%")
            )
        )
        
        return await paginate(self.session, search_query, transformer=self._page_to_response_transformer)
```

## 🔗 การใช้งานใน Router

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegisterRequest,
    user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """สมัครสมาชิกใหม่"""
    try:
        user = await user_use_case.register_user(user_data.model_dump())
        return user
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search", response_model=Page[UserResponse])
async def search_users(
    q: str,
    page: int = 1,
    size: int = 20,
    user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """ค้นหาผู้ใช้"""
    try:
        return await user_use_case.search_users(q, page, size)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """ดูโปรไฟล์ตัวเอง"""
    return await user_use_case.get_user_profile(current_user.id)
```

## 🎯 หลักการสำคัญ

### ✅ DO - สิ่งที่ควรทำ

1. **ทำ Data Access ผ่าน session ภายใน Use Case ได้เลย**
   ```python
   # ✅ ถูกต้อง
   async def find_active_users(self) -> Page[UserResponse]:
       query = select(self.model).where(self.model.is_active == True)
       return await paginate(self.session, query, transformer=self._page_to_response_transformer)
   ```

2. **ใส่ Business Logic เข้ากับ Data Validation**
   ```python
   # ✅ ถูกต้อง
   async def deactivate_user(self, user_id: str) -> bool:
       user = await self.get_by_id(user_id)
       if not user:
           raise BusinessLogicError("User not found")
       if user.role == "admin":
           raise BusinessLogicError("Cannot deactivate admin user")
       return await self.update(user_id, UpdateUser(is_active=False))
   ```

3. **ใช้ SQLModel/SQLAlchemy Expressions เสมอ**
   ```python
   # ✅ ถูกต้อง
   statement = select(self.model).where(
       self.model.age >= 18, 
       self.model.status == "active"
   )
   result = await self.session.exec(statement)
   return result.all()
   ```

### ❌ DON'T - สิ่งที่ไม่ควรทำ

1. **ไม่เขียน Endpoint หนาๆ ใน Router**
   ```python
   # ❌ ผิด
   @router.post("/users")
   async def register_user(user_data: Dict):
       if user_data["age"] < 18:  # Business logic ทะลุมาที่ Router!
           raise ValueError("User must be 18+")
       user = User(**user_data)
       session.add(user)
       await session.commit()
       return user
   ```

2. **ไม่เรียกใช้งาน Database/Model โดยตรงใน Router อย่างเด็ดขาด!**
   ```python
   # ❌ ผิด
   @router.get("/users")
   async def get_users():
       # ข้าม Use Case ไปเรียก DB ตรงๆ
       statement = select(User)
       result = await session.exec(statement)
       return result.all()
   ```

3. **ไม่ใช้ Raw SQL Queries หรือ dictionary-based filtering แบบ NoSQL**
   ```python
   # ❌ ผิด - ห้ามใช้ MongoDB query style
   # users = await self.model.find({"age": {"$gte": 18}}).to_list()
   
   # ✅ ถูกต้อง - ใช้ SQLModel select
   statement = select(self.model).where(self.model.age >= 18)
   ```

## 🧪 การทดสอบ

### Use Case Testing

การสืบทอด SQLModel มาใน Use Case ทำให้จำเป็นต้อง Mock ตัว Database ตรงๆ (ผ่าน mock object)

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from apiapp.modules.user.use_case import UserUseCase
from apiapp.core.exceptions import BusinessLogicError

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def user_use_case(mock_session):
    return UserUseCase(session=mock_session)

async def test_register_user_duplicate_email(user_use_case, mock_session):
    # Setup mock for self.session.exec
    mock_result = MagicMock()
    mock_result.first.return_value = MagicMock()  # Mock that email exists
    mock_session.exec.return_value = mock_result
    
    # Test
    with pytest.raises(BusinessLogicError, match="Email already registered"):
        await user_use_case.register_user({"email": "test@example.com"})
```

## 📊 ตัวอย่างการใช้งานจริง

### E-commerce Product Module

```python
# use_case.py
class ProductUseCase(BaseUseCase[Product, CreateProduct, UpdateProduct, ProductResponse]):
    model = Product
    response_schema = ProductResponse
    
    async def create_product(self, product_data: CreateProduct) -> ProductResponse:
        # Business validation
        if product_data.price <= 0:
            raise BusinessLogicError("Price must be positive")
        
        # Auto-generate SKU
        sku = generate_sku(product_data.name)
        
        # บันทึกข้อมูลผ่านความสามารถ BaseUseCase
        return await self.create(product_data)
    
    async def apply_discount(self, product_id: str, discount_percent: float) -> ProductResponse:
        if discount_percent < 0 or discount_percent > 50:
            raise BusinessLogicError("Discount must be between 0-50%")
        
        product = await self.get_by_id(product_id)
        if not product:
            raise BusinessLogicError("Product not found")
        
        new_price = product.price * (1 - discount_percent / 100)
        return await self.update(product_id, UpdateProduct(price=new_price))
    
    async def find_in_price_range(self, min_price: float, max_price: float) -> Page[ProductResponse]:
        query = select(self.model).where(
            self.model.price >= min_price,
            self.model.price <= max_price
        )
        return await paginate(self.session, query, transformer=self._page_to_response_transformer)
```

## 🔧 การปรับแต่งขั้นสูง

### Custom Collection Methods (Aggregation)

```python
class OrderUseCase(BaseUseCase[Order, CreateOrder, UpdateOrder, OrderResponse]):
    model = Order
    ...
    
    async def get_revenue_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        # ใช้ PostgreSQL aggregation สำหรับการคำนวณที่ซับซ้อน
        from sqlmodel import select, func
        
        statement = select(
            func.sum(self.model.total_amount).label("total_revenue"),
            func.count(self.model.id).label("order_count"),
            func.avg(self.model.total_amount).label("avg_order_value")
        ).where(
            self.model.status == "completed",
            self.model.created_at >= start_date,
            self.model.created_at <= end_date
        )
        
        result = await self.session.exec(statement)
        row = result.first()
        return {
            "total_revenue": row.total_revenue or 0,
            "order_count": row.order_count or 0,
            "avg_order_value": float(row.avg_order_value or 0)
        }
```

## 🚀 สรุป

Use Case Pattern ที่ทำงานร่วมกับ SQLModel โดยตรงช่วยให้:

- **โค้ดกระชับขึ้น** - ควบคุม Logic ฝั่งธุรกิจและ Data ในไฟล์เดียวกัน
- **ง่ายต่อการทดสอบ** - ไม่ต้องสร้าง Mock Service มากมาย
- **ลด Overhead ตัวระบบ** - ไม่มี Boilerplate Methods ให้รุงรัง
- **พัฒนาได้ไว** - ลดเวลามาปรับแก้ Type 
- **Type Safety สูงสุด** - ควบคุมข้อมูลด้วย SQLModel และ Pydantic รุ่นล่าสุด

การเรียนรู้ Pattern โดยการรวม Use Case เข้ากับ SQLModel Database Model จะทำให้โปรเจกต์คุณพัฒนาได้เร็วและเป็นระบบมากขึ้น! 🎯
