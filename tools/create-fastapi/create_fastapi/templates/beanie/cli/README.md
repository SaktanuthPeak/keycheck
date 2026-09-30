# Forge CLI Tool

Forge is a command-line tool for generating FastAPI modules with CRUD operations in the FastAPI-Beanie starter template.

## Installation

The tool is included in the project dependencies. Make sure to install dependencies:

```bash
uv sync
```

## Usage

### Generate a new module

```bash
fast generate <module-name>
```

Example:

```bash
fast generate product
```

### Start development server

```bash
fast dev
```

This runs the FastAPI development server with hot reload.

This will create a new module called `product` with the following structure:

```
apiapp/modules/product/
├── __init__.py
├── model.py          # Beanie document model
├── schemas.py        # Pydantic schemas (DTOs)
├── use_case.py       # Business logic and data access
└── router.py         # FastAPI routes
```

### Options

- `--overwrite`: Overwrite existing files if they exist

## Generated Module Features

Each generated module includes:

- **CRUD Operations**: Create, Read, Update, Delete endpoints
- **Pagination**: Built-in pagination support using `fastapi-pagination`
- **Pydantic Schemas**: Separate schemas for create, update, and response
- **Beanie Integration**: MongoDB document models with Beanie ODM
- **Dependency Injection**: Proper dependency injection setup

## Integration

After generating a module, you need to integrate it into your FastAPI application:

1. Import the router in your main app file:

   ```python
   from apiapp.modules.product.router import router
   ```

2. Include the router in your FastAPI app:
   ```python
   app.include_router(router)
   ```

## Customization

The generated files are templates that you can customize according to your needs:

- Modify the schemas in `schemas.py` to add more fields
- Add validation logic in `use_case.py`
- Customize the API endpoints in `router.py`
- Add indexes or constraints in `model.py`

## Examples

Generate multiple modules:

```bash
fast generate category
fast generate order
fast generate inventory
```

Start development:

```bash
fast dev
```
