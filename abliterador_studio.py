import sys
from pathlib import Path
import ctypes

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from abliterador_app.services.logger import setup_app_logging
from abliterador_app.ui.main_window import ModelSearcher

APP_VERSION = "0.4.0"


def main():
    logger = setup_app_logging()
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Azrael.AbliteradorStudio")
        except Exception as exc:
            logger.warning("No se pudo configurar AppUserModelID: %s", exc)

    app = QApplication(sys.argv)
    logo_path = Path(__file__).resolve().parent / "sources" / "Copilot_20260327_161839.png"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))
    logger.info("Iniciando Abliterador Studio v%s", APP_VERSION)
    window = ModelSearcher(version=APP_VERSION)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
