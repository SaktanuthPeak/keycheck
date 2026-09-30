"""
Project Scaffolding and Template Customization Logic
"""

import re
import secrets
import shutil
from pathlib import Path


PURE_BEARER_AUTH_ROUTER = '''"""
Auth API router - authentication endpoints
"""

import typing
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Security,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordRequestForm,
)

from .use_case import AuthUseCase, get_auth_use_case
from . import schemas
from ...core.security import get_current_user
from ..user import model


router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/token", summary="Get OAuth2 access token")
async def login_for_access_token(
    form_data: typing.Annotated[OAuth2PasswordRequestForm, Depends()],
    use_case: AuthUseCase = Depends(get_auth_use_case),
) -> schemas.GetAccessTokenResponse:
    """Get access token using username and password."""
    return await use_case.login_for_access_token(form_data)


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: schemas.SignIn,
    use_case: AuthUseCase = Depends(get_auth_use_case),
) -> schemas.Token:
    """Login and get access + refresh tokens in response body."""
    return await use_case.authenticate(form_data)


@router.post("/logout", response_model=schemas.Message)
async def logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(HTTPBearer(auto_error=False))
    ] = None,
    use_case: AuthUseCase = Depends(get_auth_use_case),
) -> schemas.Message:
    """Logout: denylist the Bearer refresh token for this session."""
    token = credentials.credentials if credentials else None
    if token:
        await use_case.revoke_refresh(token)
    return schemas.Message(detail="Successfully logged out")


@router.post("/logout-all", response_model=schemas.Message)
async def logout_all(
    current_user: model.User = Depends(get_current_user),
    use_case: AuthUseCase = Depends(get_auth_use_case),
) -> schemas.Message:
    """Logout all sessions by bumping the user's token_version."""
    await use_case.logout_all(current_user)
    return schemas.Message(detail="Successfully logged out from all sessions")


@router.get("/refresh_token")
async def refresh_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(HTTPBearer(auto_error=False))
    ] = None,
    use_case: AuthUseCase = Depends(get_auth_use_case),
) -> schemas.GetAccessTokenResponse:
    """Refresh access token using Bearer refresh token."""
    token = credentials.credentials if credentials else None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await use_case.refresh_token(token)
'''


def get_templates_dir() -> Path:
    """Return the path to the templates directory."""
    return Path(__file__).resolve().parent / "templates"


def _strip_worker(target_dir: Path) -> None:
    """Remove worker, controller, redis deps, and related config when worker is disabled."""
    worker_dir = target_dir / "apiapp" / "worker"
    if worker_dir.exists():
        shutil.rmtree(worker_dir)

    controllers_dir = target_dir / "apiapp" / "controllers"
    if controllers_dir.exists():
        shutil.rmtree(controllers_dir)

    controller_cmd = target_dir / "apiapp" / "cmd" / "controller.py"
    if controller_cmd.exists():
        controller_cmd.unlink()

    for script in ["run-worker", "run-controller"]:
        script_path = target_dir / "scripts" / script
        if script_path.exists():
            script_path.unlink()

    pyproject_path = target_dir / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        content = re.sub(r'\s*"arq[^"]*",?', "", content)
        content = re.sub(r'\s*"redis[^"]*",?', "", content)
        content = re.sub(
            r'controller\s*=\s*"apiapp\.cmd\.controller:main"\n?', "", content
        )
        pyproject_path.write_text(content, encoding="utf-8")

    config_path = target_dir / "apiapp" / "core" / "config.py"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        content = re.sub(
            r'\n\s*REDIS_URL: str = "[^"]*"\n?',
            "\n",
            content,
        )
        content = re.sub(
            r'\n\s*DAILY_TIME_TO_RUN_QUEUE: str = "[^"]*"\n?',
            "\n",
            content,
        )
        config_path.write_text(content, encoding="utf-8")


def _strip_examples(target_dir: Path) -> None:
    """Remove sample CRUD modules and their tests."""
    modules_dir = target_dir / "apiapp" / "modules"
    for example_module in ["hospital", "pet", "attachment"]:
        mod_path = modules_dir / example_module
        if mod_path.exists():
            shutil.rmtree(mod_path)

    tests_dir = target_dir / "tests"
    for test_file in [
        "test_attachment_api.py",
        "test_hospital.py",
        "test_pet.py",
        "test_hospital_api.py",
        "test_pet_api.py",
    ]:
        t_path = tests_dir / test_file
        if t_path.exists():
            t_path.unlink()


