import asyncio
from PySide6.QtCore import QThread, Signal
from core.status_checker import StatusChecker


class StatusThread(QThread):
    status_checked = Signal(str, bool)
    finished_all = Signal()

    def __init__(self, servers: list, parent=None):
        super().__init__(parent)
        self.servers = servers
        self._loop = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._check_all())
        except Exception:
            pass
        finally:
            self._loop.close()
            self.finished_all.emit()

    async def _check_all(self):
        checker = StatusChecker()

        def _callback(host, is_online):
            self.status_checked.emit(host, is_online)

        await checker.check_batch(self.servers, callback=_callback)

    def stop(self):
        if self._loop and self._loop.is_running():
            self._loop.stop()
