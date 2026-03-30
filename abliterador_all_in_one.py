from __future__ import annotations

import argparse
import webbrowser

import uvicorn

from abliterador_web.app import app
from abliterador_web.config import load_settings
from abliterador_web.ftp_server import ftp_urls, start_ftp_server, stop_ftp_server
from abliterador_web.network import detect_server_addresses

APP_VERSION = "0.6.0"


def main() -> None:
    parser = argparse.ArgumentParser(description="Abliterador all-in-one server launcher")
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Abre el navegador automaticamente en la primera URL detectada.",
    )
    args = parser.parse_args()

    settings = load_settings()
    urls = [item.url for item in detect_server_addresses(settings.port)]
    ftp_runtime = None

    print(f"\nAbliterador All-in-One v{APP_VERSION} levantando servicios...")
    print("Acceso disponible en:")
    for url in urls:
        print(f"  - {url}")

    if settings.ftp_enabled:
        try:
            ftp_runtime = start_ftp_server(settings)
            print("\nFTP LAN activo:")
            for url in ftp_urls(settings.ftp_port):
                print(f"  - {url}")
            print(f"  - Usuario: {settings.ftp_username}")
            print(f"  - Raiz: {settings.ftp_root}")
        except Exception as exc:
            print(f"\nFTP no se pudo iniciar: {exc}")

    print("")

    if args.open_browser and urls:
        try:
            webbrowser.open(urls[0])
        except Exception:
            pass

    try:
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level="info",
        )
    finally:
        stop_ftp_server(ftp_runtime)


if __name__ == "__main__":
    main()
