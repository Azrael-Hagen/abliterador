from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ServerAddress:
    ip: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.ip}:{self.port}"


def is_local_network_ip(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
        return bool(ip.is_loopback or ip.is_private or ip.is_link_local)
    except Exception:
        return False


def detect_local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()

    # Route-based detection (most accurate for active interface)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
            if is_local_network_ip(candidate):
                addresses.add(candidate)
    except Exception:
        pass

    # Hostname resolution fallback
    try:
        host = socket.gethostname()
        for _, _, _, _, sockaddr in socket.getaddrinfo(host, None, socket.AF_INET):
            candidate = sockaddr[0]
            if is_local_network_ip(candidate):
                addresses.add(candidate)
    except Exception:
        pass

    # Always include loopback for local diagnostics
    addresses.add("127.0.0.1")

    ordered = sorted(addresses, key=lambda item: (item == "127.0.0.1", item))
    return ordered


def detect_server_addresses(port: int) -> list[ServerAddress]:
    return [ServerAddress(ip=ip, port=port) for ip in detect_local_ipv4_addresses()]
