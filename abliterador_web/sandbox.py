from __future__ import annotations

from pathlib import Path


class SandboxError(RuntimeError):
    pass


class FileSandbox:
    def __init__(self, allowed_roots: list[Path]):
        if not allowed_roots:
            raise ValueError("allowed_roots cannot be empty")
        self.allowed_roots = [p.resolve() for p in allowed_roots]

    def _resolve_path(self, user_path: str) -> Path:
        clean = user_path.strip().replace("\\", "/")
        if clean.startswith("/") or ":" in clean:
            raise SandboxError("Absolute paths are not allowed")

        target = (self.allowed_roots[0] / clean).resolve()
        for root in self.allowed_roots:
            try:
                target.relative_to(root)
                return target
            except ValueError:
                continue
        raise SandboxError("Path outside allowed directories")

    def list_dir(self, user_path: str = ".") -> list[str]:
        target = self._resolve_path(user_path)
        if not target.exists():
            raise SandboxError("Path does not exist")
        if not target.is_dir():
            raise SandboxError("Path is not a directory")
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            suffix = "/" if item.is_dir() else ""
            entries.append(item.name + suffix)
        return entries

    def read_text(self, user_path: str) -> str:
        target = self._resolve_path(user_path)
        if not target.is_file():
            raise SandboxError("File not found")
        return target.read_text(encoding="utf-8")

    def write_text(self, user_path: str, content: str) -> str:
        target = self._resolve_path(user_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def delete_file(self, user_path: str) -> str:
        target = self._resolve_path(user_path)
        if not target.is_file():
            raise SandboxError("File not found")
        target.unlink()
        return str(target)

    def allowed_roots_display(self) -> list[str]:
        return [str(path) for path in self.allowed_roots]
