# Forge CLI Tool

Forge is a command-line tool for generating FastAPI modules with CRUD operations in the FastAPI-SQLModel starter template.

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
├── model.py          # SQLModel database model
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
- **SQLModel Integration**: PostgreSQL relational models with SQLModel
- **Dependency Injection**: Proper dependency injection setup

## Auto-Discovery

You do not need to manually register the generated router. The application automatically discovers and registers all routers located in the `apiapp/modules` subdirectories (defined in [apiapp/core/router.py](../apiapp/core/router.py)).

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
