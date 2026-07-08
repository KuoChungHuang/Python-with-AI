"""程式進入點。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui_main import APP_STYLESHEET, MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
