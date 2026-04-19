import asyncio
import asyncssh
import logging
from typing import Optional
from asyncssh.connection import SSHConnection

logger = logging.getLogger(__name__)


class SSHManager:
    def __init__(self, host: str, port: int, user: str, password: Optional[str] = None, key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.key_path = key_path
        self._conn: Optional[SSHConnection] = None

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
                connect_timeout=10
            )
            logger.info(f"SSH connected to {self.host}:{self.port}")
            return self._conn
        except asyncssh.Error as exc:
            logger.error(f"SSH connection failed for {self.host}: {exc}")
            raise

    async def close(self):
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
            logger.info(f"SSH connection closed for {self.host}")

    async def execute(self, command: str) -> str:
        if not self._conn:
            await self.connect()
        try:
            result = await self._conn.run(command, check=True)
            return result.stdout
        except asyncssh.Error as exc:
            logger.error(f"SSH execute failed on {self.host}: {exc}")
            raise

    async def check_online(self) -> bool:
        try:
            conn = await self.connect()
            await conn.close()
            return True
        except Exception:
            return False
