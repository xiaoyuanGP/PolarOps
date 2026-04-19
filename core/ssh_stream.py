import asyncio
import asyncssh
import logging
from typing import Optional, Callable
from asyncssh.connection import SSHConnection
from asyncssh.process import SSHClientProcess

logger = logging.getLogger(__name__)


class SSHStream:
    def __init__(self, host: str, port: int, user: str, password: Optional[str] = None, key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.key_path = key_path
        self._conn: Optional[SSHConnection] = None
        self._process: Optional[SSHClientProcess] = None

    async def connect(self) -> SSHConnection:
        client_keys = [self.key_path] if self.key_path else []
        try:
            self._conn = await asyncssh.connect(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                client_keys=client_keys,
                known_hosts=None,
                connect_timeout=10,
                keepalive_interval=30,
                keepalive_count_max=120
            )
            return self._conn
        except asyncssh.Error as exc:
            logger.error(f"SSH stream connect failed for {self.host}: {exc}")
            raise

    async def execute_streaming(self, command: str, output_callback: Callable[[str, str], None]):
        if not self._conn:
            await self.connect()
        try:
            self._process = await self._conn.create_process(
                command,
                env={
                    'TERM': 'dumb',
                    'DEBIAN_FRONTEND': 'noninteractive',
                }
            )
            # 读取 stdout 和 stderr 合并流
            async for line in self._process.stdout:
                line = line.rstrip('\n')
                if line:
                    output_callback(self.host, line)
            # 等待进程完成，设置长超时
            try:
                exit_code = await asyncio.wait_for(
                    self._process.wait(),
                    timeout=7200  # 2小时超时，适应大型安装
                )
            except asyncio.TimeoutError:
                output_callback(self.host, "[ERROR] 命令执行超时（2小时）")
                raise
            return exit_code
        except asyncssh.Error as exc:
            logger.error(f"SSH stream execute failed on {self.host}: {exc}")
            output_callback(self.host, f"[ERROR] {str(exc)}")
            raise
        except asyncio.TimeoutError:
            raise
        finally:
            await self.close()

    async def close(self):
        if self._process:
            self._process.close()
            self._process = None
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
            logger.info(f"SSH stream connection closed for {self.host}")
