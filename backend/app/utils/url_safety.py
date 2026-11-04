"""Outbound URL checks for the summary crawler."""
import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
}


def _is_blocked(ip_text):
    address = ipaddress.ip_address(ip_text)
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def assert_safe_http_url(url):
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("只允许 http 或 https URL")
    host = parsed.hostname.strip().lower()
    if host in _BLOCKED_HOSTS or host.endswith(".local"):
        raise ValueError("不允许访问该地址")
    literal = None
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        addresses = [host]
    else:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError("无法解析主机") from exc
        addresses = [item[4][0] for item in infos]
    for address in addresses:
        if _is_blocked(address):
            raise ValueError("不允许访问内网或本地地址")
    return url
