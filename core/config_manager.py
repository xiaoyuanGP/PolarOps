import os
import json
import uuid
from typing import List, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or CONFIG_PATH
        self._config: Dict = {}
        self._load()

    def _load(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._config = {"servers": [], "users": {"admin": "admin123"}}
            self._save()

    def _save(self):
        temp_path = self.config_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=4)
        os.replace(temp_path, self.config_path)

    def get_servers(self) -> List[Dict]:
        return self._config.get("servers", [])

    def get_users(self) -> Dict:
        return self._config.get("users", {})

    def get_all_config(self) -> Dict:
        return self._config.copy()

    def add_server(self, server: Dict) -> Dict:
        if "id" not in server or not server["id"]:
            server["id"] = str(uuid.uuid4())[:8]
        self._config.setdefault("servers", []).append(server)
        self._save()
        return server

    def update_server(self, server_id: str, updated: Dict) -> Optional[Dict]:
        servers = self._config.get("servers", [])
        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                for key in ("name", "ip", "port", "user", "password", "auth_type", "key_path", "rcon_ip", "rcon_port", "rcon_password"):
                    if key in updated:
                        servers[i][key] = updated[key]
                self._config["servers"] = servers
                self._save()
                return servers[i]
        return None

    def delete_server(self, server_id: str) -> bool:
        servers = self._config.get("servers", [])
        new_servers = [s for s in servers if s.get("id") != server_id]
        if len(new_servers) == len(servers):
            return False
        self._config["servers"] = new_servers
        self._save()
        return True

    def delete_servers(self, server_ids: List[str]) -> int:
        servers = self._config.get("servers", [])
        id_set = set(server_ids)
        new_servers = [s for s in servers if s.get("id") not in id_set]
        removed = len(servers) - len(new_servers)
        if removed > 0:
            self._config["servers"] = new_servers
            self._save()
        return removed

    def export_servers(self, server_ids: Optional[List[str]] = None) -> str:
        servers = self._config.get("servers", [])
        if server_ids:
            id_set = set(server_ids)
            servers = [s for s in servers if s.get("id") in id_set]
        return json.dumps(servers, ensure_ascii=False, indent=4)

    def import_servers(self, json_str: str) -> int:
        try:
            imported = json.loads(json_str)
            if not isinstance(imported, list):
                return 0
            count = 0
            for server in imported:
                if isinstance(server, dict) and "ip" in server and "user" in server:
                    self.add_server({
                        "id": str(uuid.uuid4())[:8],
                        "name": server.get("name", server.get("ip", "Unknown")),
                        "ip": server["ip"],
                        "port": server.get("port", 22),
                        "user": server.get("user", "root"),
                        "auth_type": server.get("auth_type", "password"),
                        "password": server.get("password", ""),
                        "key_path": server.get("key_path", "")
                    })
                    count += 1
            return count
        except json.JSONDecodeError:
            return 0
