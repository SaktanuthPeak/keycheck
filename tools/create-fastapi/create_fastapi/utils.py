"""
Utility functions for create-fastapi (Git, UV sync, UI helpers)
"""

import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def init_git(target_dir: Path) -> bool:
    """Initialize a git repository in the target directory."""
    if not shutil.which("git"):
        return False

    try:
        subprocess.run(
            ["git", "init"],
            cwd=target_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def install_dependencies(target_dir: Path) -> bool:
    """Run `uv sync` in the target directory."""
    uv_bin = shutil.which("uv") or "uv"

    try:
        subprocess.run(
            [uv_bin, "sync"],
            cwd=target_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def print_success_banner(options: dict, target_dir: Path) -> None:
    """Print a rich formatted completion message with next steps."""
    project_name = options["project_name"]
    db_name = "PostgreSQL (SQLModel)" if options["database"] == "sqlmodel" else "MongoDB (Beanie)"

    summary_text = Text()
    summary_text.append("🎉 Project ", style="bold green")
    summary_text.append(f"{project_name}", style="bold cyan")
    summary_text.append(" created successfully!\n\n", style="bold green")

    summary_text.append("📦 Configuration:\n", style="bold")
    summary_text.append(f"  • Database: {db_name}\n", style="dim")
    summary_text.append(f"  • Worker: {'Enabled (arq + Redis)' if options.get('worker') else 'Disabled'}\n", style="dim")
    summary_text.append(f"  • Auth: {'JWT + HTTP-Only Cookie' if options.get('cookie_auth') else 'Pure Bearer JWT'}\n", style="dim")
    summary_text.append(f"  • Examples: {'Included' if options.get('examples') else 'Clean Core (User/Auth/Health)'}\n", style="dim")
    summary_text.append(f"  • Package Manager: uv\n\n", style="dim")

    summary_text.append("👉 Next Steps:\n", style="bold yellow")
    summary_text.append(f"  1. cd {project_name}\n", style="cyan")
    summary_text.append("  2. uv sync\n", style="cyan")
    summary_text.append("  3. ./scripts/run-dev\n\n", style="cyan")

    summary_text.append("📚 Documentation & Tools:\n", style="bold")
    summary_text.append("  • Swagger UI: http://localhost:9000/docs\n", style="dim")
    summary_text.append("  • Generate new module: uv run fast generate <module_name>\n", style="dim")

    console.print(Panel(summary_text, title="[bold green]✅ Ready to Build[/bold green]", border_style="green"))
