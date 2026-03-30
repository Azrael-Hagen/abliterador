from __future__ import annotations

import argparse
import webbrowser

import uvicorn

from abliterador_web.app import app
from abliterador_web.config import load_settings
from abliterador_web.network import detect_server_addresses

APP_VERSION = "0.5.0"


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

    print(f"\nAbliterador All-in-One v{APP_VERSION} levantando servicios...")
    print("Acceso disponible en:")
    for url in urls:
        print(f"  - {url}")
    print("")

    if args.open_browser and urls:
        try:
            webbrowser.open(urls[0])
        except Exception:
            pass

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
