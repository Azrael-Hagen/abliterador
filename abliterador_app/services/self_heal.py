import os
import shutil
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


def _has_heretic_module() -> bool:
    return _module_exists("heretic") or _module_exists("heretic_llm")


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


def _cleanup_lockfiles(base_dir: str, progress_callback: Callable[[str], None] | None = None) -> int:
    if not base_dir or not os.path.isdir(base_dir):
        return 0

    removed = 0
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            if filename.endswith(".lock"):
                lock_path = os.path.join(root, filename)
                try:
                    os.remove(lock_path)
                    removed += 1
                except Exception:
                    pass
        for dirname in list(dirs):
            if dirname.endswith(".lock"):
                lock_dir = os.path.join(root, dirname)
                try:
                    shutil.rmtree(lock_dir, ignore_errors=True)
                    removed += 1
                except Exception:
                    pass

    if removed:
        _emit(progress_callback, f"Locks eliminados en {base_dir}: {removed}")
    return removed


def _prepare_local_hf_cache(progress_callback: Callable[[str], None] | None = None) -> str:
    cache_dir = os.path.join(os.getcwd(), ".hf_cache")
    hub_dir = os.path.join(cache_dir, "hub")
    transformers_dir = os.path.join(cache_dir, "transformers")

    os.makedirs(hub_dir, exist_ok=True)
    os.makedirs(transformers_dir, exist_ok=True)

    os.environ["HF_HOME"] = cache_dir
    os.environ["HUGGINGFACE_HUB_CACHE"] = hub_dir
    os.environ["TRANSFORMERS_CACHE"] = transformers_dir
    _emit(progress_callback, f"Cache local de Hugging Face preparado: {cache_dir}")
    return cache_dir


def attempt_auto_repair(target: str, progress_callback: Callable[[str], None] | None = None) -> dict:
    """
    Intenta reparar problemas comunes del entorno y devuelve resultado estructurado.
    """
    target = (target or "general").strip().lower()
    _emit(progress_callback, f"Auto-reparacion iniciada para: {target}")

    if target in {"huggingface", "hf", "download"}:
        local_cache = _prepare_local_hf_cache(progress_callback)
        user_cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        _cleanup_lockfiles(local_cache, progress_callback)
        _cleanup_lockfiles(user_cache, progress_callback)

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

    if target in {"heretic", "abliteration", "abliteracion"}:
        heretic_ok = _has_heretic_module()
        torch_ok = _module_exists("torch")

        if heretic_ok and torch_ok:
            msg = "Heretic ya esta listo para usarse."
            _emit(progress_callback, msg)
            return {"ok": True, "message": msg}

        if not heretic_ok:
            _emit(progress_callback, "No se detecta el modulo heretic. Intentando instalar heretic-llm...")
            if not _pip_install("heretic-llm", progress_callback):
                return {
                    "ok": False,
                    "message": "No se pudo instalar heretic-llm automaticamente.",
                }

        if not torch_ok:
            _emit(progress_callback, "No se detecta torch. Intentando instalar torch...")
            if not _pip_install("torch", progress_callback):
                return {
                    "ok": False,
                    "message": "No se pudo instalar torch automaticamente.",
                }

        heretic_ok = _has_heretic_module()
        torch_ok = _module_exists("torch")
        if heretic_ok and torch_ok:
            msg = "Reparacion Heretic completada correctamente."
            _emit(progress_callback, msg)
            return {"ok": True, "message": msg}

        return {
            "ok": False,
            "message": (
                "Heretic no quedo listo tras la reparacion "
                f"(heretic={'si' if heretic_ok else 'no'}, torch={'si' if torch_ok else 'no'})."
            ),
        }

    # Reparacion general minima
    hf_status = attempt_auto_repair("huggingface", progress_callback)
    heretic_status = attempt_auto_repair("heretic", progress_callback)
    return {
        "ok": hf_status["ok"] and heretic_status["ok"],
        "message": (
            "Reparacion general finalizada: "
            f"HF=({hf_status['message']}) | Heretic=({heretic_status['message']})"
        ),
    }
