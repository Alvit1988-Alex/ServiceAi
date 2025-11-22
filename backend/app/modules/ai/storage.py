"""Simple file storage helper for knowledge base content."""
from __future__ import annotations

from pathlib import Path

from app.utils.file_tools import ensure_dir


class FileStorage:
    """Utility class to persist uploaded files on disk."""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        ensure_dir(self._base_dir)

    def save(self, name: str, content: bytes) -> Path:
        path = self._base_dir / name
        path.write_bytes(content)
        return path

    def delete(self, name: str) -> None:
        path = self._base_dir / name
        if path.exists():
            path.unlink()

    def path_for(self, name: str) -> Path:
        return self._base_dir / name
