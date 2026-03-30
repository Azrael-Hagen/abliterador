import uvicorn

from abliterador_web.app import app
from abliterador_web.config import load_settings
from abliterador_web.network import detect_server_addresses


def main() -> None:
    settings = load_settings()
    print("\nAbliterador Web iniciado. Acceso LAN:")
    for item in detect_server_addresses(settings.port):
        print(f"  - {item.url}")
    print("")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
