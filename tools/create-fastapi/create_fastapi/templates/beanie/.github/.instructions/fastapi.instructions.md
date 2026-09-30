# FastAPI Clean Architecture Project Instructions

## 📁 Project Structure Overview

This project follows **Clean Architecture** principles with **Domain-Driven Design (DDD)** patterns using FastAPI, Beanie (MongoDB), and modular structure.

### 🏗️ Architecture Layers

```
apiapp/
├── core/                    # Business Logic & Shared Components Layer
│   ├── __init__.py
│   ├── base_schemas.py      # Base Pydantic schemas
│   ├── base_use_case.py     # Base use case pattern (CRUD & DB access)
│   ├── config.py            # App configuration & settings
│   ├── exceptions.py        # Custom business exceptions
│   ├── http_error.py        # HTTP error handling
│   ├── router.py            # Base router configuration
│   ├── security.py          # JWT, password hashing
│   ├── validation_error.py  # Validation error handling
│   └── dependencies/        # Shared dependencies (auth, validation, etc.)
│       ├── __init__.py
│       └── auth.py          # Authentication dependencies
├── infrastructure/          # Infrastructure & External Services Layer
│   ├── __init__.py
│   ├── database.py          # MongoDB connection & Beanie setup
│   └── gridfs.py            # File storage
├── middlewares/             # FastAPI Middlewares
│   ├── __init__.py
│   ├── base.py              # init_all_middlewares function
│   ├── cors.py              # CORS & compression
│   ├── security.py          # User agent filtering
│   └── timing.py            # Performance timing
├── utils/                   # Utility Functions
│   ├── __init__.py
│   ├── logging.py           # Logging configuration
│   └── request_logs.py      # Request logging
├── cmd/                     # Command Line Interface Components
│   └── __init__.py
├── shares/                  # Shared Resources
└── modules/                 # Feature Modules (Clean Architecture)
    ├── __init__.py
    ├── auth/                # Authentication module
    │   ├── __init__.py
    │   └── schemas.py       # Auth schemas
    ├── user/                # User management module
    │   ├── __init__.py
    │   ├── model.py         # User database model
    │   ├── router.py        # User API endpoints
    │   ├── schemas.py       # User schemas
    │   └── use_case.py      # User business logic & data access
    ├── health/              # Health check module
    │   ├── __init__.py
    │   ├── router.py        # Health check endpoints
    │   └── schemas.py       # Health check schemas
    └── examples/            # Example module (for testing)
```

## 🎯 Core Principles

### 1. **Dependency Direction**

- **Modules** depend on **Core** (import from `apiapp.core.*`)
- **Core** does NOT depend on **Modules**
- **Infrastructure** implements interfaces defined in **Core**
- **Models** are now within each module for better organization

### 2. **Module Structure**

Each feature module MUST follow this exact pattern:

```
modules/{feature}/
├── __init__.py
├── model.py        # Database Model (Beanie Document)
├── schemas.py      # Pydantic schemas (DTOs)
├── use_case.py     # Business logic & Database Access
└── router.py       # API endpoints
```

### 3. **Dependency Injection Pattern**

- Use FastAPI's `Depends()` for ALL dependencies
- Create shared dependency providers in `core/dependencies/`
- Inject use cases and services through dependencies
- NO direct model querying in routers

## 📋 Coding Patterns & Guidelines

### **String Quotes Convention**

- **Use double quotes (`"`) as the primary string delimiter**
- Use single quotes (`'`) only when the string contains double quotes
- Be consistent within the same file/module

```python
# ✅ Good - Use double quotes
name = "John Doe"
message = "Welcome to our API"
sql_query = "SELECT * FROM users WHERE email = 'user@example.com'"

# ❌ Bad - Mixed quotes without reason
name = 'John Doe'
message = "Welcome to our API"
```

### **1. Model Pattern**

Each module should contain its own model file:

```python
# modules/{feature}/model.py
from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class {Model}(Document):
    """Database model for {feature}"""
    
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Settings:
        name = "{feature_plural}"  # Collection name in MongoDB
        indexes = [
            "name",
            "status", 
            "created_at"
        ]
```

### **2. Use Case Pattern (Business Logic + Data Access)**

```python
# modules/{feature}/use_case.py
from fastapi import Depends
from typing import Optional
from beanie import PydanticObjectId

from apiapp.core.base_use_case import BaseUseCase
from .model import {Model}
from .schemas import Create{Model}, Update{Model}, {Model}Response

class {Feature}UseCase(BaseUseCase[{Model}, Create{Model}, Update{Model}, {Model}Response]):
    model = {Model}
    response_schema = {Model}Response

    async def custom_action(self, data: Create{Model}) -> {Model}Response:
        """Business logic and Data Access combined"""
        # 1. Validate business rules
        if not self._validate_business_rules(data):
            raise ValidationError("Business rule violation")

        # 2. Database Action via Beanie directly
        doc = self.model(**data.model_dump())
        await doc.insert()
        return self._to_response(doc)

    def _validate_business_rules(self, data: Create{Model}) -> bool:
        """Private method for business validation"""
        return True

# Dependency providers
def get_{feature}_use_case() -> {Feature}UseCase:
    """Get {feature} use case instance"""
    return {Feature}UseCase()
```

