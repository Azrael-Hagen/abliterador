from __future__ import annotations

import threading
import posixpath
from dataclasses import dataclass
from pathlib import Path

from abliterador_web.network import detect_server_addresses, is_local_network_ip


@dataclass(frozen=True)
class FtpRuntime:
    server: object
    thread: threading.Thread


def discover_windows_libraries(home: Path) -> list[Path]:
    candidates = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Pictures",
        home / "Music",
        home / "Videos",
    ]
    return [path for path in candidates if path.exists()]


def ftp_urls(port: int) -> list[str]:
    return [f"ftp://{item.ip}:{port}" for item in detect_server_addresses(port)]


def start_ftp_server(settings) -> FtpRuntime:
    try:
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.filesystems import AbstractedFS
        from pyftpdlib.handlers import FTPHandler
        from pyftpdlib.servers import FTPServer
    except Exception as exc:
        raise RuntimeError("pyftpdlib no esta instalado") from exc

    class WindowsSafeFS(AbstractedFS):
        # pyftpdlib usa os.path para rutas virtuales FTP y en Windows '/' no
        # se considera absoluto; esta version usa semantica POSIX para FTP.
        def ftpnorm(self, ftppath):
            if posixpath.isabs(ftppath):
                p = posixpath.normpath(ftppath)
            else:
                p = posixpath.normpath(posixpath.join(self.cwd, ftppath))
            while p[:2] == "//":
                p = p[1:]
            if not p.startswith("/"):
                p = "/"
            return p

    class LocalOnlyFTPHandler(FTPHandler):
        def on_connect(self):
            if settings.local_network_only and not is_local_network_ip(self.remote_ip):
                self.respond("421 Solo acceso FTP de red local.")
                self.close_when_done()

    authorizer = DummyAuthorizer()
    permissions = "elradfmwMT"
    authorizer.add_user(
        settings.ftp_username,
        settings.ftp_password,
        str(settings.ftp_root),
        perm=permissions,
    )

    handler = LocalOnlyFTPHandler
    handler.authorizer = authorizer
    handler.banner = "Abliterador FTP listo (LAN)"
    handler.abstracted_fs = WindowsSafeFS

    server = FTPServer((settings.ftp_host, settings.ftp_port), handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"timeout": 1}, daemon=True)
    thread.start()
    return FtpRuntime(server=server, thread=thread)


def stop_ftp_server(runtime: FtpRuntime | None) -> None:
    if not runtime:
        return
    try:
        runtime.server.close_all()
    except Exception:
        pass
