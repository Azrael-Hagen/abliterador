import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from abliterador_app.ui.main_window import ModelSearcher


def main():
    app = QApplication(sys.argv)
    logo_path = Path(__file__).resolve().parent / "sources" / "Copilot_20260327_161839.png"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))
    window = ModelSearcher()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
