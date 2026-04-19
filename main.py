import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    login_window = LoginWindow()

    def on_login_success(config):
        main_window = MainWindow(config)
        main_window.show()

    login_window.login_success.connect(on_login_success)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
