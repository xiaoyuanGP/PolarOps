from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget,
                               QTreeWidgetItem, QLabel, QPushButton, QMessageBox,
                               QWidget, QHeaderView, QFileDialog, QProgressBar)
from PySide6.QtGui import QGuiApplication, QIcon
import os
from ui.draggable import DraggableWindowMixin

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
IMG_PATH = os.path.join(BASE_DIR, "img", "透明.png")


class _SSHFileThread(QThread):
    files_loaded = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, server, path="/"):
        super().__init__()
        self.server = server
        self.path = path

    def run(self):
        try:
            import asyncio
            from core.ssh_manager import SSHManager

            async def _list_files():
                mgr = SSHManager(
                    host=self.server["ip"],
                    port=self.server.get("port", 22),
                    user=self.server["user"],
                    password=self.server.get("password") if self.server.get("auth_type") == "password" else None,
                    key_path=self.server.get("key_path") if self.server.get("auth_type") == "key" else None
                )
                result = await mgr.execute(f'ls -la --time-style=long-iso "{self.path}" 2>/dev/null || echo "ERROR"')
                await mgr.close()
                return result

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(_list_files())
            finally:
                loop.close()

            if result.strip() == "ERROR":
                self.error_occurred.emit(f"无法访问目录: {self.path}")
                return

            files = []
            for line in result.strip().split('\n'):
                if not line or line.startswith('total '):
                    continue
                parts = line.split(None, 7)
                if len(parts) < 8:
                    continue
                perms, links, owner, group, size, date, time_str, name = parts
                is_dir = perms.startswith('d')
                is_link = perms.startswith('l')
                files.append({
                    "name": name,
                    "is_dir": is_dir,
                    "is_link": is_link,
                    "size": size,
                    "date": f"{date} {time_str}",
                    "perms": perms,
                    "owner": owner
                })

            self.files_loaded.emit(files)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class FileBrowserDialog(QDialog, DraggableWindowMixin):
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self._server = server
        self._current_path = "/"
        self._loading = False
        self._thread = None
        self.setWindowTitle(f"文件浏览器 - {server['name']} ({server['ip']})")
        self.setFixedSize(800, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_ui()
        self._center_on_screen()
        self._load_files("/")

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
        content_layout.setSpacing(10)

        # 路径栏
        path_layout = QHBoxLayout()
        path_label = QLabel("路径:")
        path_label.setStyleSheet("color: #a0a5b0; font-size: 13px;")
        path_layout.addWidget(path_label)

        self.path_input = QLabel("/")
        self.path_input.setObjectName("loginInput")
        self.path_input.setMinimumHeight(32)
        self.path_input.setStyleSheet("padding: 0 10px;")
        path_layout.addWidget(self.path_input)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.setMinimumHeight(32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh)
        path_layout.addWidget(self.refresh_btn)

        self.up_btn = QPushButton("上级目录")
        self.up_btn.setObjectName("secondaryButton")
        self.up_btn.setMinimumHeight(32)
        self.up_btn.setCursor(Qt.PointingHandCursor)
        self.up_btn.clicked.connect(self._go_up)
        path_layout.addWidget(self.up_btn)

        self.home_btn = QPushButton("根目录")
        self.home_btn.setObjectName("secondaryButton")
        self.home_btn.setMinimumHeight(32)
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.clicked.connect(lambda: self._navigate("/"))
        path_layout.addWidget(self.home_btn)

        content_layout.addLayout(path_layout)

        # 文件树
        self.file_tree = QTreeWidget()
        self.file_tree.setObjectName("serverTable")
        self.file_tree.setHeaderLabels(["名称", "大小", "修改时间", "权限", "所有者"])
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.file_tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.file_tree.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.file_tree.header().setSectionResizeMode(4, QHeaderView.Fixed)
        self.file_tree.setColumnWidth(1, 100)
        self.file_tree.setColumnWidth(2, 150)
        self.file_tree.setColumnWidth(3, 100)
        self.file_tree.setColumnWidth(4, 80)
        self.file_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.file_tree.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.file_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        content_layout.addWidget(self.file_tree)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.download_btn = QPushButton("下载选中")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.setMinimumHeight(36)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self._download_selected)
        btn_layout.addWidget(self.download_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        content_layout.addLayout(btn_layout)

        main_layout.addWidget(content_widget)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

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

        title_label = QLabel(f"文件浏览器 - {self._server['name']}")
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

    def _load_files(self, path):
        if self._loading:
            return
        self._loading = True
        self._current_path = path
        self.path_input.setText(path)
        self.file_tree.clear()

        self.refresh_btn.setEnabled(False)
        self.up_btn.setEnabled(False)
        self.home_btn.setEnabled(False)
        self.file_tree.setEnabled(False)

        if self._thread and self._thread.isRunning():
            self._thread.terminate()
            self._thread.wait()

        self._thread = _SSHFileThread(self._server, path)
        self._thread.files_loaded.connect(self._on_files_loaded)
        self._thread.error_occurred.connect(self._on_error)
        self._thread.finished.connect(self._on_load_finished)
        self._thread.start()

    def _on_load_finished(self):
        self._loading = False
        self.refresh_btn.setEnabled(True)
        self.up_btn.setEnabled(True)
        self.home_btn.setEnabled(True)
        self.file_tree.setEnabled(True)

    def _on_files_loaded(self, files):
        self.file_tree.clear()

        # 添加 . 和 ..
        if self._current_path != "/":
            up_item = QTreeWidgetItem(["..", "", "", "", ""])
            up_item.setForeground(0, Qt.gray)
            up_item.setData(0, Qt.UserRole, "..")
            up_item.setData(0, Qt.UserRole + 1, True)
            self.file_tree.addTopLevelItem(up_item)

        # 分离目录和文件
        dirs = [f for f in files if f["is_dir"] and f["name"] not in (".", "..")]
        files_only = [f for f in files if not f["is_dir"] and not f["is_link"]]

        # 添加目录
        for d in sorted(dirs, key=lambda x: x["name"]):
            item = QTreeWidgetItem([
                f"📁 {d['name']}",
                "-",
                d["date"],
                d["perms"],
                d["owner"]
            ])
            item.setData(0, Qt.UserRole, d["name"])
            item.setData(0, Qt.UserRole + 1, True)
            self.file_tree.addTopLevelItem(item)

        # 添加文件
        for f in sorted(files_only, key=lambda x: x["name"]):
            item = QTreeWidgetItem([
                f"📄 {f['name']}",
                self._format_size(f["size"]),
                f["date"],
                f["perms"],
                f["owner"]
            ])
            item.setData(0, Qt.UserRole, f["name"])
            item.setData(0, Qt.UserRole + 1, False)
            self.file_tree.addTopLevelItem(item)

    def _on_item_double_clicked(self, item, column):
        if item is None:
            return
        name = item.data(0, Qt.UserRole)
        if name is None:
            return
        is_dir = item.data(0, Qt.UserRole + 1)

        if name == "..":
            self._go_up()
        elif is_dir:
            if self._current_path.endswith("/"):
                new_path = self._current_path + name
            else:
                new_path = self._current_path + "/" + name
            self._navigate(new_path)

    def _navigate(self, path):
        self._load_files(path)

    def _go_up(self):
        if self._current_path == "/":
            return
        try:
            stripped = self._current_path.rstrip("/")
            if not stripped:
                self._navigate("/")
                return
            idx = stripped.rfind("/")
            if idx <= 0:
                parent = "/"
            else:
                parent = stripped[:idx]
            self._navigate(parent)
        except Exception:
            self._navigate("/")

    def _refresh(self):
        self._load_files(self._current_path)

    def _format_size(self, size_str):
        try:
            size = int(size_str)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.1f} GB"
        except:
            return size_str

    def _download_selected(self):
        items = self.file_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "提示", "请先选择要下载的文件")
            return

        item = items[0]
        name = item.data(0, Qt.UserRole)
        is_dir = item.data(0, Qt.UserRole + 1)

        if is_dir:
            QMessageBox.warning(self, "提示", "暂不支持下载目录")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", name, "All Files (*)"
        )
        if not save_path:
            return

        self._download_file(name, save_path)

    def _download_file(self, remote_name, local_path):
        try:
            import asyncio
            from core.ssh_manager import SSHManager

            remote_path = self._current_path.rstrip("/") + "/" + remote_name

            async def _download():
                mgr = SSHManager(
                    host=self._server["ip"],
                    port=self._server.get("port", 22),
                    user=self._server["user"],
                    password=self._server.get("password") if self._server.get("auth_type") == "password" else None,
                    key_path=self._server.get("key_path") if self._server.get("auth_type") == "key" else None
                )
                # 使用 cat 命令获取文件内容
                result = await mgr.execute(f'cat "{remote_path}"')
                await mgr.close()
                return result

            loop = asyncio.new_event_loop()
            try:
                content = loop.run_until_complete(_download())
            finally:
                loop.close()

            with open(local_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(content)

            QMessageBox.information(self, "成功", f"文件已保存到:\n{local_path}")
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"下载失败:\n{str(exc)}")

    def _on_error(self, error_msg):
        QMessageBox.critical(self, "错误", f"加载文件失败:\n{error_msg}")
