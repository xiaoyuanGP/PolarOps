import asyncio
import sys
from PySide6.QtCore import QThread, Signal
from core.deployer import Deployer


class CommandThread(QThread):
    log_received = Signal(str, str)
    progress_updated = Signal(int, int)
    finished_all = Signal()
    error_occurred = Signal(str)

    def __init__(self, servers: list, command: str = None, deploy_type: str = None, parent=None):
        super().__init__(parent)
        self.servers = servers
        self.command = command
        self.deploy_type = deploy_type
        self._loop = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            if self.deploy_type in ("mcsmanager", "squad"):
                self._loop.run_until_complete(self._run_deploy())
            elif self.command:
                self._loop.run_until_complete(self._run_command())
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self._loop.close()
            self.finished_all.emit()

    async def _run_command(self):
        from core.ssh_stream import SSHStream

        async def _execute_one(server):
            stream = SSHStream(
                host=server["ip"],
                port=server.get("port", 22),
                user=server["user"],
                password=server.get("password") if server.get("auth_type") == "password" else None,
                key_path=server.get("key_path") if server.get("auth_type") == "key" else None
            )

            def _callback(host, message):
                self.log_received.emit(host, message)

            try:
                await stream.execute_streaming(self.command, _callback)
            except Exception as exc:
                self.log_received.emit(server["ip"], f"[ERROR] {str(exc)}")

        completed = 0
        total = len(self.servers)

        async def _execute_with_progress(server):
            nonlocal completed
            await _execute_one(server)
            completed += 1
            self.progress_updated.emit(completed, total)

        tasks = [_execute_with_progress(s) for s in self.servers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_deploy(self):
        deployer = Deployer()

        def _callback(host, message):
            self.log_received.emit(host, message)

        def _progress(completed, total):
            self.progress_updated.emit(completed, total)

        try:
            await deployer.deploy_batch(
                servers=self.servers,
                deploy_type=self.deploy_type,
                output_callback=_callback,
                progress_callback=_progress
            )
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def stop(self):
        if self._loop and self._loop.is_running():
            self._loop.stop()
