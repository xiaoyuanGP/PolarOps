import os
import json
from PySide6.QtCore import Qt, Signal, Slot, QSize, QThread, QPoint
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QCheckBox, QTextEdit, QProgressBar, QGroupBox, QMessageBox,
                               QSizePolicy, QSplitter, QMenu, QFileDialog, QDialog, QInputDialog)
from PySide6.QtGui import QFont, QIcon, QCursor, QPixmap
from ui.draggable import DraggableWindowMixin
from ui.edit_server_dialog import EditServerDialog
from ui.add_server_dialog import AddServerDialog
from ui.port_open_dialog import PortOpenDialog
from ui.file_browser_dialog import FileBrowserDialog
from ui.start_squad_dialog import StartSquadDialog
from threads.command_thread import CommandThread
from threads.status_thread import StatusThread
from core.config_manager import ConfigManager

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STYLE_PATH = os.path.join(BASE_DIR, "resources", "style.qss")
IMG_PATH = os.path.join(BASE_DIR, "img", "透明.png")


class MainWindow(QMainWindow, DraggableWindowMixin):
    def __init__(self, config: dict):
        super().__init__()
        self.config_mgr = ConfigManager(CONFIG_PATH)
        self.servers = self.config_mgr.get_servers()
        self._command_thread = None
        self._status_thread = None
        self._dark_mode = False
        self._setup_window()
        self._load_style()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowTitle("PolarOps - Squad Server Manager")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.path.exists(IMG_PATH):
            self.setWindowIcon(QIcon(IMG_PATH))
        self.setup_draggable()

    def _load_style(self):
        try:
            with open(STYLE_PATH, "r", encoding="utf-8") as f:
                style = f.read()
            if not self._dark_mode:
                style = self._generate_light_style()
            self.setStyleSheet(style)
        except Exception:
            pass

    def _generate_light_style(self):
        return """
            QWidget#mainCentral, QWidget#loginCentral {
                background-color: #f0f0f0;
                border-radius: 10px;
            }
            #topBar {
                background-color: #e8e8e8;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #d0d0d0;
            }
            #topTitle {
                color: #333333;
                font-size: 14px;
                font-weight: bold;
                padding-left: 10px;
            }
            #windowButton {
                background-color: #e8e8e8;
                color: #666666;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            #windowButton:hover {
                background-color: #d0d0d0;
                color: #333333;
            }
            #closeButton {
                background-color: #e8e8e8;
                color: #666666;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            #closeButton:hover {
                background-color: #e81123;
                color: white;
            }
            #loginTitle {
                color: #333333;
                font-size: 24px;
                font-weight: bold;
            }
            #loginInput {
                background-color: #ffffff;
                color: #333333;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            #loginInput:focus {
                border: 2px solid #2196f3;
            }
            #loginButton {
                background-color: #2196f3;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            #loginButton:hover {
                background-color: #1976d2;
            }
            QGroupBox {
                color: #555555;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #333333;
            }
            #serverTable {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                gridline-color: #e0e0e0;
                selection-background-color: #2196f3;
                selection-color: #ffffff;
                font-size: 13px;
            }
            #serverTable::item {
                padding: 8px;
            }
            #serverTable::item:hover {
                background-color: #e3f2fd;
            }
            #serverTable QHeaderView::section {
                background-color: #f5f5f5;
                color: #2196f3;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #d0d0d0;
                border-right: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 13px;
            }
            #logText {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 10px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                color: #333333;
                background-color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton#primaryButton {
                background-color: #2196f3;
                color: #ffffff;
            }
            QPushButton#primaryButton:hover {
                background-color: #1976d2;
            }
            QPushButton#secondaryButton {
                background-color: #e0e0e0;
            }
            QPushButton#deployButton {
                background-color: #4caf50;
                color: #ffffff;
            }
            QPushButton#deployButton:hover {
                background-color: #388e3c;
            }
            QPushButton#deleteButton {
                background-color: #ef5350;
                color: #ffffff;
            }
            QPushButton#deleteButton:hover {
                background-color: #d32f2f;
            }
            QMenu {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 5px 0;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #2196f3;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #d0d0d0;
                margin: 5px 10px;
            }
            #commandInput {
                background-color: #ffffff;
                color: #333333;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: "Consolas", "Courier New", monospace;
            }
            #commandInput:focus {
                border: 2px solid #2196f3;
            }
            #progressBar {
                background-color: #e0e0e0;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                text-align: center;
                color: #333333;
                height: 25px;
            }
            #progressBar::chunk {
                background-color: #2196f3;
                border-radius: 6px;
            }
            #progressLabel {
                color: #666666;
                font-size: 12px;
                padding-left: 10px;
            }
            QSplitter::handle {
                background-color: #d0d0d0;
            }
            QSplitter::handle:hover {
                background-color: #2196f3;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #b0b0b0;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #2196f3;
                border-color: #2196f3;
            }
            QMessageBox QPushButton {
                background-color: #e0e0e0;
                color: #333333;
                padding: 6px 20px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2196f3;
                color: #ffffff;
            }
        """

    def _setup_ui(self):
        central = QWidget(self)
        central.setObjectName("mainCentral")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        content_splitter = QSplitter(Qt.Vertical)

        server_group = self._create_server_group()
        content_splitter.addWidget(server_group)

        bottom_splitter = QSplitter(Qt.Horizontal)

        log_group = self._create_log_group()
        bottom_splitter.addWidget(log_group)

        control_group = self._create_control_group()
        bottom_splitter.addWidget(control_group)

        bottom_splitter.setSizes([700, 300])
        content_splitter.addWidget(bottom_splitter)

        content_splitter.setSizes([400, 400])
        main_layout.addWidget(content_splitter)

        self._apply_drag_to_children(self)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._load_style()

    def _create_top_bar(self):
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(40)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 10, 0)

        logo_label = QLabel()
        if os.path.exists(IMG_PATH):
            pixmap = QPixmap(IMG_PATH).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        top_layout.addWidget(logo_label)

        title_label = QLabel("PolarOps")
        title_label.setObjectName("topTitle")
        title_label.setStyleSheet("padding-left: 8px;")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        theme_btn = QPushButton("🌓")
        theme_btn.setObjectName("windowButton")
        theme_btn.setFixedSize(35, 30)
        theme_btn.setCursor(Qt.PointingHandCursor)
        theme_btn.clicked.connect(self._toggle_theme)
        theme_btn.setToolTip("切换主题")
        top_layout.addWidget(theme_btn)

        minimize_btn = QPushButton("─")
        minimize_btn.setObjectName("windowButton")
        minimize_btn.setFixedSize(35, 30)
        minimize_btn.setCursor(Qt.PointingHandCursor)
        minimize_btn.clicked.connect(self.showMinimized)
        top_layout.addWidget(minimize_btn)

        max_btn = QPushButton("☐")
        max_btn.setObjectName("windowButton")
        max_btn.setFixedSize(35, 30)
        max_btn.setCursor(Qt.PointingHandCursor)
        max_btn.clicked.connect(self._toggle_maximize)
        top_layout.addWidget(max_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(35, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        top_layout.addWidget(close_btn)

        return top_bar

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _create_server_group(self):
        group = QGroupBox("服务器节点列表")
        group.setObjectName("serverGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)

        self.server_table = QTableWidget()
        self.server_table.setObjectName("serverTable")
        self.server_table.setColumnCount(8)
        self.server_table.setHorizontalHeaderLabels(["选择", "名称", "IP", "端口", "用户", "状态", "人数", "ID"])
        self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.server_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.server_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.server_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.server_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.server_table.setColumnWidth(0, 50)
        self.server_table.setColumnWidth(3, 60)
        self.server_table.setColumnWidth(5, 80)
        self.server_table.setColumnWidth(6, 80)
        self.server_table.setColumnWidth(7, 90)
        self.server_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.server_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.server_table.verticalHeader().setVisible(False)
        self.server_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.server_table.customContextMenuRequested.connect(self._show_context_menu)
        self.server_table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self._populate_server_table()

        layout.addWidget(self.server_table)

        table_btn_layout = QHBoxLayout()

        self.add_server_btn = QPushButton("添加服务器")
        self.add_server_btn.setObjectName("primaryButton")
        self.add_server_btn.setCursor(Qt.PointingHandCursor)
        self.add_server_btn.clicked.connect(self._add_server)
        table_btn_layout.addWidget(self.add_server_btn)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setObjectName("secondaryButton")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self._select_all)
        table_btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.setObjectName("secondaryButton")
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        table_btn_layout.addWidget(self.deselect_all_btn)

        self.delete_selected_btn = QPushButton("删除选中")
        self.delete_selected_btn.setObjectName("deleteButton")
        self.delete_selected_btn.setCursor(Qt.PointingHandCursor)
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        table_btn_layout.addWidget(self.delete_selected_btn)

        self.refresh_status_btn = QPushButton("刷新状态")
        self.refresh_status_btn.setObjectName("primaryButton")
        self.refresh_status_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_status_btn.clicked.connect(self._refresh_status)
        table_btn_layout.addWidget(self.refresh_status_btn)

        self.refresh_rcon_btn = QPushButton("刷新人数")
        self.refresh_rcon_btn.setObjectName("primaryButton")
        self.refresh_rcon_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_rcon_btn.clicked.connect(self._refresh_rcon)
        table_btn_layout.addWidget(self.refresh_rcon_btn)

        table_btn_layout.addStretch()

        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("secondaryButton")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_servers)
        table_btn_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("secondaryButton")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_servers)
        table_btn_layout.addWidget(self.export_btn)

        layout.addLayout(table_btn_layout)

        return group

    def _show_context_menu(self, pos: QPoint):
        row = self.server_table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)
        menu.setObjectName("contextMenu")

        browse_action = menu.addAction("浏览文件")
        browse_action.triggered.connect(lambda: self._browse_files(row))

        menu.addSeparator()

        start_squad_action = menu.addAction("启动 Squad 实例")
        start_squad_action.triggered.connect(lambda: self._start_squad_instance(row))

        edit_action = menu.addAction("编辑服务器")
        edit_action.triggered.connect(lambda: self._edit_server_by_row(row))

        delete_action = menu.addAction("删除服务器")
        delete_action.triggered.connect(lambda: self._delete_single_by_row(row))

        menu.exec(QCursor.pos())

    def _browse_files(self, row: int):
        if row < 0 or row >= len(self.servers):
            return
        server = self.servers[row]
        dialog = FileBrowserDialog(server, self)
        dialog.exec()

    def _start_squad_instance(self, row: int):
        if row < 0 or row >= len(self.servers):
            return
        server = self.servers[row]
        dialog = StartSquadDialog(server, self)
        dialog.exec()

    def _on_row_double_clicked(self, row: int, col: int):
        self._edit_server_by_row(row)

    def _populate_server_table(self):
        self.server_table.setRowCount(len(self.servers))
        for i, server in enumerate(self.servers):
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.server_table.setCellWidget(i, 0, checkbox_widget)

            name_item = QTableWidgetItem(server.get("name", ""))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(i, 1, name_item)

            ip_item = QTableWidgetItem(server.get("ip", ""))
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(i, 2, ip_item)

            port_item = QTableWidgetItem(str(server.get("port", 22)))
            port_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(i, 3, port_item)

            user_item = QTableWidgetItem(server.get("user", ""))
            user_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(i, 4, user_item)

            status_item = QTableWidgetItem("未检测")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(Qt.gray)
            self.server_table.setItem(i, 5, status_item)

            player_item = QTableWidgetItem("--")
            player_item.setTextAlignment(Qt.AlignCenter)
            player_item.setForeground(Qt.gray)
            self.server_table.setItem(i, 6, player_item)

            id_item = QTableWidgetItem(server.get("id", ""))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(i, 7, id_item)

    def _refresh_table(self):
        self.servers = self.config_mgr.get_servers()
        checked_ids = self._get_checked_ids()
        self.server_table.setRowCount(0)
        self._populate_server_table()
        self._restore_checked_state(checked_ids)

    def _get_checked_ids(self):
        ids = set()
        for i in range(self.server_table.rowCount()):
            widget = self.server_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    id_item = self.server_table.item(i, 6)
                    if id_item:
                        ids.add(id_item.text())
        return ids

    def _restore_checked_state(self, ids: set):
        for i in range(self.server_table.rowCount()):
            id_item = self.server_table.item(i, 6)
            if id_item and id_item.text() in ids:
                widget = self.server_table.cellWidget(i, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)

    def _create_log_group(self):
        group = QGroupBox("实时日志")
        group.setObjectName("logGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        log_btn_layout = QHBoxLayout()

        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.setObjectName("secondaryButton")
        self.clear_log_btn.setCursor(Qt.PointingHandCursor)
        self.clear_log_btn.clicked.connect(self._clear_log)
        log_btn_layout.addWidget(self.clear_log_btn)

        log_btn_layout.addStretch()
        layout.addLayout(log_btn_layout)

        return group

    def _create_control_group(self):
        group = QGroupBox("操作控制台")
        group.setObjectName("controlGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)

        cmd_layout = QHBoxLayout()
        cmd_label = QLabel("命令:")
        layout.addWidget(cmd_label)

        self.command_input = QLineEdit()
        self.command_input.setObjectName("commandInput")
        self.command_input.setPlaceholderText("输入要执行的命令，例如: ls -la /home")
        self.command_input.returnPressed.connect(self._execute_command)
        layout.addWidget(self.command_input)

        self.execute_cmd_btn = QPushButton("执行命令")
        self.execute_cmd_btn.setObjectName("primaryButton")
        self.execute_cmd_btn.setCursor(Qt.PointingHandCursor)
        self.execute_cmd_btn.clicked.connect(self._execute_command)
        layout.addWidget(self.execute_cmd_btn)

        layout.addLayout(cmd_layout)

        deploy_layout = QHBoxLayout()
        deploy_label = QLabel("部署:")
        layout.addWidget(deploy_label)

        self.deploy_mcs_btn = QPushButton("安装 MCSManager")
        self.deploy_mcs_btn.setObjectName("deployButton")
        self.deploy_mcs_btn.setCursor(Qt.PointingHandCursor)
        self.deploy_mcs_btn.clicked.connect(lambda: self._start_deploy("mcsmanager"))
        layout.addWidget(self.deploy_mcs_btn)

        self.deploy_squad_btn = QPushButton("安装 Squad")
        self.deploy_squad_btn.setObjectName("deployButton")
        self.deploy_squad_btn.setCursor(Qt.PointingHandCursor)
        self.deploy_squad_btn.clicked.connect(lambda: self._start_deploy("squad"))
        layout.addWidget(self.deploy_squad_btn)

        layout.addLayout(deploy_layout)

        port_layout = QHBoxLayout()
        port_label = QLabel("防火墙:")
        layout.addWidget(port_label)

        self.open_port_btn = QPushButton("开放端口")
        self.open_port_btn.setObjectName("deployButton")
        self.open_port_btn.setCursor(Qt.PointingHandCursor)
        self.open_port_btn.clicked.connect(self._open_ports)
        port_layout.addWidget(self.open_port_btn)

        port_layout.addStretch()
        layout.addLayout(port_layout)

        progress_layout = QHBoxLayout()
        progress_label = QLabel("进度:")
        layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        self.progress_label.setObjectName("progressLabel")
        layout.addWidget(self.progress_label)

        layout.addLayout(progress_layout)

        return group

    def _get_selected_servers(self):
        selected = []
        for i in range(self.server_table.rowCount()):
            widget = self.server_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    if 0 <= i < len(self.servers):
                        selected.append(self.servers[i])
        return selected

    def _select_all(self):
        for i in range(self.server_table.rowCount()):
            widget = self.server_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def _deselect_all(self):
        for i in range(self.server_table.rowCount()):
            widget = self.server_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

    def _clear_log(self):
        self.log_text.clear()

    def _append_log(self, host: str, message: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f'<span style="color:#888;">[{timestamp}]</span> <span style="color:#4fc3f7;">[{host}]</span> {message}')

    @Slot(str, bool)
    def _on_status_checked(self, host: str, is_online: bool):
        for i in range(self.server_table.rowCount()):
            ip_item = self.server_table.item(i, 2)
            if ip_item and ip_item.text() == host:
                status_item = self.server_table.item(i, 5)
                if status_item:
                    if is_online:
                        status_item.setText("在线")
                        status_item.setForeground(Qt.green)
                    else:
                        status_item.setText("离线")
                        status_item.setForeground(Qt.red)
                break

    def _refresh_status(self):
        selected = self._get_selected_servers()
        if not selected:
            selected = self.servers
        if not selected:
            QMessageBox.warning(self, "提示", "没有可用的服务器节点")
            return

        self._append_log("系统", f"开始检测 {len(selected)} 个节点状态...")

        if self._status_thread and self._status_thread.isRunning():
            self._status_thread.stop()
            self._status_thread.wait()

        self._status_thread = StatusThread(selected)
        self._status_thread.status_checked.connect(self._on_status_checked)
        self._status_thread.finished_all.connect(self._on_status_check_finished)
        self._status_thread.start()

    def _on_status_check_finished(self):
        self._append_log("系统", "状态检测完成")

    def _refresh_rcon(self):
        selected = self._get_selected_servers()
        if not selected:
            selected = self.servers
        if not selected:
            QMessageBox.warning(self, "提示", "没有可用的服务器节点")
            return

        rcon_servers = [s for s in selected if s.get("rcon_port")]
        if not rcon_servers:
            QMessageBox.warning(self, "提示", "选中的服务器没有配置RCON端口")
            return

        self._append_log("系统", f"开始查询 {len(rcon_servers)} 个节点的RCON人数...")
        self._refresh_rcon_players(rcon_servers)

    def _refresh_rcon_players(self, servers: list):
        from PySide6.QtCore import QThread, Signal

        class _RconThread(QThread):
            rcon_done = Signal(str, int)
            rcon_error = Signal(str, str)

            def __init__(self, srv_list):
                super().__init__()
                self.srv_list = srv_list

            def run(self):
                from core.rcon_manager import RconManager
                for srv in self.srv_list:
                    rcon_ip = srv.get("rcon_ip", srv["ip"])
                    rcon_port = srv.get("rcon_port")
                    rcon_pw = srv.get("rcon_password")
                    if not rcon_port or not rcon_pw:
                        continue
                    try:
                        mgr = RconManager(host=rcon_ip, port=rcon_port, password=rcon_pw)
                        players = mgr.get_players()
                        mgr.close()
                        count = len(players) if players else 0
                        self.rcon_done.emit(srv["ip"], count)
                    except Exception as exc:
                        self.rcon_error.emit(srv.get("name", srv["ip"]), str(exc))

        self._rcon_thread = _RconThread(servers)
        self._rcon_thread.rcon_done.connect(self._on_rcon_checked)
        self._rcon_thread.rcon_error.connect(self._on_rcon_error)
        self._rcon_thread.start()

    @Slot(str, int)
    def _on_rcon_checked(self, ip: str, count: int):
        for i in range(self.server_table.rowCount()):
            ip_item = self.server_table.item(i, 2)
            if ip_item and ip_item.text() == ip:
                player_item = self.server_table.item(i, 6)
                if player_item:
                    player_item.setText(f"{count} 人")
                    player_item.setForeground(Qt.green)
                break

    @Slot(str, str)
    def _on_rcon_error(self, name: str, error: str):
        self._append_log("系统", f"RCON查询 {name} 失败: {error}")

    def _execute_command(self):
        command = self.command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "提示", "请输入要执行的命令")
            return

        selected = self._get_selected_servers()
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个服务器节点")
            return

        self._append_log("系统", f"开始对 {len(selected)} 个节点执行命令: {command}")
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0/{len(selected)} 完成")

        self._start_command_thread(selected, command=command)

    def _start_deploy(self, deploy_type: str):
        selected = self._get_selected_servers()
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个服务器节点")
            return

        deploy_name = "MCSManager" if deploy_type == "mcsmanager" else "Squad"
        self._append_log("系统", f"开始部署 {deploy_name} 到 {len(selected)} 个节点...")
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0/{len(selected)} 完成")

        self._start_command_thread(selected, deploy_type=deploy_type)

    def _start_command_thread(self, servers: list, command: str = None, deploy_type: str = None):
        if self._command_thread and self._command_thread.isRunning():
            QMessageBox.warning(self, "提示", "有任务正在执行，请等待完成")
            return

        self._command_thread = CommandThread(servers=servers, command=command, deploy_type=deploy_type)
        self._command_thread.log_received.connect(self._append_log)
        self._command_thread.progress_updated.connect(self._on_progress_updated)
        self._command_thread.finished_all.connect(self._on_command_finished)
        self._command_thread.error_occurred.connect(self._on_command_error)
        self._command_thread.start()

    def _open_ports(self):
        selected = self._get_selected_servers()
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个服务器节点")
            return

        port_dialog = PortOpenDialog(selected, self)
        if port_dialog.exec() == QDialog.Accepted:
            ports = port_dialog.get_ports()
            if ports:
                protocol = port_dialog.get_protocol()
                port_list = ' '.join(ports)
                cmd = f"""#!/bin/bash
echo "=== 开始配置防火墙规则 ==="

# 检测防火墙类型并配置
if command -v firewall-cmd &>/dev/null && systemctl is-active firewalld &>/dev/null 2>&1; then
    echo "[firewalld] 放行端口..."
    for p in {port_list}; do
        echo "  开放端口: $p/{protocol}"
        sudo firewall-cmd --permanent --add-port=$p/{protocol}
    done
    sudo firewall-cmd --reload
    echo "✓ firewalld 已放行端口: {port_list}"
elif command -v ufw &>/dev/null; then
    echo "[ufw] 放行端口..."
    sudo ufw enable 2>/dev/null
    for p in {port_list}; do
        echo "  开放端口: $p/{protocol}"
        sudo ufw allow $p/{protocol}
    done
    sudo ufw reload
    echo "✓ ufw 已放行端口: {port_list}"
else
    echo "[iptables] 放行端口..."
    for p in {port_list}; do
        echo "  开放端口: $p/{protocol}"
        sudo iptables -C INPUT -p {protocol} --dport $p -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p {protocol} --dport $p -j ACCEPT
    done
    sudo mkdir -p /etc/iptables 2>/dev/null
    command -v iptables-save &>/dev/null && sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null 2>&1
    echo "✓ iptables 已放行端口: {port_list}"
fi

# 验证端口是否开放
echo ""
echo "=== 验证端口配置 ==="
for p in {port_list}; do
    if command -v firewall-cmd &>/dev/null && systemctl is-active firewalld &>/dev/null 2>&1; then
        if sudo firewall-cmd --list-ports 2>/dev/null | grep -q "$p/{protocol}"; then
            echo "✓ 端口 $p/{protocol} 已成功开放 (firewalld)"
        else
            echo "✗ 端口 $p/{protocol} 可能未在 firewalld 中放行"
        fi
    elif sudo iptables -L INPUT -n 2>/dev/null | grep -q "dpt:$p"; then
        echo "✓ 端口 $p/{protocol} 已成功开放 (iptables/ufw)"
    else
        echo "✗ 端口 $p/{protocol} 配置可能失败，请手动检查"
    fi
done

echo ""
echo "=== 防火墙配置完成 ==="
echo "注意: 如果仍无法访问，请检查:"
echo "1. 云服务商安全组/网络 ACL 是否放行 (阿里云/腾讯云/AWS 等需要在控制台配置)"
echo "2. 服务是否监听 0.0.0.0 而非 127.0.0.1"
echo "3. SELinux 是否阻止访问 (执行: sudo setenforce 0 临时关闭)"
"""
                self._append_log("系统", f"开始对 {len(selected)} 个节点开放端口: {', '.join(ports)} ({protocol})")
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"0/{len(selected)} 完成")
                self._start_command_thread(selected, command=cmd)

    @Slot(int, int)
    def _on_progress_updated(self, completed: int, total: int):
        if total > 0:
            percentage = int((completed / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"{completed}/{total} 完成 ({percentage}%)")

    @Slot()
    def _on_command_finished(self):
        self._append_log("系统", "所有任务执行完成")
        self.progress_bar.setValue(100)
        self.progress_label.setText("全部完成")

    @Slot(str)
    def _on_command_error(self, error_msg: str):
        self._append_log("系统", f"[ERROR] {error_msg}")
        QMessageBox.critical(self, "错误", f"执行过程中发生错误:\n{error_msg}")

    def _add_server(self):
        dialog = AddServerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self.config_mgr.add_server(result)
                self._refresh_table()
                self._append_log("系统", f"已添加服务器: {result['name']} ({result['ip']})")
                self._auto_check_server(result)

    def _auto_check_server(self, server: dict):
        self._append_log("系统", f"正在检测服务器: {server['name']} ({server['ip']})...")

        from PySide6.QtCore import QThread, Signal

        class _CheckThread(QThread):
            finished_check = Signal(str, bool)
            error_check = Signal(str, str)

            def __init__(self, srv):
                super().__init__()
                self.srv = srv

            def run(self):
                import asyncio
                from core.ssh_manager import SSHManager
                loop = asyncio.new_event_loop()
                try:
                    async def _check():
                        mgr = SSHManager(
                            host=self.srv["ip"],
                            port=self.srv.get("port", 22),
                            user=self.srv["user"],
                            password=self.srv.get("password") if self.srv.get("auth_type") == "password" else None,
                            key_path=self.srv.get("key_path") if self.srv.get("auth_type") == "key" else None
                        )
                        is_online = await mgr.check_online()
                        await mgr.close()
                        return is_online
                    is_online = loop.run_until_complete(_check())
                    self.finished_check.emit(self.srv["ip"], is_online)
                except Exception as exc:
                    self.error_check.emit(self.srv["name"], str(exc))
                finally:
                    loop.close()

        self._check_thread = _CheckThread(server)
        self._check_thread.finished_check.connect(self._on_auto_check_done)
        self._check_thread.error_check.connect(self._on_auto_check_error)
        self._check_thread.start()

    @Slot(str, bool)
    def _on_auto_check_done(self, ip: str, is_online: bool):
        for i in range(self.server_table.rowCount()):
            ip_item = self.server_table.item(i, 2)
            if ip_item and ip_item.text() == ip:
                status_item = self.server_table.item(i, 5)
                if status_item:
                    if is_online:
                        status_item.setText("在线")
                        status_item.setForeground(Qt.green)
                    else:
                        status_item.setText("离线")
                        status_item.setForeground(Qt.red)
                break

    @Slot(str, str)
    def _on_auto_check_error(self, name: str, error: str):
        self._append_log("系统", f"检测 {name} 失败: {error}")

    def _edit_server_by_row(self, row: int):
        if row < 0 or row >= len(self.servers):
            return
        server = self.servers[row]
        dialog = EditServerDialog(server, self)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                server_id = server.get("id")
                self.config_mgr.update_server(server_id, result)
                self._refresh_table()
                self._append_log("系统", f"已更新服务器: {result['name']} ({result['ip']})")

    def _delete_single_by_row(self, row: int):
        if row < 0 or row >= len(self.servers):
            return
        server = self.servers[row]
        name = server.get("name", server.get("ip", "Unknown"))
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除服务器 \"{name}\" 吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            server_id = server.get("id")
            if self.config_mgr.delete_server(server_id):
                self._refresh_table()
                self._append_log("系统", f"已删除服务器: {name}")
            else:
                QMessageBox.critical(self, "错误", "删除失败，服务器不存在")

    def _delete_selected(self):
        selected = []
        for i in range(self.server_table.rowCount()):
            widget = self.server_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    if 0 <= i < len(self.servers):
                        selected.append(self.servers[i])

        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个服务器节点")
            return

        count = len(selected)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {count} 个服务器吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ids = [s.get("id") for s in selected]
            removed = self.config_mgr.delete_servers(ids)
            self._refresh_table()
            self._append_log("系统", f"已删除 {removed} 个服务器")

    def _import_servers(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入服务器配置", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()
            count = self.config_mgr.import_servers(json_str)
            self._refresh_table()
            self._append_log("系统", f"已导入 {count} 个服务器节点")
            if count == 0:
                QMessageBox.warning(self, "提示", "未找到有效的服务器配置")
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"导入失败: {str(exc)}")

    def _export_servers(self):
        selected = self._get_selected_servers()
        if selected:
            json_str = self.config_mgr.export_servers([s.get("id") for s in selected])
        else:
            json_str = self.config_mgr.export_servers()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出服务器配置", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        if not file_path.endswith(".json"):
            file_path += ".json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            self._append_log("系统", f"已导出服务器配置到: {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"导出失败: {str(exc)}")

    def closeEvent(self, event):
        if self._command_thread and self._command_thread.isRunning():
            self._command_thread.stop()
            self._command_thread.wait()
        if self._status_thread and self._status_thread.isRunning():
            self._status_thread.stop()
            self._status_thread.wait()
        event.accept()
