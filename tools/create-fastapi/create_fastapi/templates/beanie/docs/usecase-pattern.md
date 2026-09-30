# 📚 Use Case Pattern

## 🎯 ภาพรวม

Use Case Pattern เป็นใจความหลักส่วนสำคัญของ Clean Architecture ในโปรเจกต์นี้ ที่ช่วยรวบรวม Business Logic และการเข้าถึงข้อมูลผ่าน Beanie Document ไว้ด้วยกัน ทำให้โค้ดดูแลง่าย โฟลว์การทำงานกระชับขึ้นและใช้ความสามารถของ Beanie ODM (MongoDB) ระดับ Model ได้เต็มความสามารถ

## 🏗️ โครงสร้างของ Pattern

```
modules/{feature}/
├── model.py        # Database Document (Beanie) - โครงสร้างตารางต่างๆ
├── use_case.py     # Business Logic & Beanie Data Access - ประมวลผลและต่อ DB
└── router.py       # Presentation Layer - รับ/ส่งข้อมูลผ่าน API
```

## 📊 Data Access ผ่าน Beanie Document โดยตรง

### 🎯 ใช้ Active Record ของ Beanie

Beanie ODM นำเสนอ Active Record Pattern ในตัวผ่านคลาส `Document` โปรเจกต์นี้จึงให้ **Use Case** เข้าถึงข้อมูลผ่าน Beanie Document ได้โดยตรง:

- **รวบรัดโค้ดลง ลดความซ้ำซ้อน**
- **ได้ Type Safety สูงสุดจาก Beanie Operators ทันที**
- **ไม่ต้องเขียน boilerplate methods ซ้ำไปมา**

### 🔧 ตัวอย่างการใช้งาน BaseUseCase สำหรับ CRUD พื้นฐาน

โปรเจกต์นี้มี `BaseUseCase` ที่ห่อหุ้มฟังก์ชัน CRUD พื้นฐานมาให้แล้ว:

```python
from apiapp.core.base_use_case import BaseUseCase
from typing import Optional
from fastapi_pagination import Page
from beanie.operators import And, Or
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
        """หาผู้ใช้จาก email: Query ผ่าน Model ตรงๆ ได้เลย"""
        return await self.model.find_one({"email": email})
    
    async def get_active_users(self) -> Page[UserResponse]:
        """หาผู้ใช้ที่ active เท่านั้น"""
        query = self.model.find(
            self.model.is_active == True,  # Beanie operators
        ).sort("-created_at")
        
        from fastapi_pagination.ext.beanie import paginate
        page = await paginate(query)
        return self._page_to_response(page)
```

### 🔍 Query Patterns

#### 1. PyMongo Style (ใช้ได้แต่ไม่แนะนำ)

```python
# ❌ PyMongo style - ไม่มี type safety บางครั้ง
users = await self.model.find({
    "age": {"$gt": 18},
    "status": "active"
}).to_list()
```

#### 2. Beanie Operators (แนะนำ) ⭐

```python
# ✅ Beanie operators - มี type safety และอ่านง่าย
from beanie.operators import And, Or, In, RegEx

# การกรองแบบง่าย
adults = await self.model.find(self.model.age > 18).to_list()

# การกรองแบบซับซ้อน
active_adults = await self.model.find(
    And(self.model.age >= 18, self.model.status == "active")
).to_list()

# การค้นหาด้วย regex
users = await self.model.find(
    RegEx(self.model.name, "john", "i")  # case-insensitive
).to_list()

# การกรองหลายค่า
vip_users = await self.model.find(
    In(self.model.role, ["admin", "premium"])
).to_list()

# การรวมเงื่อนไข
result = await self.model.find(
    Or(
        And(self.model.role == "admin", self.model.is_active == True),
        And(self.model.role == "premium", self.model.credits > 100)
    )
).to_list()
```

### 📄 Pagination (Beanie + FastAPI-Pagination)

```python
from fastapi_pagination.ext.beanie import paginate

# สร้าง Query ด้วย Beanie Pattern แบบปกติ
query = self.model.find(
    self.model.is_active == True,
).sort("-created_at")

# เข้าสู่การ Paginate (ผลลัพธ์เป็น Page object สำเร็จรูป)
page = await paginate(query)

# แปลงผลลัพธ์เป็น ResponseSchemaType
return self._page_to_response(page)
```

## 💼 Use Case Pattern

### 🎯 หน้าที่ของ Use Case

Use Case เป็นชั้นที่รับผิดชอบ Business Logic โดย:

- **ประมวลผลตามกฎธุรกิจ**
- **ควบคุม Transaction และ Data Consistency**
- **จัดการ Error Handling**
- **ทำหน้าที่เป็นตัวกลางระหว่าง Router และ Beanie Document**

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
        existing_user = await self.model.find_one({"email": user_data["email"]})
        if existing_user:
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
        await self.update(user_id, {"password": hashed_password})
        
        return True
    
    async def get_user_profile(self, user_id: str) -> Optional[User]:
        """ดูโปรไฟล์ผู้ใช้ พร้อม linked documents"""
        return await self.get_by_id(user_id, fetch_links=True)
    
    async def search_users(self, query: str, page: int = 1, size: int = 20) -> Page[UserResponse]:
        """ค้นหาผู้ใช้ตามคำค้น"""
        if len(query.strip()) < 2:
            raise BusinessLogicError("Search query must be at least 2 characters")
        
        from beanie.operators import Or, RegEx
        from fastapi_pagination.ext.beanie import paginate
        
        # ค้นหาด้วย Regex ผ่าน Model ตรงๆ
        search_query = self.model.find(
            Or(
                RegEx(self.model.full_name, query, "i"),
                RegEx(self.model.email, query, "i")
            )
        )
        
        page = await paginate(search_query)
        return self._page_to_response(page)
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

