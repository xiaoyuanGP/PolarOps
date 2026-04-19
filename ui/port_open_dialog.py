from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox,
                               QWidget, QTextEdit)
from PySide6.QtGui import QGuiApplication
from ui.draggable import DraggableWindowMixin


class PortOpenDialog(QDialog, DraggableWindowMixin):
    def __init__(self, servers: list, parent=None):
        super().__init__(parent)
        self._servers = servers
        self._ports = []
        self._protocol = "tcp"
        self.setWindowTitle("开放端口")
        self.setFixedSize(550, 500)
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

        title_label = QLabel("开放端口")
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
        layout.setContentsMargins(30, 15, 30, 20)
        layout.setSpacing(12)

        info_label = QLabel(f"目标服务器: {len(self._servers)} 个")
        info_label.setStyleSheet("color: #a0a5b0; font-size: 13px;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItem("TCP", "tcp")
        self.protocol_combo.addItem("UDP", "udp")
        self.protocol_combo.setObjectName("loginInput")
        self.protocol_combo.setMinimumHeight(36)
        form.addRow("协议:", self.protocol_combo)

        self.ports_input = QLineEdit()
        self.ports_input.setObjectName("loginInput")
        self.ports_input.setMinimumHeight(36)
        self.ports_input.setPlaceholderText("例如: 22 23333 24444 7777 27015")
        form.addRow("端口列表:", self.ports_input)

        layout.addLayout(form)

        quick_label = QLabel("快捷选择:")
        quick_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(quick_label)

        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)

        squad_btn = QPushButton("Squad (7777/27015/27016)")
        squad_btn.setObjectName("secondaryButton")
        squad_btn.setMinimumHeight(32)
        squad_btn.setCursor(Qt.PointingHandCursor)
        squad_btn.clicked.connect(lambda: self._set_ports("7777 27015 27016"))
        quick_layout.addWidget(squad_btn)

        mcs_btn = QPushButton("MCSM (23333/24444)")
        mcs_btn.setObjectName("secondaryButton")
        mcs_btn.setMinimumHeight(32)
        mcs_btn.setCursor(Qt.PointingHandCursor)
        mcs_btn.clicked.connect(lambda: self._set_ports("23333 24444"))
        quick_layout.addWidget(mcs_btn)

        ssh_btn = QPushButton("SSH (22)")
        ssh_btn.setObjectName("secondaryButton")
        ssh_btn.setMinimumHeight(32)
        ssh_btn.setCursor(Qt.PointingHandCursor)
        ssh_btn.clicked.connect(lambda: self._set_ports("22"))
        quick_layout.addWidget(ssh_btn)

        layout.addLayout(quick_layout)

        preset_text = QTextEdit()
        preset_text.setReadOnly(True)
        preset_text.setMaximumHeight(50)
        preset_text.setObjectName("logText")
        preset_text.setPlainText("预设: Squad游戏端口(7777 TCP/UDP, 27015 TCP, 27016 UDP), MCSManager面板(23333 TCP, 24444 TCP)")
        layout.addWidget(preset_text)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        open_btn = QPushButton("开放端口")
        open_btn.setObjectName("deployButton")
        open_btn.setMinimumHeight(38)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self._do_open)
        btn_layout.addWidget(open_btn)

        layout.addLayout(btn_layout)

        return content

    def _set_ports(self, ports: str):
        self.ports_input.setText(ports)

    def _do_open(self):
        ports_str = self.ports_input.text().strip()
        if not ports_str:
            QMessageBox.warning(self, "提示", "请输入要开放的端口")
            return
        ports = [p.strip() for p in ports_str.replace(",", " ").split() if p.strip()]
        for p in ports:
            try:
                port_num = int(p)
                if port_num < 1 or port_num > 65535:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "提示", f"端口 {p} 无效，必须是1-65535之间的数字")
                return
        self._ports = ports
        self._protocol = self.protocol_combo.currentData()
        self.accept()

    def get_ports(self) -> List[str]:
        return self._ports

    def get_protocol(self) -> str:
        return self._protocol
