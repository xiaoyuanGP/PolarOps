from PySide6.QtCore import Qt, QPoint, QEvent, QObject
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QMouseEvent


class _DragEventFilter(QObject):
    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        self._drag_pos = None

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if event.position().y() <= 40:
                self._drag_pos = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
                return False
        elif et == QEvent.MouseMove and event.buttons() == Qt.LeftButton:
            if self._drag_pos is not None:
                self._parent.move(event.globalPosition().toPoint() - self._drag_pos)
                return False
        elif et == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self._drag_pos = None
            return False
        return super().eventFilter(obj, event)


class DraggableWindowMixin:
    def setup_draggable(self):
        self._drag_filter = _DragEventFilter(self)
        self.installEventFilter(self._drag_filter)
        self._apply_drag_to_children(self)

    def _apply_drag_to_children(self, parent):
        for child in parent.children():
            if isinstance(child, QWidget):
                child.installEventFilter(self._drag_filter)
                self._apply_drag_to_children(child)
