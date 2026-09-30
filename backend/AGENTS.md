# AGENTS.md — create-fastapi (CLI repo)

This repository is the **`create-fastapi` CLI scaffolder**, not a runnable FastAPI application.
It generates FastAPI projects from templates. Do not treat this repo’s layout as the architecture of a generated app.

## What this package is

- A Typer-based CLI (`create-fastapi`) that scaffolds enterprise-style FastAPI projects.
- Templates live under `create_fastapi/templates/` (shared + SQLModel + Beanie).
- Generated apps get their own `AGENTS.md` / `.agents/rules/` from the chosen template.

## Repo layout (overview)

```text
create_fastapi/
  cli.py              # CLI entrypoint
  generator.py        # Scaffolding / template merge
  prompts.py          # Interactive prompts
  utils.py            # Helpers (git, uv sync, banners)
  templates/
    _shared/          # Files shared by both backends
    sqlmodel/         # PostgreSQL + SQLModel specifics
    beanie/           # MongoDB + Beanie specifics
pyproject.toml        # Package metadata & version (source of truth)
CHANGELOG.md
AGENTS.md             # This file (CLI repo guidance)
```

## Develop workflow

```bash
# Install CLI dependencies (editable)
uv sync

# Run the CLI locally
uv run create-fastapi
uv run create-fastapi my-app --db sqlmodel
uv run create-fastapi --version
```

### How templates work

1. `_shared/` holds common files (middlewares, health/auth routers, Docker/scripts patterns, etc.).
2. `sqlmodel/` or `beanie/` overlays backend-specific models, infrastructure, docs, and agent rules.
3. The generator merges shared + selected backend into the target project directory.

When editing scaffolding output, change the right layer:

- Cross-cutting behavior → `templates/_shared/`
- SQL/Postgres-only → `templates/sqlmodel/`
- Mongo/Beanie-only → `templates/beanie/`

## Version and release rules

- **Source of truth:** `pyproject.toml` → `[project].version`
- Python code must read the version via `importlib.metadata.version("create-fastapi")` (see `__init__.py` / CLI). Do not hardcode release versions in Python.
- For a release:
  1. Bump `version` in `pyproject.toml` (SemVer: MAJOR.MINOR.PATCH).
  2. Update `CHANGELOG.md` under a new `[X.Y.Z]` section.
  3. Commit the release changes.
  4. Create an annotated tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`
  5. Push: `git push origin main --tags`
- Brief SemVer: MAJOR = breaking CLI/scaffold contract; MINOR = new features (backward compatible); PATCH = fixes/docs.

No GitHub Release or PyPI publish is required unless explicitly requested.

## Generated-app architecture (do not confuse)

For architecture, coding standards, and testing rules of **apps this CLI generates**, see:

- `create_fastapi/templates/sqlmodel/.agents/rules/`
- `create_fastapi/templates/beanie/.agents/rules/`

Those rules apply inside generated projects, not to developing this CLI package itself.
