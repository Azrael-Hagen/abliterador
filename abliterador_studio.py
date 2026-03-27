import sys

from PySide6.QtWidgets import QApplication

from abliterador_app.ui.main_window import ModelSearcher


def main():
    app = QApplication(sys.argv)
    window = ModelSearcher()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
