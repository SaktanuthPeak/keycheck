"""
Create FastAPI CLI Entrypoint
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .prompts import ask_project_options
from .generator import scaffold_project
from .utils import init_git, install_dependencies, print_success_banner

app = typer.Typer(
    name="create-fastapi",
    help="🚀 Bootstrap production-ready FastAPI applications with Clean Architecture.",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.command()
def main(
    project_name: Optional[str] = typer.Argument(
        None,
        help="Name of the project and target directory.",
    ),
    db: Optional[str] = typer.Option(
        None,
        "--db",
        "-d",
        help="Database & ORM choice: 'sqlmodel' or 'beanie'",
    ),
    worker: Optional[bool] = typer.Option(
        None,
        "--worker/--no-worker",
        help="Include Background Worker & Redis (arq).",
    ),
    cookie_auth: Optional[bool] = typer.Option(
        None,
        "--cookie-auth/--no-cookie-auth",
        help="Enable HTTP-Only cookie strategy for refresh tokens.",
    ),
    examples: Optional[bool] = typer.Option(
        None,
        "--examples/--no-examples",
        help="Include sample CRUD modules (Pet / Hospital / Attachment).",
    ),
    git_init: Optional[bool] = typer.Option(
        None,
        "--git/--no-git",
        "-g",
        help="Initialize Git repository.",
    ),
    install_deps: Optional[bool] = typer.Option(
        None,
        "--install/--no-install",
        "-i",
        help="Install dependencies with uv sync immediately.",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the create-fastapi version and exit.",
    ),
):
    """
    Bootstrap a new production-ready FastAPI application with Clean Architecture.
    """
    _ = version  # handled by eager callback
    console.print("\n[bold cyan]🚀 Create-FastAPI Starter CLI[/bold cyan]")
    console.print("[dim]Scaffold enterprise-grade FastAPI projects with ease[/dim]\n")

    # If any required options are missing, ask interactively
    if db is not None and db.lower() in ("sql", "postgres", "postgresql", "sqlmodel"):
        db = "sqlmodel"
    elif db is not None and db.lower() in ("mongo", "mongodb", "beanie"):
        db = "beanie"

    options = ask_project_options(
        default_name=project_name,
        db=db,
        worker=worker,
        cookie_auth=cookie_auth,
        examples=examples,
        git_init=git_init,
        install_deps=install_deps,
    )

    target_dir = Path.cwd() / options["project_name"]

    if target_dir.exists():
        console.print(f"[bold red]❌ Error:[/bold red] Directory '[yellow]{target_dir.name}[/yellow]' already exists!")
        sys.exit(1)

    # Scaffolding process
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(description="[cyan]Scaffolding project structure...[/cyan]", total=None)
        
        try:
            scaffold_project(target_dir, options)
        except Exception as e:
            console.print(f"[bold red]❌ Failed to scaffold project:[/bold red] {e}")
            sys.exit(1)

        if options.get("git_init"):
            progress.update(task, description="[cyan]Initializing Git repository...[/cyan]")
            init_git(target_dir)

        if options.get("install_deps"):
            progress.update(task, description="[cyan]Installing dependencies with uv sync...[/cyan]")
            install_dependencies(target_dir)

    console.print()
    print_success_banner(options, target_dir)


if __name__ == "__main__":
    app()
