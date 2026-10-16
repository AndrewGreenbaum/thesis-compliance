"""Offline regression tests for PDF limits, safe connections, and cleanup."""

import asyncio
import http.client
import io
import socket
from unittest.mock import Mock

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from thesis_compliance import api, download


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("These tests must not make network requests")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(download._PinnedConnection, "connect", unexpected)


class Response:
    def __init__(self, body=b"%PDF-example", status=200, headers=None):
        self.status = status
        self.body = io.BytesIO(body)
        self.headers = headers or {}

    def getheader(self, name):
        return self.headers.get(name)

    def read1(self, amount):
        return self.body.read(amount)


@pytest.fixture
def connections(monkeypatch):
    created = []
    responses = []

    class Connection:
        def __init__(self, host, port, address, tls, timeout):
            self.host, self.port, self.address = host, port, address
            self.tls, self.timeout = tls, timeout
            self.sock = Mock()
            self.closed = False
            created.append(self)

        def request(self, method, target, headers):
            self.request_args = (method, target, headers)

        def getresponse(self):
            return responses.pop(0)

        def close(self):
            self.closed = True

    monkeypatch.setattr(download, "_PinnedConnection", Connection)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))
        ],
    )
    return created, responses


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "169.254.169.254",
        "::1",
        "100.64.0.1",
        "224.0.0.1",
        "::ffff:127.0.0.1",
    ],
)
def test_private_dns_answers_are_blocked(monkeypatch, tmp_path, connections, address):
    created, _ = connections
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))],
    )
    with pytest.raises(download.DownloadError, match="non-public"):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert not created


def test_mixed_dns_answers_are_blocked(monkeypatch, tmp_path, connections):
    created, _ = connections
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))
            for ip in ["8.8.8.8", "192.168.1.2"]
        ],
    )
    with pytest.raises(download.DownloadError):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert not created


def test_redirect_to_private_destination_is_blocked(tmp_path, connections):
    created, responses = connections
    responses.append(Response(status=302, headers={"Location": "http://127.0.0.1/private"}))
    with pytest.raises(download.DownloadError):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert len(created) == 1
    assert created[0].closed


def test_redirect_hostname_is_resolved_again(monkeypatch, tmp_path, connections):
    created, responses = connections
    lookups = []

    def resolve(host, port, **kwargs):
        lookups.append(host)
        address = "8.8.8.8" if host == "example.com" else "10.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    responses.append(Response(status=302, headers={"Location": "https://internal.test/paper.pdf"}))
    with pytest.raises(download.DownloadError):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert lookups == ["example.com", "internal.test"]
    assert len(created) == 1


def test_relative_redirect_and_query_preserved(tmp_path, connections):
    created, responses = connections
    responses.extend([Response(status=302, headers={"Location": "/new.pdf?token=x"}), Response()])
    output = tmp_path / "paper.pdf"
    download.download_pdf("https://example.com/old.pdf", output)
    assert output.read_bytes() == b"%PDF-example"
    assert created[-1].request_args[1] == "/new.pdf?token=x"
    assert all(connection.closed for connection in created)
    assert all(0 < connection.timeout <= download.REQUEST_TIMEOUT for connection in created)


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "1000"}])
def test_download_size_is_bounded(tmp_path, connections, headers):
    created, responses = connections
    responses.append(Response(body=b"x" * 1000, headers=headers))
    output = tmp_path / "paper.pdf"
    with pytest.raises(download.PDFTooLargeError):
        download.download_pdf("https://example.com/paper.pdf", output, max_bytes=10)
    assert not output.exists() or output.stat().st_size <= 10
    assert created[0].closed


def test_redirect_loop_is_bounded(tmp_path, connections):
    created, responses = connections
    responses.extend(
        Response(status=302, headers={"Location": "/again.pdf"})
        for _ in range(download.MAX_REDIRECTS + 1)
    )
    with pytest.raises(download.DownloadError, match="Too many"):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert len(created) == download.MAX_REDIRECTS + 1
    assert all(connection.closed for connection in created)


def test_read_timeout_closes_connection(tmp_path, connections):
    created, responses = connections
    response = Response()
    response.read1 = Mock(side_effect=TimeoutError("timed out"))
    responses.append(response)
    with pytest.raises(download.DownloadError):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert created[0].closed


def test_early_eof_with_declared_length_is_rejected(tmp_path, connections):
    created, responses = connections
    sock = Mock()
    sock.makefile.return_value = io.BytesIO(
        b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\nConnection: close\r\n\r\n%PDF-short"
    )
    response = http.client.HTTPResponse(sock)
    response.begin()
    responses.append(response)
    with pytest.raises(download.DownloadError, match="declared length"):
        download.download_pdf("https://example.com/paper.pdf", tmp_path / "paper.pdf")
    assert created[0].closed


def test_complete_declared_length_is_accepted(tmp_path, connections):
    _, responses = connections
    body = b"%PDF-example"
    responses.append(Response(body=body, headers={"Content-Length": str(len(body))}))
    output = tmp_path / "paper.pdf"
    download.download_pdf("https://example.com/paper.pdf", output)
    assert output.read_bytes() == body


