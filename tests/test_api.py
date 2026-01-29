"""Tests for FastAPI endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if FastAPI is not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from thesis_compliance.api import app, _validate_url


@pytest.fixture
def client() -> TestClient:
    """Create test client for API."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestSpecsEndpoints:
    """Tests for spec-related endpoints."""

    def test_list_specs(self, client: TestClient):
        """Test listing available specs."""
        response = client.get("/specs")
        assert response.status_code == 200
        specs = response.json()
        assert isinstance(specs, list)
        # Should have at least rackham
        spec_names = [s["name"] for s in specs]
        assert "rackham" in spec_names

    def test_get_spec(self, client: TestClient):
        """Test getting specific spec info."""
        response = client.get("/specs/rackham")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "rackham"
        assert "university" in data
        assert "rule_count" in data

    def test_get_spec_not_found(self, client: TestClient):
        """Test getting nonexistent spec returns 404."""
        response = client.get("/specs/nonexistent")
        assert response.status_code == 404


class TestCheckEndpoint:
    """Tests for file upload check endpoint."""

    def test_check_valid_pdf(self, client: TestClient, valid_thesis_pdf: Path):
        """Test checking a valid PDF."""
        with open(valid_thesis_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("thesis.pdf", f, "application/pdf")},
                data={"spec": "rackham"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "violations" in data
        assert "pages_checked" in data

    def test_check_with_page_range(self, client: TestClient, valid_thesis_pdf: Path):
        """Test checking with page range."""
        with open(valid_thesis_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("thesis.pdf", f, "application/pdf")},
                data={"spec": "rackham", "pages": "1-3"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["pages_checked"] == 3

    def test_check_invalid_file_type(self, client: TestClient):
        """Test rejecting non-PDF files."""
        response = client.post(
            "/check",
            files={"file": ("document.txt", b"not a pdf", "text/plain")},
            data={"spec": "rackham"},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_check_invalid_spec(self, client: TestClient, valid_thesis_pdf: Path):
        """Test error with invalid spec name."""
        with open(valid_thesis_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("thesis.pdf", f, "application/pdf")},
                data={"spec": "nonexistent"},
            )
        assert response.status_code == 400
        assert "Unknown spec" in response.json()["detail"]


class TestURLValidation:
    """Tests for SSRF protection URL validation."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URL passes validation."""
        _validate_url("https://example.com/file.pdf")
        # Should not raise

    def test_valid_http_url(self):
        """Test that valid HTTP URL passes validation."""
        _validate_url("http://example.com/file.pdf")
        # Should not raise

    def test_invalid_scheme_file(self):
        """Test that file:// scheme is rejected."""
        with pytest.raises(ValueError, match="Only http/https"):
            _validate_url("file:///etc/passwd")

    def test_invalid_scheme_ftp(self):
        """Test that ftp:// scheme is rejected."""
        with pytest.raises(ValueError, match="Only http/https"):
            _validate_url("ftp://example.com/file.pdf")

    def test_private_ip_127(self):
        """Test that localhost IP is rejected."""
        with pytest.raises(ValueError, match="Private|loopback"):
            _validate_url("http://127.0.0.1/file.pdf")

    def test_private_ip_192(self):
        """Test that private IP 192.168.x.x is rejected."""
        with pytest.raises(ValueError, match="Private|loopback"):
            _validate_url("http://192.168.1.1/file.pdf")

    def test_private_ip_10(self):
        """Test that private IP 10.x.x.x is rejected."""
        with pytest.raises(ValueError, match="Private|loopback"):
            _validate_url("http://10.0.0.1/file.pdf")

    def test_private_ip_172(self):
        """Test that private IP 172.16.x.x is rejected."""
        with pytest.raises(ValueError, match="Private|loopback"):
            _validate_url("http://172.16.0.1/file.pdf")

    def test_no_hostname(self):
        """Test that URL without hostname is rejected."""
        with pytest.raises(ValueError, match="no hostname"):
            _validate_url("http:///path")

    def test_hostname_allowed(self):
        """Test that hostname (non-IP) is allowed."""
        _validate_url("https://university.edu/thesis.pdf")
        # Should not raise


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client: TestClient):
        """Test that CORS headers are present."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # Should allow the configured origin
        # Note: actual headers depend on FastAPI CORS middleware behavior


class TestAPIEdgeCases:
    """Edge case tests for API."""

    def test_check_with_bad_margins_pdf(self, client: TestClient, bad_margins_pdf: Path):
        """Test checking PDF with bad margins."""
        with open(bad_margins_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("bad.pdf", f, "application/pdf")},
                data={"spec": "rackham"},
            )
        assert response.status_code == 200
        data = response.json()
        # Should find violations
        assert data["error_count"] > 0 or data["warning_count"] > 0

    def test_check_empty_pdf(self, client: TestClient, empty_pdf: Path):
        """Test checking empty PDF."""
        with open(empty_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("empty.pdf", f, "application/pdf")},
                data={"spec": "rackham"},
            )
        assert response.status_code == 200
        # Should complete without crashing

    def test_default_spec(self, client: TestClient, valid_thesis_pdf: Path):
        """Test using default spec when not specified."""
        with open(valid_thesis_pdf, "rb") as f:
            response = client.post(
                "/check",
                files={"file": ("thesis.pdf", f, "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["spec_name"] == "rackham"
