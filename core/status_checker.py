import asyncio
import asyncssh
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class StatusChecker:
    async def check_single(self, host: str, port: int, user: str, password: Optional[str] = None, key_path: Optional[str] = None) -> bool:
        client_keys = [key_path] if key_path else []
        try:
            conn = await asyncssh.connect(
                host=host,
                port=port,
                username=user,
                password=password,
                client_keys=client_keys,
                known_hosts=None,
                connect_timeout=5
            )
            conn.close()
            await conn.wait_closed()
            return True
        except Exception:
            return False

    async def check_batch(self, servers: List[Dict], callback=None) -> List[Tuple[str, bool]]:
        results = []

        async def _check_one(server):
            is_online = await self.check_single(
                host=server["ip"],
                port=server.get("port", 22),
                user=server["user"],
                password=server.get("password") if server.get("auth_type") == "password" else None,
                key_path=server.get("key_path") if server.get("auth_type") == "key" else None
            )
            result = (server["ip"], is_online)
            results.append(result)
            if callback:
                callback(server["ip"], is_online)

        tasks = [_check_one(s) for s in servers]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results
