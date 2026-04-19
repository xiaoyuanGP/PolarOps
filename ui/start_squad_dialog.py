from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QMessageBox,
                               QWidget, QTextEdit, QComboBox, QSpinBox)
from PySide6.QtGui import QGuiApplication
import os
from ui.draggable import DraggableWindowMixin
import asyncio
from core.ssh_manager import SSHManager

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
IMG_PATH = os.path.join(BASE_DIR, "img", "透明.png")


class _StartSquadThread(QThread):
    started = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, server, script_path, port, query_port, max_players, fixed_map):
        super().__init__()
        self.server = server
        self.script_path = script_path
        self.port = port
        self.query_port = query_port
        self.max_players = max_players
        self.fixed_map = fixed_map

    def run(self):
        try:
            async def _start():
                mgr = SSHManager(
                    host=self.server["ip"],
                    port=self.server.get("port", 22),
                    user=self.server["user"],
                    password=self.server.get("password") if self.server.get("auth_type") == "password" else None,
                    key_path=self.server.get("key_path") if self.server.get("auth_type") == "key" else None
                )
                # 检测 SquadGame 目录
                dirs_to_check = ["/data/SquadGame", "/home/steam/squadserver/SquadGame", "/root/squadserver/SquadGame"]
                game_dir = None
                for d in dirs_to_check:
                    result = await mgr.execute(f'test -d "{d}" && echo OK || echo NO')
                    if "OK" in result:
                        game_dir = d
                        break

                if not game_dir:
                    found = await mgr.execute('find / -maxdepth 4 -type d -name "SquadGame" 2>/dev/null | head -1')
                    found = found.strip()
                    if found:
                        game_dir = found

                if not game_dir:
                    await mgr.close()
                    return False, "未找到 SquadGame 目录，请确认服务器是否已安装 Squad"

                # 创建启动脚本
                script_content = f'#!/bin/bash\ncd "{game_dir}"\n./SquadGameServer.sh Port={self.port} QueryPort={self.query_port} FIXEDMAXPLAYERS={self.max_players}'
                if self.fixed_map:
                    script_content += f' FIXEDMAP={self.fixed_map}'
                script_content += '\n'

                script_path = f"/tmp/start_squad_{self.port}.sh"
                await mgr.execute(f'cat > {script_path} << \'SCRIPT_EOF\'\n{script_content}\nSCRIPT_EOF')
                await mgr.execute(f'chmod +x {script_path}')

                # 使用 screen 后台运行
                screen_name = f"squad_{self.port}"
                cmd = f'screen -dmS {screen_name} bash {script_path}'
                await mgr.execute(cmd)

                await mgr.close()
                return True, f"服务器已启动 (screen: {screen_name}, Port: {self.port})"

            loop = asyncio.new_event_loop()
            try:
                success, msg = loop.run_until_complete(_start())
            finally:
                loop.close()

            self.finished_signal.emit(success, msg)
        except Exception as exc:
            self.finished_signal.emit(False, str(exc))


class StartSquadDialog(QDialog, DraggableWindowMixin):
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self._server = server
        self._dark_mode = True
        if parent is not None:
            self._dark_mode = getattr(parent, '_dark_mode', True)
        self.setWindowTitle(f"启动 Squad 实例 - {server['name']}")
        self.setFixedSize(500, 480)
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

        content_widget = QWidget()
        content_widget.setObjectName("mainCentral")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        if self._dark_mode:
            label_style = "color: #ffffff; font-size: 13px;"
        else:
            label_style = "color: #333333; font-size: 13px;"

        self.port_input = QSpinBox()
        self.port_input.setMinimum(1024)
        self.port_input.setMaximum(65535)
        self.port_input.setValue(7787)
        self.port_input.setMinimumHeight(36)
        port_label = QLabel("游戏端口 (Port):")
        port_label.setStyleSheet(label_style)
        form.addRow(port_label, self.port_input)

        self.query_port_input = QSpinBox()
        self.query_port_input.setMinimum(1024)
        self.query_port_input.setMaximum(65535)
        self.query_port_input.setValue(27165)
        self.query_port_input.setMinimumHeight(36)
        query_label = QLabel("查询端口 (QueryPort):")
        query_label.setStyleSheet(label_style)
        form.addRow(query_label, self.query_port_input)

        self.max_players_input = QSpinBox()
        self.max_players_input.setMinimum(10)
        self.max_players_input.setMaximum(100)
        self.max_players_input.setValue(100)
        self.max_players_input.setMinimumHeight(36)
        players_label = QLabel("最大人数:")
        players_label.setStyleSheet(label_style)
        form.addRow(players_label, self.max_players_input)

        self.fixed_map_input = QLineEdit()
        self.fixed_map_input.setObjectName("loginInput")
        self.fixed_map_input.setMinimumHeight(36)
        self.fixed_map_input.setPlaceholderText("可选，例如: Fallujah")
        map_label = QLabel("固定地图 (可选):")
        map_label.setStyleSheet(label_style)
        form.addRow(map_label, self.fixed_map_input)

        content_layout.addLayout(form)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        content_layout.addWidget(self.log_output)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("启动服务器")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_server)
        btn_layout.addWidget(self.start_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumHeight(40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content_widget)

        self.setup_draggable()

    def _create_top_bar(self):
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(45)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 10, 0)

        icon_label = QLabel()
        if os.path.exists(IMG_PATH):
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(IMG_PATH).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        top_layout.addWidget(icon_label)

        title_label = QLabel(f"启动 Squad - {self._server['name']}")
        title_label.setObjectName("topTitle")
        title_label.setStyleSheet("padding-left: 8px;")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        top_layout.addWidget(close_btn)

        return top_bar

    def _start_server(self):
        port = self.port_input.value()
        query_port = self.query_port_input.value()
        max_players = self.max_players_input.value()
        fixed_map = self.fixed_map_input.text().strip()

        self.start_btn.setEnabled(False)
        self.log_output.clear()
        self.log_output.append("正在启动 Squad 服务器实例...")

        self._thread = _StartSquadThread(self._server, None, port, query_port, max_players, fixed_map)
        self._thread.started.connect(lambda m: self.log_output.append(m))
        self._thread.finished_signal.connect(self._on_finished)
        self._thread.start()

    def _on_finished(self, success, msg):
        self.start_btn.setEnabled(True)
        if success:
            self.log_output.append(f"\n✓ {msg}")
            QMessageBox.information(self, "成功", msg)
        else:
            self.log_output.append(f"\n✗ {msg}")
            QMessageBox.critical(self, "错误", msg)
