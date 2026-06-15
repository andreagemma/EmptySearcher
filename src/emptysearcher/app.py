from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from emptysearcher.ui.main_window import MainWindow


def build_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("EmptySearcher")
    app.setOrganizationName("EmptySearcher")
    app.setStyle("Fusion")
    return app


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
