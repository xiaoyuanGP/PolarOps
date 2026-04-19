import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QMessageBox,
                               QSpacerItem, QSizePolicy)
from PySide6.QtGui import QMouseEvent, QIcon, QPixmap
from ui.draggable import DraggableWindowMixin

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STYLE_PATH = os.path.join(BASE_DIR, "resources", "style.qss")
IMG_PATH = os.path.join(BASE_DIR, "img", "透明.png")


class LoginWindow(QMainWindow, DraggableWindowMixin):
    login_success = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录 - PolarOps")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.path.exists(IMG_PATH):
            self.setWindowIcon(QIcon(IMG_PATH))
        self.setup_draggable()
        self._load_style()
        self._setup_ui()
        self._load_config()

    def _load_style(self):
        try:
            with open(STYLE_PATH, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

    def _setup_ui(self):
        central = QWidget(self)
        central.setObjectName("loginCentral")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(40)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 0, 5, 0)

        logo_label = QLabel()
        if os.path.exists(IMG_PATH):
            pixmap = QPixmap(IMG_PATH).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        top_bar_layout.addWidget(logo_label)

        title_label = QLabel("PolarOps")
        title_label.setObjectName("topTitle")
        title_label.setStyleSheet("padding-left: 8px;")
        top_bar_layout.addWidget(title_label)

        top_bar_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        top_bar_layout.addWidget(close_btn)

        main_layout.addWidget(top_bar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(15)

        spacer_top = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        content_layout.addItem(spacer_top)

        title_label = QLabel("系统登录")
        title_label.setObjectName("loginTitle")
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        content_layout.addSpacing(20)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setObjectName("loginInput")
        self.username_input.setMinimumHeight(40)
        content_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("loginInput")
        self.password_input.setMinimumHeight(40)
        self.password_input.returnPressed.connect(self._do_login)
        content_layout.addWidget(self.password_input)

        content_layout.addSpacing(10)

        self.login_btn = QPushButton("登 录")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self._do_login)
        content_layout.addWidget(self.login_btn)

        spacer_bottom = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        content_layout.addItem(spacer_bottom)

        main_layout.addWidget(content_widget)

    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except Exception:
            self._config = {"users": {"admin": "admin123"}}

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return
        users = self._config.get("users", {})
        if username in users and users[username] == password:
            self.login_success.emit(self._config)
            self.close()
        else:
            QMessageBox.critical(self, "错误", "用户名或密码错误")
