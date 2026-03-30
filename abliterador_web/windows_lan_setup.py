"""
windows_lan_setup.py
────────────────────
Configurador inteligente de acceso LAN en Windows.
Se ejecuta al arrancar el all-in-one y verifica/crea:

  1. Regla de Firewall inbound TCP para el puerto HTTP
  2. Regla de Firewall inbound TCP para el puerto FTP (si habilitado)
  3. Reserva de URL (netsh http add urlacl) — necesaria en algunas
     configuraciones de Windows Server sin admin explícito
  4. Comprueba que el servidor esté escuchando en 0.0.0.0

Si alguna comprobación requiere permisos de administrador y el proceso
no los tiene, re-lanza el ejecutable con "Ejecutar como administrador"
(UAC) solo para la configuración, o muestra instrucciones precisas.

Todas las operaciones son IDEMPOTENTES: volver a ejecutar no rompe nada.
"""

from __future__ import annotations

import ctypes
import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

RULE_PREFIX = "AbliteradorNexus"


# ── Utilidades básicas ──────────────────────────────────────────────────


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_admin() -> bool:
    """True si el proceso actual tiene privilegios de administrador."""
    if not is_windows():
        return os.geteuid() == 0  # type: ignore[attr-defined]
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run(cmd: list[str], *, capture: bool = True) -> tuple[int, str]:
    """Ejecuta un comando y devuelve (returncode, stdout+stderr combinados)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"Comando no encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 1, "Timeout"
    except Exception as exc:
        return 1, str(exc)


# ── Firewall ────────────────────────────────────────────────────────────


def _firewall_rule_exists(rule_name: str) -> bool:
    code, out = _run(
        ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"]
    )
    return code == 0 and "No rules match" not in out and rule_name in out


def _create_firewall_rule(rule_name: str, port: int, protocol: str = "TCP") -> tuple[bool, str]:
    """Crea una regla inbound si no existe. Devuelve (success, message)."""
    if _firewall_rule_exists(rule_name):
        return True, f"Regla ya existe: {rule_name}"

    code, out = _run([
        "netsh", "advfirewall", "firewall", "add", "rule",
        f"name={rule_name}",
        "dir=in",
        "action=allow",
        f"protocol={protocol}",
        f"localport={port}",
        "profile=any",
        "enable=yes",
    ])
    if code == 0:
        return True, f"Regla creada: {rule_name} → Puerto {port}/{protocol}"
    return False, f"Error creando regla {rule_name}: {out}"


def _delete_firewall_rule(rule_name: str) -> None:
    _run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"])


# ── URL ACL (netsh http) ─────────────────────────────────────────────────


def _url_acl_exists(url: str) -> bool:
    code, out = _run(["netsh", "http", "show", "urlacl", f"url={url}"])
    return code == 0 and url in out


def _create_url_acl(url: str) -> tuple[bool, str]:
    if _url_acl_exists(url):
        return True, f"URL ACL ya existe: {url}"
    # Allow "Everyone" (SDDL) — works across locales
    code, out = _run([
        "netsh", "http", "add", "urlacl",
        f"url={url}",
        "user=Everyone",
    ])
    if code == 0:
        return True, f"URL ACL creada: {url}"
    return False, f"Error URL ACL {url}: {out}"


# ── Port availability check ─────────────────────────────────────────────


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def _process_using_port(port: int) -> str:
    """Devuelve el PID/nombre del proceso usando el puerto, o ''."""
    code, out = _run(["netstat", "-ano"])
    if code != 0:
        return ""
    for line in out.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            parts = line.split()
            pid = parts[-1] if parts else ""
            if pid.isdigit():
                code2, out2 = _run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"])
                if code2 == 0 and pid in out2:
                    name = out2.split('"')[1] if '"' in out2 else pid
                    return f"PID {pid} ({name})"
            return f"PID {pid}"
    return ""


# ── UAC re-lanzador ─────────────────────────────────────────────────────


def _relaunch_as_admin() -> None:
    """Re-lanza el proceso actual con UAC elevation y sale del proceso actual."""
    if not is_windows():
        return
    exe = sys.executable
    args = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
    sys.exit(0)


# ── Dataclass resultado ─────────────────────────────────────────────────


@dataclass
class LanSetupResult:
    firewall_http: Optional[str] = None      # mensaje de resultado
    firewall_ftp: Optional[str] = None
    url_acl: Optional[str] = None
    port_conflict: Optional[str] = None
    warnings: list[str] = None  # type: ignore[assignment]
    elevated_needed: bool = False

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []

    @property
    def ok(self) -> bool:
        return self.port_conflict is None

    def print_summary(self) -> None:
        print("\n── Configurador LAN Abliterador ────────────────────────────")
        if self.firewall_http:
            label = "✓" if "creada" in self.firewall_http or "ya existe" in self.firewall_http else "✗"
            print(f"  Firewall HTTP : {label} {self.firewall_http}")
        if self.firewall_ftp:
            label = "✓" if "creada" in self.firewall_ftp or "ya existe" in self.firewall_ftp else "✗"
            print(f"  Firewall FTP  : {label} {self.firewall_ftp}")
        if self.url_acl:
            label = "✓" if "Error" not in self.url_acl else "✗"
            print(f"  URL ACL       : {label} {self.url_acl}")
        if self.port_conflict:
            print(f"  CONFLICTO     : ✗ {self.port_conflict}")
        for w in (self.warnings or []):
            print(f"  AVISO         : ⚠ {w}")
        if self.elevated_needed:
            print(
                "\n  ⚠  Algunas configuraciones requieren Administrador.\n"
                "     Ejecuta el .exe con 'Clic derecho → Ejecutar como administrador'\n"
                "     para que el firewall y la URL ACL se configuren automáticamente."
            )
        print("────────────────────────────────────────────────────────────\n")


# ── Punto de entrada principal ──────────────────────────────────────────


def configure_lan_access(
    http_port: int,
    ftp_port: int | None = None,
    *,
    auto_elevate: bool = False,
) -> LanSetupResult:
    """
    Verifica y configura acceso LAN en Windows.

    Parámetros:
        http_port   – Puerto del servidor web (normalmente 8088)
        ftp_port    – Puerto FTP o None si deshabilitado
        auto_elevate – Si True y se necesita admin, relanza con UAC (sale del proceso actual)
    """
    result = LanSetupResult()

    if not is_windows():
        result.warnings.append("Solo Windows. Configuración LAN omitida en este SO.")
        return result

    admin = is_admin()
    if not admin:
        result.elevated_needed = True
        if auto_elevate:
            _relaunch_as_admin()
        else:
            result.warnings.append(
                "Sin privilegios de Administrador – el firewall no se puede configurar "
                "automáticamente. Ejecuta como admin para configuración completa."
            )

    # ── 1. Comprobación de puerto HTTP libre ────────────────────────────
    if _port_in_use(http_port):
        proc = _process_using_port(http_port)
        result.port_conflict = (
            f"Puerto {http_port} ya está en uso"
            + (f" por {proc}" if proc else "")
            + ". Libera el puerto o cambia ABLITERADOR_WEB_PORT."
        )

    # ── 2. Regla firewall HTTP ──────────────────────────────────────────
    if admin:
        ok, msg = _create_firewall_rule(f"{RULE_PREFIX}_HTTP_{http_port}", http_port)
        result.firewall_http = msg
        if not ok:
            result.warnings.append(msg)
    else:
        result.firewall_http = f"Omitido (sin admin) – crea manualmente: puerto {http_port}/TCP entrada"

    # ── 3. Regla firewall FTP ───────────────────────────────────────────
    if ftp_port is not None:
        if admin:
            ok, msg = _create_firewall_rule(f"{RULE_PREFIX}_FTP_{ftp_port}", ftp_port)
            result.firewall_ftp = msg
            if not ok:
                result.warnings.append(msg)
        else:
            result.firewall_ftp = f"Omitido (sin admin) – crea manualmente: puerto {ftp_port}/TCP entrada"

    # ── 4. URL ACL para el puerto HTTP ─────────────────────────────────
    # Permite que un proceso sin admin escuche en http://+:<puerto>/
    # Necesario en Windows Server con políticas restrictivas
    url = f"http://+:{http_port}/"
    if admin:
        ok, msg = _create_url_acl(url)
        result.url_acl = msg
        if not ok:
            result.warnings.append(msg)
    else:
        if not _url_acl_exists(url):
            result.url_acl = f"Omitido (sin admin) – si falla el bind, ejecuta: netsh http add urlacl url={url} user=Everyone"
        else:
            result.url_acl = f"URL ACL ya existe: {url}"

    return result
