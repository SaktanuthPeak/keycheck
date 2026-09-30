# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-23

### Added

- JWT revoke (D3) in generated apps: refresh-token denylist in DB and `User.token_version` for logout-all / password-change invalidation.
- `POST /v1/auth/logout-all` and `PATCH /v1/users/me/password` (bumps `token_version`).
- Auth revoke coverage in shared refresh/logout tests; README notes on cookie vs BFF and revoke semantics.

## [0.1.0] - 2026-08-23

### Added

- Initial public release of the `create-fastapi` CLI scaffolder.
- Interactive and flag-driven scaffolding for production-ready FastAPI apps.
- Dual template backends: PostgreSQL + SQLModel (Alembic) and MongoDB + Beanie.
- Optional features: background worker (`arq` + Redis), HTTP-only cookie refresh auth, and sample CRUD modules.
- Shared template layer under `create_fastapi/templates/_shared` merged with backend-specific trees.
- Local post-scaffold helpers: optional `git init` and `uv sync`.