def test_spec_metadata_cannot_read_local_yaml(monkeypatch, tmp_path):
    (tmp_path / "private-test.yaml").write_text(
        "name: internal-test\nuniversity: synthetic-private-metadata\n"
        "description: should-not-be-listed\n"
    )
    monkeypatch.chdir(tmp_path)
    client = TestClient(api.app)
    for name in ["private-test.yaml", "private-test"]:
        response = client.get(f"/specs/{name}")
        assert response.status_code == 404
        assert "synthetic-private-metadata" not in response.text
    assert client.get("/specs/rackham").status_code == 200


def test_pinned_tls_uses_checked_ip_and_original_hostname(monkeypatch):
    # Restore only this method; socket creation and TLS stay mocked.
    monkeypatch.undo()
    sock, context = Mock(), Mock()
    monkeypatch.setattr(socket, "socket", Mock(return_value=sock))
    monkeypatch.setattr(socket, "getaddrinfo", Mock(side_effect=AssertionError("Unexpected DNS")))
    monkeypatch.setattr(download.ssl, "create_default_context", Mock(return_value=context))
    connection = download._PinnedConnection("example.com", 443, "8.8.8.8", True, 10)
    connection.connect()
    sock.connect.assert_called_once_with(("8.8.8.8", 443))
    sock.settimeout.assert_called_once_with(10)
    context.wrap_socket.assert_called_once_with(sock, server_hostname="example.com")
    assert connection.sock is context.wrap_socket.return_value
    connection.close()


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@example.com/file.pdf",
        "https://example.com:0/file.pdf",
        "https://example.com:bad/",
        "https://example.com/\r\nHost:localhost",
        "http://[fe80::1%eth0]/",
    ],
)
def test_malformed_or_credential_urls_are_rejected(url):
    with pytest.raises(download.DownloadError):
        download.validate_url(url)


def test_failed_download_removes_partial_file(monkeypatch):
    paths = []

    def fail(url, path, **kwargs):
        paths.append(path)
        path.write_bytes(b"partial")
        raise download.DownloadError("Download interrupted")

    monkeypatch.setattr(api, "download_pdf", fail)
    response = TestClient(api.app).post("/check/url", params={"url": "https://example.com/a.pdf"})
    assert response.status_code == 400
    assert paths and all(not path.exists() and not path.parent.exists() for path in paths)


def test_url_success_cleans_file_and_omits_query(monkeypatch, valid_thesis_pdf):
    paths = []

    def copy(url, path, **kwargs):
        paths.append(path)
        path.write_bytes(valid_thesis_pdf.read_bytes())

    monkeypatch.setattr(api, "download_pdf", copy)
    response = TestClient(api.app).post(
        "/check/url", params={"url": "https://example.com/my%20thesis.pdf?secret=hidden"}
    )
    assert response.status_code == 200
    assert response.json()["pdf_name"] == "my thesis.pdf"
    assert not paths[0].parent.exists()


@pytest.mark.parametrize("route", ["upload", "url"])
def test_invalid_pdf_is_a_useful_client_error(monkeypatch, route):
    paths = []

    def invalid(url, path, **kwargs):
        paths.append(path)
        path.write_bytes(b"not a PDF")

    monkeypatch.setattr(api, "download_pdf", invalid)
    client = TestClient(api.app)
    if route == "upload":
        response = client.post("/check", files={"file": ("bad.pdf", b"not a PDF")})
    else:
        response = client.post("/check/url", params={"url": "https://example.com/bad.pdf"})
    assert response.status_code == 400
    assert response.json()["detail"] == "File is not a readable PDF"
    assert all(not path.parent.exists() for path in paths)


def test_upload_length_is_rejected(monkeypatch):
    monkeypatch.setattr(api, "MAX_PDF_BYTES", 10)
    response = TestClient(api.app).post("/check", files={"file": ("large.pdf", b"x" * 11)})
    assert response.status_code == 413


def test_unknown_upload_length_streams_in_chunks_and_cleans_up(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "MAX_PDF_BYTES", 10)
    monkeypatch.setattr(api, "CHUNK_BYTES", 4)
    monkeypatch.setattr(api.tempfile, "tempdir", str(tmp_path))
    upload = UploadFile(file=io.BytesIO(b"x" * 11), filename="large.pdf", size=None)
    reads = []
    original_read = upload.read

    async def read(size=-1):
        reads.append(size)
        return await original_read(size)

    upload.read = read
    with pytest.raises(HTTPException) as raised:
        asyncio.run(api.check_thesis(upload, "rackham", None))
    assert raised.value.status_code == 413
    assert reads and set(reads) == {4}
    assert list(tmp_path.iterdir()) == []


def test_upload_write_failure_cleans_up(monkeypatch, tmp_path):
    monkeypatch.setattr(api.tempfile, "tempdir", str(tmp_path))
    upload = UploadFile(file=io.BytesIO(b""), filename="bad.pdf", size=None)

    async def fail(size=-1):
        raise OSError("private local path details")

    upload.read = fail
    with pytest.raises(HTTPException) as raised:
        asyncio.run(api.check_thesis(upload, "rackham", None))
    assert raised.value.status_code == 500
    assert raised.value.detail == "Could not check the PDF"
    assert list(tmp_path.iterdir()) == []
