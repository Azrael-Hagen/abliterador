"""
setup_wizard.py
───────────────
Wizard de configuración inicial de Abliterador.

Flujo:
  1. Auto-check silencioso: verifica toda la config y resuelve lo que puede solo.
  2. Si quedan issues de seguridad/críticos → wizard interactivo en consola.
  3. Persiste cambios en .abliterador.env junto al ejecutable/CWD.
  4. Carga ese .env en os.environ antes de que load_settings() sea llamado.

Idempotente: volver a ejecutar nunca rompe nada.
"""

from __future__ import annotations

import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Colores ANSI ─────────────────────────────────────────────────────────

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty() or "win" in platform.system().lower() and not os.environ.get("WT_SESSION") and not os.environ.get("TERM_PROGRAM")

def _c(code: str, text: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def OK(t: str) -> str:   return _c("92", t)
def WARN(t: str) -> str: return _c("93", t)
def ERR(t: str) -> str:  return _c("91", t)
def DIM(t: str) -> str:  return _c("2",  t)
def BOLD(t: str) -> str: return _c("1",  t)
def CYAN(t: str) -> str: return _c("96", t)


# ── Persistencia de configuración (.abliterador.env) ─────────────────────

def _env_path(base_dir: Optional[Path] = None) -> Path:
    """Ruta del archivo .abliterador.env junto al ejecutable o CWD."""
    if base_dir:
        return base_dir / ".abliterador.env"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / ".abliterador.env"
    return Path.cwd() / ".abliterador.env"


def load_env_file(env_path: Optional[Path] = None) -> dict[str, str]:
    """Lee .abliterador.env y devuelve el dict de variables."""
    path = env_path or _env_path()
    env: dict[str, str] = {}
    if not path.exists():
        return env
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def save_env_file(env: dict[str, str], env_path: Optional[Path] = None) -> None:
    """Escribe .abliterador.env con los pares clave=valor dados."""
    path = env_path or _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Abliterador – configuración local generada automáticamente",
        "# Edita este archivo para ajustar la configuración del servidor.",
        "# Los valores aquí sobreescriben las variables de entorno del sistema.",
        "",
    ]
    for key, val in sorted(env.items()):
        lines.append(f'{key}={val}')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inject_env_file(env_path: Optional[Path] = None) -> dict[str, str]:
    """Inyecta .abliterador.env en os.environ (no sobreescribe vars ya definidas en el entorno)."""
    loaded = load_env_file(env_path)
    for key, val in loaded.items():
        if key not in os.environ:
            os.environ[key] = val
    return loaded


# ── Checks individuales ───────────────────────────────────────────────────

@dataclass
class CheckItem:
    code: str
    severity: str          # "critical" | "high" | "medium" | "info"
    title: str
    message: str
    auto_fixed: bool = False
    fix_note: str = ""
    requires_input: bool = False


@dataclass
class WizardState:
    env: dict[str, str] = field(default_factory=dict)
    checks: list[CheckItem] = field(default_factory=list)
    env_path: Optional[Path] = None

    @property
    def has_critical(self) -> bool:
        return any(c.severity == "critical" and not c.auto_fixed for c in self.checks)

    @property
    def has_high(self) -> bool:
        return any(c.severity == "high" and not c.auto_fixed for c in self.checks)

    @property
    def needs_wizard(self) -> bool:
        return any(c.requires_input and not c.auto_fixed for c in self.checks)

    @property
    def all_ok(self) -> bool:
        return all(c.auto_fixed or c.severity == "info" for c in self.checks)

    def add(self, item: CheckItem) -> None:
        self.checks.append(item)


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _ollama_reachable(url: str) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=4) as r:
            return r.status < 400
    except Exception:
        return False