### **4. Router Pattern**

```python
# modules/{feature}/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from apiapp.core.dependencies import get_current_active_user, RoleChecker
from apiapp.modules.user.model import User
from .use_case import get_{feature}_use_case, {Feature}UseCase
from .schemas import {Schema}Request, {Schema}Response

router = APIRouter(prefix="/v1/{feature}", tags=["{Feature}"])

# Use "" for root endpoint, NOT "/"
@router.get("", response_model=List[{Schema}Response])
async def list_{feature}(
    current_user: User = Depends(get_current_active_user),
    {feature}_use_case: {Feature}UseCase = Depends(get_{feature}_use_case)
):
    """List all {feature} items"""
    items = await {feature}_use_case.get_all()
    # If returned as objects, manually validate, or let FastAPI handle it if BaseUseCase returns Schemas
    return items

@router.post("", response_model={Schema}Response, status_code=status.HTTP_201_CREATED)
async def create_{feature}(
    data: {Schema}Request,
    current_user: User = Depends(get_current_active_user),
    {feature}_use_case: {Feature}UseCase = Depends(get_{feature}_use_case)
):
    """Create new {feature}"""
    try:
        return await {feature}_use_case.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{item_id}", response_model={Schema}Response)
async def get_{feature}(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    {feature}_use_case: {Feature}UseCase = Depends(get_{feature}_use_case)
):
    """Get {feature} by ID"""
    item = await {feature}_use_case.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="{Feature} not found")
    return item
```

### **5. Cross-Module Dependencies**

When a use case needs to call another module's use case:

```python
# modules/auth/use_case.py
from fastapi import Depends

from ..user.use_case import get_user_use_case, UserUseCase

class AuthUseCase:
    def __init__(
        self,
        user_use_case: UserUseCase
    ):
        self.user_use_case = user_use_case

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        """Login with user validation"""
        # Use another module's use case
        user = await self.user_use_case.get_by_email(credentials.email)

        # Auth-specific business logic
        if not verify_password(credentials.password, user.password):
            raise AuthenticationError("Invalid credentials")

        return await self._generate_tokens(user)


# Dependency providers
def get_auth_use_case(
    user_use_case: UserUseCase = Depends(get_user_use_case)
) -> AuthUseCase:
    """Get auth use case with user use case injection"""
    return AuthUseCase(
        user_use_case=user_use_case
    )
```

### **6. Schemas Pattern**

```python
# modules/{feature}/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from apiapp.core.base_schemas import BaseSchema

class {Schema}Base(BaseModel):
    """Base schema with common fields"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class {Schema}Request({Schema}Base):
    """Request schema for creating/updating"""
    pass

class {Schema}Response({Schema}Base, BaseSchema):
    """Response schema with additional fields"""
    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_entity(cls, entity) -> "{Schema}Response":
        """Convert entity to response schema"""
        return cls(
            id=str(entity.id),
            name=entity.name,
            description=entity.description,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
```

### **7. Pagination Pattern with fastapi_pagination**

This project uses **fastapi_pagination** library with **Beanie pagination** for consistent paginated responses.

```python
# modules/{feature}/use_case.py
from fastapi import Depends
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.beanie import paginate

from apiapp.core.base_use_case import BaseUseCase
from .model import {Model}
from .schemas import Create{Model}, Update{Model}, {Model}Response

class {Feature}UseCase(BaseUseCase[{Model}, Create{Model}, Update{Model}, {Model}Response]):
    model = {Model}
    response_schema = {Model}Response

    async def get_by_status_paginated(self, status: str) -> Page[{Model}Response]:
        """Get paginated list filtered by status"""
        query = self.model.find({"status": status})
        page = await paginate(query)
        
        # BaseUseCase helps transforming paginated models to response schemas
        return self._page_to_response(page)
```

```python
# modules/{feature}/router.py
from fastapi import APIRouter, Depends
from fastapi_pagination import Page, Params

from apiapp.core.dependencies import get_current_active_user
from apiapp.modules.user.model import User
from .use_case import get_{feature}_use_case, {Feature}UseCase
from .schemas import {Schema}Response

router = APIRouter(prefix="/v1/{feature}", tags=["{Feature}"])

@router.get("", response_model=Page[{Schema}Response])
async def list_{feature}(
    params: Params = Depends(),
    current_user: User = Depends(get_current_active_user),
    {feature}_use_case: {Feature}UseCase = Depends(get_{feature}_use_case)
):
    """Get paginated list of {feature} items"""
    return await {feature}_use_case.get_list()

@router.get("/by-status/{status}", response_model=Page[{Schema}Response])
async def list_{feature}_by_status(
    status: str,
    params: Params = Depends(),
    current_user: User = Depends(get_current_active_user),
    {feature}_use_case: {Feature}UseCase = Depends(get_{feature}_use_case)
):
    """Get paginated list filtered by status"""
    return await {feature}_use_case.get_by_status_paginated(status)
```

