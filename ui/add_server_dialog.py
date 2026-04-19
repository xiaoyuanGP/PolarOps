from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox,
                               QWidget)
from PySide6.QtGui import QGuiApplication
from ui.draggable import DraggableWindowMixin


class AddServerDialog(QDialog, DraggableWindowMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self.setWindowTitle("添加服务器")
        self.setFixedSize(500, 560)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_ui()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        content_widget = self._create_content()
        main_layout.addWidget(content_widget)

        self.setup_draggable()

    def _create_top_bar(self):
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(45)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 10, 0)

        title_label = QLabel("添加服务器")
        title_label.setObjectName("topTitle")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        top_layout.addWidget(close_btn)

        return top_bar

    def _create_content(self):
        content = QWidget()
        content.setObjectName("mainCentral")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignHCenter)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("loginInput")
        self.name_input.setMinimumHeight(40)
        self.name_input.setPlaceholderText("例如: Squad-Server-01")
        form.addRow("名称:", self.name_input)

        self.ip_input = QLineEdit()
        self.ip_input.setObjectName("loginInput")
        self.ip_input.setMinimumHeight(40)
        self.ip_input.setPlaceholderText("例如: 192.168.1.100")
        form.addRow("IP地址:", self.ip_input)

        self.port_input = QLineEdit()
        self.port_input.setObjectName("loginInput")
        self.port_input.setMinimumHeight(40)
        self.port_input.setText("22")
        form.addRow("端口:", self.port_input)

        self.user_input = QLineEdit()
        self.user_input.setObjectName("loginInput")
        self.user_input.setMinimumHeight(40)
        self.user_input.setText("root")
        form.addRow("用户:", self.user_input)

        self.auth_combo = QComboBox()
        self.auth_combo.addItem("密码认证", "password")
        self.auth_combo.addItem("密钥认证", "key")
        self.auth_combo.setObjectName("loginInput")
        self.auth_combo.setMinimumHeight(40)
        form.addRow("认证方式:", self.auth_combo)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.setPlaceholderText("请输入密码")
        form.addRow("密码:", self.password_input)

        self.key_path_input = QLineEdit()
        self.key_path_input.setObjectName("loginInput")
        self.key_path_input.setMinimumHeight(40)
        self.key_path_input.setPlaceholderText("请输入私钥文件路径")
        self.key_path_input.setVisible(False)
        form.addRow("密钥路径:", self.key_path_input)

        rcon_label = QLabel("RCON 配置 (可选)")
        rcon_label.setStyleSheet("color: #a0a5b0; font-size: 13px; font-weight: bold;")
        form.addRow(rcon_label)

        self.rcon_port_input = QLineEdit()
        self.rcon_port_input.setObjectName("loginInput")
        self.rcon_port_input.setMinimumHeight(40)
        self.rcon_port_input.setPlaceholderText("RCON 端口，例如: 21114")
        form.addRow("RCON端口:", self.rcon_port_input)

        self.rcon_password_input = QLineEdit()
        self.rcon_password_input.setObjectName("loginInput")
        self.rcon_password_input.setMinimumHeight(40)
        self.rcon_password_input.setEchoMode(QLineEdit.Password)
        self.rcon_password_input.setPlaceholderText("RCON 密码")
        form.addRow("RCON密码:", self.rcon_password_input)

        self.auth_combo.currentIndexChanged.connect(self._on_auth_changed)
        layout.addLayout(form)

        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        add_btn = QPushButton("添加")
        add_btn.setObjectName("primaryButton")
        add_btn.setMinimumHeight(42)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._do_add)
        btn_layout.addWidget(add_btn)

        layout.addLayout(btn_layout)

        return content

    def _on_auth_changed(self):
        auth_type = self.auth_combo.currentData()
        if auth_type == "key":
            self.password_input.setVisible(False)
            self.key_path_input.setVisible(True)
        else:
            self.password_input.setVisible(True)
            self.key_path_input.setVisible(False)

    def _do_add(self):
        name = self.name_input.text().strip()
        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()
        user = self.user_input.text().strip()

        if not name:
            QMessageBox.warning(self, "提示", "服务器名称不能为空")
            return
        if not ip:
            QMessageBox.warning(self, "提示", "IP地址不能为空")
            return
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "提示", "端口必须是1-65535之间的数字")
            return
        if not user:
            QMessageBox.warning(self, "提示", "用户名不能为空")
            return

        auth_type = self.auth_combo.currentData()
        rcon_port = self.rcon_port_input.text().strip()
        rcon_password = self.rcon_password_input.text().strip()
        self._result = {
            "name": name,
            "ip": ip,
            "port": port,
            "user": user,
            "auth_type": auth_type,
            "password": self.password_input.text() if auth_type == "password" else "",
            "key_path": self.key_path_input.text().strip() if auth_type == "key" else "",
            "rcon_ip": ip,
            "rcon_port": int(rcon_port) if rcon_port else None,
            "rcon_password": rcon_password if rcon_port else None
        }
        self.accept()

    def get_result(self) -> Optional[dict]:
        return self._result