def _apply_pure_bearer_auth(target_dir: Path) -> None:
    """Replace auth router with pure Bearer JWT (no cookie handling)."""
    auth_router_path = target_dir / "apiapp" / "modules" / "auth" / "router.py"
    if auth_router_path.exists():
        auth_router_path.write_text(PURE_BEARER_AUTH_ROUTER, encoding="utf-8")


_TEMPLATE_IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "poetry.lock",
    "poetry.toml",
    "uv.lock",
)


def _copy_overlay(overlay_src: Path, target_dir: Path) -> None:
    """Copy overlay files on top of an existing target (overlay wins on conflict)."""
    for src_path in overlay_src.rglob("*"):
        rel = src_path.relative_to(overlay_src)
        if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in rel.parts):
            continue
        if src_path.suffix == ".pyc":
            continue
        if src_path.name in {"poetry.lock", "poetry.toml", "uv.lock"}:
            continue

        dest_path = target_dir / rel
        if src_path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)


def scaffold_project(target_dir: Path, options: dict) -> None:
    """
    Scaffold a new FastAPI project from the selected template and options.
    """
    db = options["database"]
    templates_dir = get_templates_dir()
    shared_src = templates_dir / "_shared"
    overlay_src = templates_dir / db

    if not shared_src.exists():
        raise FileNotFoundError(
            f"Shared template not found at {shared_src}"
        )

    if not overlay_src.exists():
        raise FileNotFoundError(
            f"Template for database '{db}' not found at {overlay_src}"
        )

    if target_dir.exists():
        raise FileExistsError(f"Target directory '{target_dir}' already exists.")

    # 1. Copy shared base, then DB overlay on top
    shutil.copytree(shared_src, target_dir, ignore=_TEMPLATE_IGNORE)
    _copy_overlay(overlay_src, target_dir)

    # 2. Worker & Redis customization
    if not options.get("worker", True):
        _strip_worker(target_dir)

    # 3. Example Modules customization
    if not options.get("examples", False):
        _strip_examples(target_dir)

    # 4. Auth Strategy customization (Cookie vs Pure Bearer)
    if not options.get("cookie_auth", True):
        _apply_pure_bearer_auth(target_dir)

    # 5. Project Name & Secret Key replacements
    project_name = options["project_name"]
    safe_slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", project_name.lower())
    generated_secret = secrets.token_urlsafe(32)

    # Update pyproject.toml
    pyproject_path = target_dir / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        content = re.sub(r'name = "apiapp"', f'name = "{safe_slug}"', content)
        pyproject_path.write_text(content, encoding="utf-8")

    # Update .env.sample & create .env
    env_sample_path = target_dir / ".env.sample"
    if env_sample_path.exists():
        content = env_sample_path.read_text(encoding="utf-8")
        content = re.sub(
            r'SECRET_KEY="?[^"\n]*"?', f'SECRET_KEY="{generated_secret}"', content
        )
        content = re.sub(
            r'TITLE="?[^"\n]*"?', f'TITLE="{project_name} API"', content
        )
        if db == "sqlmodel":
            content = re.sub(r"appdb", safe_slug.replace("-", "_"), content)
        elif db == "beanie":
            content = re.sub(
                r"fastapi_starter|appdb", safe_slug.replace("-", "_"), content
            )
        env_sample_path.write_text(content, encoding="utf-8")

        # Copy to .env
        env_path = target_dir / ".env"
        env_path.write_text(content, encoding="utf-8")

    # Update README.md
    readme_path = target_dir / "README.md"
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        content = re.sub(
            r"# 🚀 FastAPI Clean Architecture Starter",
            f"# 🚀 {project_name}",
            content,
        )
        readme_path.write_text(content, encoding="utf-8")

    # 6. Ensure scripts are executable
    scripts_dir = target_dir / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.iterdir():
            if script_file.is_file():
                script_file.chmod(script_file.stat().st_mode | 0o755)
