"""Image storage on disk (Spec §11.1, §13): file names come only from internal ids; no user paths, no listing."""

import os
import re
import tempfile
import time
from pathlib import Path

_KEY_RE = re.compile(r"^[a-z]{3}_[a-z0-9]{20}\.(jpg|png)$")


class ImageStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.images = self.root / "images"

    def init(self) -> None:
        self.images.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for(image_id: str, ext: str) -> str:
        key = f"{image_id}.{ext}"
        if not _KEY_RE.match(key):
            raise ValueError("invalid storage key")
        return key

    def path(self, key: str) -> Path:
        if not _KEY_RE.match(key):
            raise ValueError("invalid storage key")
        return self.images / key

    def write(self, key: str, data: bytes) -> None:
        """Atomic write: temp file in the same directory + rename."""
        dst = self.path(key)
        fd, tmp = tempfile.mkstemp(dir=self.images, prefix=".tmp_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, dst)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)

    def keys_older_than(self, seconds: float) -> list[str]:
        """Stored keys (and stale temp files) whose mtime is older than `seconds` - for the orphan sweep."""
        if not self.images.is_dir():
            return []
        cutoff = time.time() - seconds
        out = []
        for p in self.images.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    out.append(p.name)
            except FileNotFoundError:
                continue
        return out

    def remove_stale(self, name: str) -> None:
        """Delete a file found by keys_older_than (also handles temp files, which are not valid keys)."""
        p = self.images / Path(name).name
        p.unlink(missing_ok=True)
