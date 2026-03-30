from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from abliterador_web.config import WebSettings


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    exe_parent = Path(sys.executable).resolve().parent
    cwd = Path.cwd().resolve()
    for root in [cwd, cwd.parent, exe_parent, exe_parent.parent]:
        if root not in roots:
            roots.append(root)
    return roots


def find_gui_launch_targets() -> list[Path]:
    candidates: list[Path] = []
    names = ["AbliteradorStudio.exe", "launch_abliterador_studio.bat", "abliterador_studio.py"]
    for root in _candidate_roots():
        for name in names:
            candidate = (root / name).resolve()
            if candidate.exists() and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def launch_desktop_gui(settings: WebSettings) -> str:
    if settings.gui_launch_command:
        subprocess.Popen(settings.gui_launch_command, shell=True, cwd=str(Path.cwd()))
        return settings.gui_launch_command

    for target in find_gui_launch_targets():
        if target.suffix.lower() == ".exe":
            subprocess.Popen([str(target)], cwd=str(target.parent))
            return str(target)

        if target.suffix.lower() == ".bat":
            subprocess.Popen(["cmd", "/c", str(target)], cwd=str(target.parent))
            return str(target)

        if target.name.lower() == "abliterador_studio.py":
            if not getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable, str(target)], cwd=str(target.parent))
                return str(target)

            for launcher in [["python", str(target)], ["py", "-3", str(target)], ["py", str(target)]]:
                try:
                    subprocess.Popen(launcher, cwd=str(target.parent))
                    return str(target)
                except Exception:
                    continue

    raise FileNotFoundError("No se encontro GUI de escritorio")