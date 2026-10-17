"""Bounded PDF downloads with explicit redirect and destination checks."""

import http.client
import ipaddress
import socket
import ssl
import time
from pathlib import Path
from urllib.parse import SplitResult, urljoin, urlsplit

MAX_PDF_BYTES = 20 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
REQUEST_TIMEOUT = 10.0
DOWNLOAD_TIMEOUT = 30.0
MAX_REDIRECTS = 5


class DownloadError(ValueError):
    """The remote document cannot be downloaded safely."""


class PDFTooLargeError(DownloadError):
    """The document exceeds the configured size limit."""


def _public_ip(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        raise DownloadError("Private, loopback, or other non-public IPs are not allowed")
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        _public_ip(str(ip.ipv4_mapped))


def validate_url(url: str) -> SplitResult:
    """Check URL syntax and literal addresses; DNS is checked before connecting."""
    if any(ord(char) < 33 or ord(char) == 127 for char in url):
        raise DownloadError("Invalid URL: whitespace or control characters")
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https"):
            raise DownloadError("Only http/https URLs allowed")
        if not parsed.hostname:
            raise DownloadError("Invalid URL: no hostname")
        if parsed.username is not None or parsed.password is not None:
            raise DownloadError("URL credentials are not allowed")
        if "%" in parsed.hostname:
            raise DownloadError("Invalid URL hostname")
        if parsed.port == 0:
            raise DownloadError("Invalid URL port")
        parsed.port  # Validate the port even when the default is used.
    except ValueError as exc:
        raise DownloadError(str(exc)) from exc
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        _public_ip(parsed.hostname)
    return parsed


def _resolve_address(hostname: str, port: int) -> str:
    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise DownloadError("Could not resolve the PDF hostname") from exc
    addresses = [str(answer[4][0]) for answer in answers]
    if not addresses:
        raise DownloadError("Could not resolve the PDF hostname")
    # Reject mixed public/private DNS answers as well as wholly private destinations.
    for address in addresses:
        _public_ip(address)
    return addresses[0]


class _PinnedConnection(http.client.HTTPConnection):
    """Connect to a checked IP while preserving the original Host header and TLS name."""

    def __init__(self, host: str, port: int, address: str, tls: bool, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self.address = address
        self.tls = tls

    def connect(self) -> None:
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect((self.address, self.port))
            if self.tls:
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
            self.sock = sock
        except BaseException:
            sock.close()
            raise


def download_pdf(url: str, destination: Path, *, max_bytes: int = MAX_PDF_BYTES) -> None:
    """Stream a public HTTP(S) document into a caller-owned temporary file.

    Each redirect is resolved and checked independently. Connections use the validated
    numeric address, so a second DNS lookup cannot redirect the connection internally.
    Socket operations time out; the deadline is also checked between streamed reads.
    System DNS resolution uses the operating system's resolver timeout.
    """
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT
    current_url = url
    try:
        for redirect in range(MAX_REDIRECTS + 1):
            parsed = validate_url(current_url)
            hostname = (parsed.hostname or "").encode("idna").decode("ascii")
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            address = _resolve_address(hostname, port)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DownloadError("PDF download timed out")
            connection = _PinnedConnection(
                hostname, port, address, parsed.scheme == "https", min(REQUEST_TIMEOUT, remaining)
            )
            try:
                target = parsed.path or "/"
                if parsed.query:
                    target += "?" + parsed.query
                connection.request("GET", target, headers={"Accept-Encoding": "identity"})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise DownloadError("PDF redirect has no destination")
                    if redirect == MAX_REDIRECTS:
                        raise DownloadError("Too many PDF redirects")
                    current_url = urljoin(current_url, location)
                    continue
                if response.status != 200:
                    raise DownloadError(f"PDF server returned HTTP {response.status}")
                length = response.getheader("Content-Length")
                declared_size = None
                if length is not None:
                    try:
                        declared_size = int(length)
                    except ValueError as exc:
                        raise DownloadError("Invalid PDF response length") from exc
                    if declared_size < 0:
                        raise DownloadError("Invalid PDF response length")
                    if declared_size > max_bytes:
                        raise PDFTooLargeError("PDF exceeds the size limit")
                total = 0
                with destination.open("wb") as output:
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise DownloadError("PDF download timed out")
                        if connection.sock is not None:
                            connection.sock.settimeout(min(REQUEST_TIMEOUT, remaining))
                        chunk = response.read1(min(CHUNK_BYTES, max_bytes - total + 1))
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise PDFTooLargeError("PDF exceeds the size limit")
                        output.write(chunk)
                if declared_size is not None and total != declared_size:
                    raise DownloadError("PDF response ended before its declared length")
                return
            finally:
                connection.close()
    except DownloadError:
        raise
    except (OSError, http.client.HTTPException, UnicodeError, ValueError) as exc:
        raise DownloadError("Could not download the PDF from this URL") from exc