1. **ใช้ Data Access ภายใน Use Case ได้เลย**
   ```python
   # ✅ ถูกต้อง
   async def find_active_users(self) -> Page[UserResponse]:
       return await self._page_to_response(
           await paginate(self.model.find(self.model.is_active == True))
       )
   ```

2. **ใส่ Business Logic เข้ากับ Data Validation**
   ```python
   # ✅ ถูกต้อง
   async def deactivate_user(self, user_id: str) -> bool:
       user = await self.get_by_id(user_id)
       if user.role == "admin":
           raise BusinessLogicError("Cannot deactivate admin user")
       return await self.update(user_id, {"is_active": False})
   ```

3. **ใช้ Beanie Operators สำหรับ Type Safety เสมอ**
   ```python
   # ✅ ถูกต้อง
   return await self.model.find(
       And(self.model.age >= 18, self.model.status == "active")
   ).to_list()
   ```

4. **ระวังการใช้งาน `.to_list()`**
   ```python
   # ใช้ .to_list() เมื่อผลลัพธ์มีจำนวนน้อยและแน่นอน
   user_list = await self.model.find_all().to_list()
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
       await user.insert()
       return user
   ```

2. **ไม่เข้าถึง Model โดยตรงใน Router อย่างเด็ดขาด!**
   ```python
   # ❌ ผิด
   @router.get("/users")
   async def get_users():
       # ข้าม Use Case ไปเรียก DB ตรงๆ
       return await User.find_all().to_list()  
   ```

3. **ไม่ใช้ Raw MongoDB Queries โดยไม่จำเป็น**
   ```python
   # ❌ ผิด - ไม่มี type safety
   users = await self.model.find({"age": {"$gte": 18}}).to_list()
   
   # ✅ ถูกต้อง - มี type safety
   users = await self.model.find(self.model.age >= 18).to_list()
   ```

## 🧪 การทดสอบ

### Use Case Testing

การสืบทอด Beanie มาใน Use Case ทำให้จำเป็นต้อง Mock ตัว Database ตรงๆ (ผ่าน mock object)

```python
import pytest
from unittest.mock import AsyncMock, patch
from apiapp.modules.user.use_case import UserUseCase
from apiapp.core.exceptions import BusinessLogicError

@pytest.fixture
def user_use_case():
    return UserUseCase()

@patch('apiapp.modules.user.model.User.find_one')
async def test_register_user_duplicate_email(mock_find_one, user_use_case):
    # Setup mock
    mock_find_one.return_value = AsyncMock() # Mock ว่าดึงค่า existing_user มาได้
    
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
    
    async def create_product(self, product_data: Dict[str, Any]) -> ProductResponse:
        # Business validation
        if product_data["price"] <= 0:
            raise BusinessLogicError("Price must be positive")
        
        # Auto-generate SKU
        product_data["sku"] = generate_sku(product_data["name"])
        product_data["created_at"] = datetime.utcnow()
        
        return await self.create(CreateProduct(**product_data))
    
    async def apply_discount(self, product_id: str, discount_percent: float) -> ProductResponse:
        if discount_percent < 0 or discount_percent > 50:
            raise BusinessLogicError("Discount must be between 0-50%")
        
        product = await self.get_by_id(product_id)
        if not product:
            raise BusinessLogicError("Product not found")
        
        new_price = product.price * (1 - discount_percent / 100)
        return await self.update(product_id, UpdateProduct(price=new_price))
    
    async def find_in_price_range(self, min_price: float, max_price: float) -> Page[ProductResponse]:
        query = self.model.find(
            And(self.model.price >= min_price, self.model.price <= max_price)
        )
        page = await paginate(query)
        return self._page_to_response(page)
```

## 🔧 การปรับแต่งขั้นสูง

### Custom Collection Methods (Aggregation)

```python
class OrderUseCase(BaseUseCase[Order, CreateOrder, UpdateOrder, OrderResponse]):
    model = Order
    ...
    
    async def get_revenue_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        # ใช้ MongoDB aggregation สำหรับการคำนวณที่ซับซ้อน
        pipeline = [
            {"$match": {
                "status": "completed",
                "created_at": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_amount"},
                "order_count": {"$sum": 1},
                "avg_order_value": {"$avg": "$total_amount"}
            }}
        ]
        
        result = await self.model.aggregate(pipeline).to_list()
        return result[0] if result else {"total_revenue": 0, "order_count": 0, "avg_order_value": 0}
```

## 🚀 สรุป

Use Case Pattern ที่ทำงานร่วมกับ Beanie Document โดยตรงช่วยให้:

- **โค้ดกระชับขึ้น** - ควบคุม Logic ฝั่งธุรกิจและ Data ในไฟล์เดียวกัน
- **ง่ายต่อการทดสอบ** - ไม่ต้องสร้าง Mock Service มากมาย
- **ลด Overhead ตัวระบบ** - ไม่มี Boilerplate Methods ให้รุงรัง
- **พัฒนาได้ไว** - ลดเวลามาปรับแก้ Type 
- **Type Safety สูงสุด** - ควบคุมข้อมูลด้วย Beanie และ Pydantic รุ่นล่าสุด

การเรียนรู้ Pattern โดยการรวม Use Case เข้ากับ Beanie Database Model จะทำให้โปรเจกต์คุณพัฒนาได้เร็วและเป็นระบบมากขึ้น! 🎯
