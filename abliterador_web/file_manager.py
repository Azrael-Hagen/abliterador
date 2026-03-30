"""
File Manager - Organize and manage files with OneDrive-like interface.

Features:
- List files with metadata (size, date, type)
- Preview support for common file types
- Batch operations (copy, move, delete)
- Search/filter by name or type
"""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileMetadata:
    """File information for display."""

    path: str  # Relative path
    name: str  # Filename only
    size_bytes: int
    modified_at: float  # Unix timestamp
    is_dir: bool
    file_type: str  # Extension or "folder"
    readable_size: str  # "1.2 MB" format


class FileManager:
    """Manage files in user workspace with OneDrive-like operations."""

    PREVIEW_TYPES = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".xml"}
    MAX_PREVIEW_BYTES = 50_000

    def __init__(self, root_path: Path):
        """
        Args:
            root_path: Root directory for all file operations
        """
        self.root = root_path.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, rel_path: str) -> Path:
        """Resolve path safely, preventing directory traversal."""
        if not rel_path or rel_path.startswith("/"):
            return self.root

        parts = Path(rel_path).parts
        # Reject .. or absolute paths
        if any(p == ".." for p in parts):
            raise ValueError("Directory traversal not allowed")

        resolved = (self.root / rel_path).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise ValueError("Path outside workspace")

        return resolved

    def list_files(
        self,
        path: str = "",
        filter_type: Optional[str] = None,
        limit: int = 1000,
    ) -> list[FileMetadata]:
        """
        List files in directory.

        Args:
            path: Relative path (default: root)
            filter_type: Filter by extension (e.g., ".txt")
            limit: Max files to return

        Returns:
            List of file metadata
        """
        dir_path = self._resolve_safe(path)
        if not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        results: list[FileMetadata] = []
        try:
            for item in sorted(dir_path.iterdir())[:limit]:
                if filter_type and not item.name.lower().endswith(filter_type):
                    continue

                stat = item.stat()
                file_type = (
                    "folder"
                    if item.is_dir()
                    else (item.suffix.lower() or "file")
                )
                metadata = FileMetadata(
                    path=str(item.relative_to(self.root)).replace("\\", "/"),
                    name=item.name,
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                    is_dir=item.is_dir(),
                    file_type=file_type,
                    readable_size=self._format_size(stat.st_size),
                )
                results.append(metadata)
        except Exception as exc:
            raise ValueError(f"Cannot list directory: {exc}")

        return results

    def get_file_info(self, path: str) -> FileMetadata:
        """Get metadata for single file."""
        file_path = self._resolve_safe(path)
        if not file_path.exists():
            raise FileNotFoundError(path)

        stat = file_path.stat()
        file_type = (
            "folder" if file_path.is_dir() else (file_path.suffix.lower() or "file")
        )
        return FileMetadata(
            path=str(file_path.relative_to(self.root)).replace("\\", "/"),
            name=file_path.name,
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
            is_dir=file_path.is_dir(),
            file_type=file_type,
            readable_size=self._format_size(stat.st_size),
        )

    def get_preview(self, path: str, max_lines: int = 50) -> dict[str, str]:
        """
        Get text preview of file.

        Returns:
            Dict with keys: content, truncated, size_bytes, file_type
        """
        file_path = self._resolve_safe(path)
        if not file_path.is_file():
            raise ValueError("Path is not a file")

        size = file_path.stat().st_size
        if size > self.MAX_PREVIEW_BYTES:
            return {
                "content": "",
                "truncated": True,
                "size_bytes": size,
                "file_type": file_path.suffix.lower(),
                "reason": f"File too large ({self._format_size(size)})",
            }

        if file_path.suffix.lower() not in self.PREVIEW_TYPES:
            return {
                "content": "",
                "truncated": False,
                "size_bytes": size,
                "file_type": file_path.suffix.lower(),
                "reason": f"File type not supported for preview",
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[:max_lines]
                content = "".join(lines)
                truncated = len(lines) >= max_lines
                return {
                    "content": content,
                    "truncated": truncated,
                    "size_bytes": size,
                    "file_type": file_path.suffix.lower(),
                    "line_count": len(lines),
                }
        except Exception as exc:
            return {
                "content": "",
                "truncated": False,
                "size_bytes": size,
                "file_type": file_path.suffix.lower(),
                "reason": f"Cannot read file: {exc}",
            }

    def copy_file(self, src: str, dst: str) -> str:
        """Copy file from src to dst."""
        src_path = self._resolve_safe(src)
        dst_path = self._resolve_safe(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        if dst_path.exists() and dst_path.is_dir():
            dst_path = dst_path / src_path.name

        try:
            if src_path.is_file():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            return str(dst_path.relative_to(self.root)).replace("\\", "/")
        except Exception as exc:
            raise ValueError(f"Copy failed: {exc}")

    def move_file(self, src: str, dst: str) -> str:
        """Move or rename file from src to dst."""
        src_path = self._resolve_safe(src)
        dst_path = self._resolve_safe(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        if dst_path.exists() and dst_path.is_dir():
            dst_path = dst_path / src_path.name

        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return str(dst_path.relative_to(self.root)).replace("\\", "/")
        except Exception as exc:
            raise ValueError(f"Move failed: {exc}")

    def delete_file(self, path: str) -> bool:
        """Delete file or directory."""
        file_path = self._resolve_safe(path)
        if not file_path.exists():
            raise FileNotFoundError(path)

        try:
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            return True
        except Exception as exc:
            raise ValueError(f"Delete failed: {exc}")

    def create_folder(self, path: str) -> str:
        """Create a new folder."""
        folder_path = self._resolve_safe(path)
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            return str(folder_path.relative_to(self.root)).replace("\\", "/")
        except Exception as exc:
            raise ValueError(f"Cannot create folder: {exc}")

    def search(self, query: str, max_results: int = 100) -> list[FileMetadata]:
        """Search files by name (case-insensitive)."""
        results: list[FileMetadata] = []
        query_lower = query.lower()

        try:
            for item in self.root.rglob("*"):
                if len(results) >= max_results:
                    break
                if query_lower in item.name.lower():
                    stat = item.stat()
                    file_type = (
                        "folder"
                        if item.is_dir()
                        else (item.suffix.lower() or "file")
                    )
                    results.append(
                        FileMetadata(
                            path=str(item.relative_to(self.root)).replace("\\", "/"),
                            name=item.name,
                            size_bytes=stat.st_size,
                            modified_at=stat.st_mtime,
                            is_dir=item.is_dir(),
                            file_type=file_type,
                            readable_size=self._format_size(stat.st_size),
                        )
                    )
        except Exception:
            pass  # Silence errors during search

        return sorted(results, key=lambda x: x.modified_at, reverse=True)

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format byte size as human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
