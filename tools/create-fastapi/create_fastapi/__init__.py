"""
Create FastAPI CLI - Enterprise Project Initializer
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("create-fastapi")
except PackageNotFoundError:
    # Source checkout without an install; pyproject.toml remains the source of truth.
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