def _try_start_ollama() -> bool:
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        time.sleep(3)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _random_secret(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def _is_default_secret(v: str) -> bool:
    return not v or v in {"replace-me-with-random-secret", "secret", "changeme", "change_me"}


def _is_default_password(v: str) -> bool:
    return not v or v in {"change_me_now", "changeme", "admin", "password", "1234", ""}


def _workspace_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    test = path / ".abliterador_write_test"
    try:
        test.touch()
        test.unlink()
        return True
    except Exception:
        return False


# ── Auto-check + auto-fix ─────────────────────────────────────────────────

def auto_check_and_fix(state: WizardState) -> None:
    """Phase 1: silencioso. Detecta y arregla todo lo automático."""
    env = state.env

    web_port  = int(env.get("ABLITERADOR_WEB_PORT", os.getenv("ABLITERADOR_WEB_PORT", "8088")))
    ftp_port  = int(env.get("ABLITERADOR_FTP_PORT", os.getenv("ABLITERADOR_FTP_PORT", "2121")))
    ollama_url = env.get("ABLITERADOR_OLLAMA_URL", os.getenv("ABLITERADOR_OLLAMA_URL", "http://127.0.0.1:11434"))
    password   = env.get("ABLITERADOR_WEB_PASSWORD", os.getenv("ABLITERADOR_WEB_PASSWORD", "change_me_now"))
    secret     = env.get("ABLITERADOR_WEB_SECRET", os.getenv("ABLITERADOR_WEB_SECRET", "replace-me-with-random-secret"))
    ftp_pass   = env.get("ABLITERADOR_FTP_PASSWORD", os.getenv("ABLITERADOR_FTP_PASSWORD", "change_me_ftp"))
    ws_root    = Path(env.get("ABLITERADOR_USER_WORKSPACES_ROOT",
                               os.getenv("ABLITERADOR_USER_WORKSPACES_ROOT", "web_workspace/users"))).resolve()

    # ── 1. Signing secret ─────────────────────────────────────────────
    if _is_default_secret(secret):
        new_secret = _random_secret()
        env["ABLITERADOR_WEB_SECRET"] = new_secret
        state.add(CheckItem(
            code="default_signing_secret",
            severity="critical",
            title="Secret de firmado generado",
            message="El JWT signing secret estaba en valor predeterminado.",
            auto_fixed=True,
            fix_note=f"Secret generado automáticamente ({len(new_secret)} chars).",
        ))
    else:
        state.add(CheckItem(
            code="signing_secret_ok",
            severity="info",
            title="Secret de firmado personalizado",
            message="JWT secret configurado.",
            auto_fixed=True,
        ))

    # ── 2. Contraseña admin ────────────────────────────────────────────
    if _is_default_password(password):
        state.add(CheckItem(
            code="default_admin_password",
            severity="critical",
            title="Contraseña admin por defecto",
            message="La contraseña admin sigue siendo 'change_me_now'. Debes cambiarla.",
            auto_fixed=False,
            requires_input=True,
        ))
    else:
        state.add(CheckItem(
            code="admin_password_ok",
            severity="info",
            title="Contraseña admin personalizada",
            message="Contraseña admin configurada.",
            auto_fixed=True,
        ))

    # ── 3. Contraseña FTP ─────────────────────────────────────────────
    if ftp_pass in {"change_me_ftp", "changeme", "1234", "password", ""}:
        new_ftp = _random_secret(18)
        env["ABLITERADOR_FTP_PASSWORD"] = new_ftp
        state.add(CheckItem(
            code="default_ftp_password",
            severity="high",
            title="Contraseña FTP generada",
            message="La contraseña FTP estaba en valor predeterminado.",
            auto_fixed=True,
            fix_note=f"Contraseña FTP generada: {new_ftp}",
        ))
    else:
        state.add(CheckItem(
            code="ftp_password_ok",
            severity="info",
            title="Contraseña FTP personalizada",
            message="Contraseña FTP configurada.",
            auto_fixed=True,
        ))

    # ── 4. Puerto HTTP libre ───────────────────────────────────────────
    if not _port_free(web_port):
        state.add(CheckItem(
            code="port_conflict_http",
            severity="critical",
            title=f"Puerto HTTP {web_port} en uso",
            message=f"El puerto {web_port} está ocupado. Se necesita cambiarlo.",
            auto_fixed=False,
            requires_input=True,
        ))
    else:
        state.add(CheckItem(
            code="port_http_ok",
            severity="info",
            title=f"Puerto HTTP {web_port} libre",
            message="Puerto HTTP disponible.",
            auto_fixed=True,
        ))

    # ── 5. Puerto FTP libre ────────────────────────────────────────────
    ftp_enabled = env.get("ABLITERADOR_FTP_ENABLED", os.getenv("ABLITERADOR_FTP_ENABLED", "1")) == "1"
    if ftp_enabled and not _port_free(ftp_port):
        state.add(CheckItem(
            code="port_conflict_ftp",
            severity="high",
            title=f"Puerto FTP {ftp_port} en uso",
            message=f"El puerto FTP {ftp_port} está ocupado.",
            auto_fixed=False,
            requires_input=True,
        ))
    else:
        state.add(CheckItem(
            code="port_ftp_ok",
            severity="info",
            title=f"Puerto FTP {ftp_port}",
            message="Puerto FTP OK.",
            auto_fixed=True,
        ))

    # ── 6. Ollama accesible ────────────────────────────────────────────
    if not _ollama_reachable(ollama_url):
        started = _try_start_ollama()
        if started and _ollama_reachable(ollama_url):
            state.add(CheckItem(
                code="ollama_started",
                severity="high",
                title="Ollama iniciado automáticamente",
                message="Ollama no estaba corriendo; se lanzó 'ollama serve'.",
                auto_fixed=True,
                fix_note="Ollama iniciado en background.",
            ))
        else:
            state.add(CheckItem(
                code="ollama_unreachable",
                severity="high",
                title="Ollama no responde",
                message=f"No se puede conectar a Ollama en {ollama_url}.",
                auto_fixed=False,
                requires_input=True,
            ))
    else:
        state.add(CheckItem(
            code="ollama_ok",
            severity="info",
            title="Ollama accesible",
            message=f"Ollama responde en {ollama_url}.",
            auto_fixed=True,
        ))

    # ── 7. Workspace de usuarios escribible ───────────────────────────
    if not _workspace_writable(ws_root):
        state.add(CheckItem(
            code="workspace_not_writable",
            severity="high",
            title="Workspace no escribible",
            message=f"No se puede escribir en {ws_root}.",
            auto_fixed=False,
            requires_input=False,
        ))
    else:
        state.add(CheckItem(
            code="workspace_ok",
            severity="info",
            title="Workspace verificado",
            message=f"Workspace {ws_root} accesible.",
            auto_fixed=True,
        ))

    # ── 8. Host en 0.0.0.0 ────────────────────────────────────────────
    current_host = env.get("ABLITERADOR_WEB_HOST", os.getenv("ABLITERADOR_WEB_HOST", "0.0.0.0"))
    if current_host not in ("0.0.0.0", "::"):
        env["ABLITERADOR_WEB_HOST"] = "0.0.0.0"
        state.add(CheckItem(
            code="host_fixed",
            severity="high",
            title="Host ajustado a 0.0.0.0",
            message=f"El host era '{current_host}' (solo local). Cambiado a 0.0.0.0 para LAN.",
            auto_fixed=True,
            fix_note="Host ajustado automáticamente para acceso LAN.",
        ))
    else:
        state.add(CheckItem(
            code="host_ok",
            severity="info",
            title="Host configurado para LAN",
            message=f"Host = {current_host} (accesible desde LAN).",
            auto_fixed=True,
        ))


# ── Wizard interactivo ────────────────────────────────────────────────────

def _prompt(msg: str, default: str = "", hidden: bool = False) -> str:
    """Pide input al usuario con valor por defecto."""
    hint = f" [{default}]" if default else ""
    prompt_str = f"  {CYAN('→')} {msg}{hint}: "
    try:
        if hidden:
            import getpass
            val = getpass.getpass(prompt_str)
        else:
            val = input(prompt_str)
        return val.strip() or default
    except (EOFError, KeyboardInterrupt):
        return default


def _divider(title: str = "") -> None:
    bar = "─" * 62
    if title:
        print(f"\n{BOLD(bar)}")
        print(f" {BOLD(title)}")
        print(f"{BOLD(bar)}")
    else:
        print(DIM(bar))


def run_interactive_wizard(state: WizardState) -> None:
    """Phase 2: wizard guiado por consola para issues que requieren input."""

    _divider("🧙 Abliterador – Wizard de Configuración Inicial")
    print(f"\n  {WARN('Se detectaron configuraciones que necesitan tu atención.')}")
    print(f"  {DIM('Presiona Enter para aceptar el valor sugerido entre [corchetes].')}\n")

    env = state.env

    for check in state.checks:
        if check.auto_fixed or not check.requires_input:
            continue

        _divider(f"{'⚠' if check.severity == 'high' else '🔴'} {check.title}")
        print(f"  {WARN(check.message)}\n")

        # ── Contraseña admin ──────────────────────────────────────────
        if check.code == "default_admin_password":
            print(f"  {DIM('Mínimo 8 caracteres. Se guardará en .abliterador.env.')}")
            while True:
                pw = _prompt("Nueva contraseña admin", hidden=True)
                if len(pw) >= 8:
                    break
                pw2 = _random_secret(12)
                print(f"  {ERR('Muy corta.')} Sugerencia automática: {pw2}")
                choice = _prompt("Usa la sugerida? [s/n]", default="s")
                if choice.lower() in ("s", "si", "sí", "y", "yes", ""):
                    pw = pw2
                    break
            env["ABLITERADOR_WEB_PASSWORD"] = pw
            check.auto_fixed = True
            check.fix_note = "Contraseña admin actualizada."
            print(f"  {OK('✓ Contraseña guardada.')}")

        # ── Puerto HTTP en conflicto ───────────────────────────────────
        elif check.code == "port_conflict_http":
            current = int(env.get("ABLITERADOR_WEB_PORT", "8088"))
            candidates = [8080, 8000, 7860, 9000, 9088]
            suggested = next((p for p in candidates if _port_free(p)), current + 1)
            new_port_str = _prompt(f"Nuevo puerto HTTP", default=str(suggested))
            try:
                new_port = int(new_port_str)
                env["ABLITERADOR_WEB_PORT"] = str(new_port)
                check.auto_fixed = True
                check.fix_note = f"Puerto HTTP cambiado a {new_port}."
                print(f"  {OK(f'✓ Puerto HTTP → {new_port}')}")
            except ValueError:
                print(f"  {ERR('Puerto inválido. Se mantendrá el original.')}")

        # ── Puerto FTP en conflicto ────────────────────────────────────
        elif check.code == "port_conflict_ftp":
            current = int(env.get("ABLITERADOR_FTP_PORT", "2121"))
            suggested = next((p for p in range(2122, 2200) if _port_free(p)), current)
            resp = _prompt("Desactivar FTP o cambiar puerto? [d=desactivar | número=puerto]", default="d")
            if resp.lower() in ("d", "desactivar"):
                env["ABLITERADOR_FTP_ENABLED"] = "0"
                check.auto_fixed = True
                check.fix_note = "FTP desactivado."
                print(f"  {OK('✓ FTP desactivado.')}")
            else:
                try:
                    env["ABLITERADOR_FTP_PORT"] = str(int(resp))
                    check.auto_fixed = True
                    check.fix_note = f"Puerto FTP cambiado a {resp}."
                    print(f"  {OK(f'✓ Puerto FTP → {resp}')}")
                except ValueError:
                    print(f"  {ERR('Valor inválido. FTP podría fallar al iniciar.')}")

        # ── Ollama no responde ─────────────────────────────────────────
        elif check.code == "ollama_unreachable":
            current_url = env.get("ABLITERADOR_OLLAMA_URL", "http://127.0.0.1:11434")
            print(f"  {DIM('URL actual: ' + current_url)}")
            print(f"  {DIM('Opciones: Enter=reintentar | URL=cambiar URL | s=saltar')}")
            resp = _prompt("Nueva URL de Ollama o acción", default="reintentar")
            if resp in ("s", "skip", "saltar"):
                print(f"  {WARN('⚠ Ollama no estará disponible hasta que se inicie manualmente.')}")
            elif resp.lower() in ("reintentar", "retry", "r", ""):
                if _ollama_reachable(current_url):
                    check.auto_fixed = True
                    check.fix_note = "Ollama ahora responde."
                    print(f"  {OK('✓ Ollama accesible.')}")
                else:
                    print(f"  {ERR('Sigue sin responder. El servidor arrancará de todas formas.')}")
            elif resp.startswith("http"):
                env["ABLITERADOR_OLLAMA_URL"] = resp
                check.auto_fixed = True
                check.fix_note = f"URL Ollama cambiada a {resp}."
                print(f"  {OK(f'✓ URL Ollama → {resp}')}")

    _divider()


# ── Resumen de estado ─────────────────────────────────────────────────────

def print_wizard_summary(state: WizardState) -> None:
    _divider("Resumen de Configuración")
    for check in state.checks:
        if check.severity == "info" and check.auto_fixed:
            icon = OK("✓")
        elif check.auto_fixed:
            icon = OK("✓")
        elif check.requires_input:
            icon = WARN("⚠")
        else:
            icon = ERR("✗")
        note = f" {DIM('→ ' + check.fix_note)}" if check.fix_note else ""
        print(f"  {icon} {check.title}{note}")
    print()


# ── Pipeline principal ────────────────────────────────────────────────────

def run_wizard_pipeline(
    env_path: Optional[Path] = None,
    *,
    force_wizard: bool = False,
    skip_wizard: bool = False,
) -> dict[str, str]:
    """
    Ejecuta el pipeline completo de configuración.

    - Carga .abliterador.env existente
    - Corre auto-check + auto-fix
    - Si hay issues interactivos y no se pide skip: lanza wizard
    - Guarda cambios en .abliterador.env
    - Inyecta todo en os.environ

    Devuelve el dict final de variables de configuración.
    """
    resolved_path = env_path or _env_path()
    existing_env = load_env_file(resolved_path)

    state = WizardState(env=dict(existing_env), env_path=resolved_path)

    # Phase 1: auto-check y auto-fix
    auto_check_and_fix(state)

    # Phase 2: wizard interactivo si hay issues que requieren input
    if not skip_wizard and (state.needs_wizard or force_wizard):
        try:
            run_interactive_wizard(state)
        except Exception:
            # Si el wizard falla (ej. stdin no interactivo), continúa sin él
            pass

    # Print summary
    print_wizard_summary(state)

    # Guardar .abliterador.env con los cambios
    if state.env != existing_env:
        try:
            save_env_file(state.env, resolved_path)
            print(f"  {OK('✓')} Configuración guardada en: {DIM(str(resolved_path))}\n")
        except Exception as exc:
            print(f"  {WARN('⚠')} No se pudo guardar .abliterador.env: {exc}\n")
    else:
        print(f"  {DIM('Configuración sin cambios. Archivo:')} {DIM(str(resolved_path))}\n")

    # Inyectar en os.environ para que load_settings() los vea
    for key, val in state.env.items():
        os.environ[key] = val

    return dict(state.env)