**Pagination Query Parameters:**

- `page`: Page number (default: 1)
- `size`: Items per page (default: 50, max: 100)

**Example API calls:**

```
GET /v1/users?page=1&size=20
GET /v1/users/by-status/active?page=2&size=10
```

**Response format:**

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "size": 20,
  "pages": 8
}
```

## 🔧 Essential Patterns

### **Error Handling**

```python
# Always use specific HTTP exceptions
from fastapi import HTTPException, status

# ✅ Good
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)

# ❌ Bad
raise Exception("Something went wrong")
```

### **Authentication & Authorization**

```python
# Use shared dependencies from core
from apiapp.core.dependencies import (
    get_current_active_user,
    RoleChecker
)

# Role-based access
require_admin = RoleChecker("admin")

@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    admin_user: User = Depends(require_admin)  # Only admin can delete
):
    pass
```

### **Database Operations**

```python
# Centralize Beanie logic inside the UseCase
# ✅ Good
item = await self.model.get(PydanticObjectId(item_id))
await item.delete()

# ❌ Bad (Doing DB operations inside the Router directly)
@router.delete("/{item_id}")
async def delete_item(item_id: str):
    item = await Item.get(item_id)
    await item.delete()
```

### **Response Models**

```python
# Always specify response_model
@router.get("", response_model=List[ItemResponse])
async def list_items():
    pass

@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item():
    pass
```

## 🚫 Anti-Patterns to Avoid

1. **NO direct model imports in routers**

   ```python
   # ❌ Bad
   from apiapp.modules.user.model import User
   user = await User.find_one({"email": email})

   # ✅ Good
   user = await user_use_case.get_by_email(email)
   ```

2. **NO business logic in routers**

   ```python
   # ❌ Bad - business logic in router
   @router.post("/users")
   async def create_user(data: UserRequest):
       if len(data.password) < 8:
           raise HTTPException(400, "Password too short")
       user = User(**data.dict())
       await user.save()

   # ✅ Good - business logic in use case
   @router.post("/users")
   async def create_user(
       data: UserRequest,
       user_use_case: UserUseCase = Depends(get_user_use_case)
   ):
       return await user_use_case.create_user(data)
   ```

3. **NO direct model imports directly to routers**

   ```python
   # ❌ Bad - Import other module's internal directly in router
   from apiapp.modules.user.model import User

   # ✅ Good - Import target module's use case dependency provider into your UseCase
   from ..user.use_case import get_user_use_case, UserUseCase
   ```

## 📊 File Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Router prefixes**: `/v1/{feature}` (lowercase, plural if applicable)
- **Router tags**: `["{Feature}"]` (PascalCase, singular)

## 🚀 Running The App

Always run the app using the provided scripts after activating your virtual environment.

```bash
# 1. Activate Virtual Environment
source venv/bin/activate

# 2. Run in Development Mode
./scripts/run-dev

# 3. Run in Production Mode
./scripts/run-prod
```

## 🎯 When Creating New Features

### **Option 1: Using CLI Tools (Recommended)**

The project includes a powerful CLI module generator:

```bash
# Direct creation with module name
poetry run forge generate {feature_name}

# Force overwrite existing files
poetry run forge generate {feature_name} --overwrite
```

The CLI will automatically generate:
- `modules/{feature}/model.py` - Database model with proper Beanie Document
- `modules/{feature}/schemas.py` - Request/Response schemas
- `modules/{feature}/use_case.py` - Business logic + Data Access layer
- `modules/{feature}/router.py` - API endpoints with proper routing

### **Option 2: Manual Creation**

If creating manually:

1. **Create module directory**: `modules/{feature}/`
2. **Add `__init__.py`** to make it a Python package  
3. **Create all required files**: `model.py`, `schemas.py`, `use_case.py`, `router.py`
4. **Follow the exact patterns** shown above
5. **Export router** with variable name `router`
6. **Add dependency providers** in `use_case.py` file
7. **The auto-discovery system** will automatically include your router

## 💡 Pro Tips

- Use type hints everywhere
- Add docstrings to all public methods
- Use `async/await` only for I/O operations
- Keep use cases focused on single responsibilities
- Test use cases independently with mocked repositories
- Use dependency injection for ALL external dependencies

Remember: **Consistency is key**. Follow these patterns exactly to maintain clean, maintainable, and scalable code.