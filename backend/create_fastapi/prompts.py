"""
Interactive Questionary Prompts for create-fastapi
"""

import sys
import questionary
from rich.console import Console

console = Console()


def ask_project_options(
    default_name: str | None = None,
    db: str | None = None,
    worker: bool | None = None,
    cookie_auth: bool | None = None,
    examples: bool | None = None,
    git_init: bool | None = None,
    install_deps: bool | None = None,
) -> dict:
    """Prompt user for project configuration interactively if not supplied via flags."""
    is_interactive = sys.stdin.isatty()

    # 1. Project Name
    project_name = default_name
    if not project_name:
        if is_interactive:
            project_name = questionary.text(
                "Project name:",
                default="my-fastapi-app",
                validate=lambda text: True
                if len(text.strip()) > 0
                else "Project name cannot be empty",
            ).ask()
            if project_name is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            project_name = "my-fastapi-app"

    # 2. Database Choice
    if db is None:
        if is_interactive:
            db = questionary.select(
                "Choose Database & ORM/ODM:",
                choices=[
                    questionary.Choice(
                        "🐘 PostgreSQL (SQLModel + Alembic + AsyncPG)", value="sqlmodel"
                    ),
                    questionary.Choice(
                        "🍃 MongoDB (Beanie + PyMongo)", value="beanie"
                    ),
                ],
            ).ask()
            if db is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            db = "sqlmodel"

    # 3. Background Worker & Redis
    if worker is None:
        if is_interactive:
            worker = questionary.confirm(
                "Include Background Worker & Redis (arq + tasks)?",
                default=True,
            ).ask()
            if worker is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            worker = True

    # 4. Auth Strategy
    if cookie_auth is None:
        if is_interactive:
            auth_choice = questionary.select(
                "Select Authentication Strategy:",
                choices=[
                    questionary.Choice(
                        "🔐 JWT Access Token + HTTP-Only Refresh Cookie (Recommended)",
                        value=True,
                    ),
                    questionary.Choice(
                        "🔑 Pure Bearer JWT Token (Header only)",
                        value=False,
                    ),
                ],
            ).ask()
            if auth_choice is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
            cookie_auth = auth_choice
        else:
            cookie_auth = True

    # 5. Example Modules
    if examples is None:
        if is_interactive:
            examples = questionary.confirm(
                "Include sample CRUD modules (Pet / Hospital / Attachment)?",
                default=False,
            ).ask()
            if examples is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            examples = False

    # 6. Git Init
    if git_init is None:
        if is_interactive:
            git_init = questionary.confirm(
                "Initialize Git repository?",
                default=True,
            ).ask()
            if git_init is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            git_init = True

    # 7. Install dependencies
    if install_deps is None:
        if is_interactive:
            install_deps = questionary.confirm(
                "Install dependencies with uv sync?",
                default=True,
            ).ask()
            if install_deps is None:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
        else:
            install_deps = True

    return {
        "project_name": project_name.strip(),
        "database": db,
        "worker": worker,
        "cookie_auth": cookie_auth,
        "examples": examples,
        "git_init": git_init,
        "install_deps": install_deps,
    }
