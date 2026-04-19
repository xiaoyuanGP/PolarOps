import socket
import struct
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

SERVERDATA_EXECTECOMMAND = 2
SERVERDATA_AUTH = 3
SERVERDATA_RESPONSE_VALUE = 0
SERVERDATA_AUTH_RESPONSE = 2


class RconManager:
    def __init__(self, host: str, port: int, password: str, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._authenticated = False
        self._request_id = 0

    def connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            auth_response = self._send_auth(self.password)
            if auth_response is not None and auth_response.strip() == "":
                self._authenticated = True
                return True
            elif auth_response is not None and "authenticated" in auth_response.lower():
                self._authenticated = True
                return True
            return False
        except Exception as exc:
            logger.error(f"RCON connection failed for {self.host}:{self.port}: {exc}")
            self.close()
            return False

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
            self._authenticated = False

    def _make_packet(self, request_id: int, req_type: int, body: str) -> bytes:
        body_bytes = body.encode("utf-8")
        packet = struct.pack("<ii", request_id, req_type) + body_bytes + b"\x00\x00"
        header = struct.pack("<i", len(packet))
        return header + packet

    def _recv_packet(self) -> Tuple[int, int, str]:
        header_data = self._sock.recv(4)
        if len(header_data) < 4:
            raise ConnectionError("Failed to read packet header")
        packet_length = struct.unpack("<i", header_data)[0]
        data = b""
        while len(data) < packet_length:
            chunk = self._sock.recv(packet_length - len(data))
            if not chunk:
                break
            data += chunk
        if len(data) < 8:
            raise ConnectionError("Invalid packet data")
        request_id, req_type = struct.unpack("<ii", data[:8])
        body = data[8:].split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        return request_id, req_type, body

    def _send_auth(self, password: str) -> Optional[str]:
        self._request_id += 1
        packet = self._make_packet(self._request_id, SERVERDATA_AUTH, password)
        self._sock.sendall(packet)
        try:
            req_id, req_type, body = self._recv_packet()
            if req_type == SERVERDATA_AUTH_RESPONSE:
                return body
        except socket.timeout:
            return None
        return None

    def _send_command(self, command: str) -> Optional[str]:
        if not self._authenticated:
            return None
        self._request_id += 1
        packet = self._make_packet(self._request_id, SERVERDATA_EXECTECOMMAND, command)
        self._sock.sendall(packet)
        try:
            req_id, req_type, body = self._recv_packet()
            if req_type == SERVERDATA_RESPONSE_VALUE:
                return body
        except socket.timeout:
            return None
        return None

    def get_players(self) -> Optional[List[str]]:
        try:
            if not self._sock:
                if not self.connect():
                    return None
            response = self._send_command("Status")
            if response is None:
                response = self._send_command("listPlayers")
            if response is None:
                return None
            players = []
            for line in response.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    is_number = False
                    try:
                        int(parts[0])
                        is_number = True
                    except ValueError:
                        pass
                    if is_number and "@" not in parts[0]:
                        name_part = " ".join(parts[1:])
                        players.append(name_part)
                    elif "#" in parts[0] or "@" in parts[0]:
                        name_part = " ".join(parts[1:])
                        if name_part and name_part != "":
                            players.append(name_part)
            if not players:
                for line in response.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("hostname") and not line.startswith("version"):
                        if ":" in line:
                            pass
                        else:
                            players.append(line)
            return players if players else None
        except Exception as exc:
            logger.error(f"RCON get_players failed: {exc}")
            return None

    def get_player_count(self) -> Optional[int]:
        players = self.get_players()
        if players is not None:
            return len(players)
        return None

    def send_command(self, command: str) -> Optional[str]:
        try:
            if not self._sock:
                if not self.connect():
                    return None
            return self._send_command(command)
        except Exception as exc:
            logger.error(f"RCON send_command failed: {exc}")
            return None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
