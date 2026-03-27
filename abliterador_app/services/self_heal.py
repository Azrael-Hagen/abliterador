import subprocess
import sys
from typing import Callable


def _emit(cb: Callable[[str], None] | None, msg: str):
    if cb:
        cb(msg)


def _command_exists(cmd: str) -> bool:
    try:
        result = subprocess.run([cmd, "--help"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0 or "usage" in (result.stdout or "").lower()
    except Exception:
        return False


def _module_exists(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


def _pip_install(package_name: str, progress_callback: Callable[[str], None] | None = None) -> bool:
    _emit(progress_callback, f"Instalando paquete: {package_name}...")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in process.stdout:
            line = line.strip()
            if line:
                _emit(progress_callback, line)
        process.wait(timeout=600)
        return process.returncode == 0
    except Exception as exc:
        _emit(progress_callback, f"Fallo instalacion de {package_name}: {exc}")
        return False


def attempt_auto_repair(target: str, progress_callback: Callable[[str], None] | None = None) -> dict:
    """
    Intenta reparar problemas comunes del entorno y devuelve resultado estructurado.
    """
    target = (target or "general").strip().lower()
    _emit(progress_callback, f"Auto-reparacion iniciada para: {target}")

    if target in {"huggingface", "hf", "download"}:
        cli_ok = _command_exists("huggingface-cli")
        hub_ok = _module_exists("huggingface_hub")

        if cli_ok and hub_ok:
            msg = "Hugging Face ya esta correctamente instalado."
            _emit(progress_callback, msg)
            return {"ok": True, "message": msg}

        if not hub_ok:
            _emit(progress_callback, "Falta huggingface_hub, intentando instalar...")
            if not _pip_install("huggingface_hub", progress_callback):
                return {
                    "ok": False,
                    "message": "No se pudo instalar huggingface_hub automaticamente.",
                }

        # Verificacion final
        cli_ok = _command_exists("huggingface-cli")
        hub_ok = _module_exists("huggingface_hub")
        if cli_ok or hub_ok:
            msg = (
                "Reparacion completada. Se detecto soporte Hugging Face "
                f"(cli={'si' if cli_ok else 'no'}, modulo={'si' if hub_ok else 'no'})."
            )
            _emit(progress_callback, msg)
            return {"ok": True, "message": msg}

        return {
            "ok": False,
            "message": "No se encontro soporte Hugging Face despues de la reparacion.",
        }

    if target in {"ollama"}:
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                msg = "Ollama esta instalado y disponible."
                _emit(progress_callback, msg)
                return {"ok": True, "message": msg}
        except Exception:
            pass
        return {
            "ok": False,
            "message": "Ollama no esta disponible en el PATH del sistema.",
        }

    # Reparacion general minima
    hf_status = attempt_auto_repair("huggingface", progress_callback)
    return {
        "ok": hf_status["ok"],
        "message": f"Reparacion general finalizada: {hf_status['message']}",
    }
