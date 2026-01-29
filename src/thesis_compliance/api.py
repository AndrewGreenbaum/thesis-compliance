"""FastAPI server for thesis compliance checking."""

import ipaddress
import os
import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from thesis_compliance import __version__
from thesis_compliance.checker.engine import ThesisChecker
from thesis_compliance.models import ComplianceReport
from thesis_compliance.spec import SpecLoader

app = FastAPI(
    title="Thesis Compliance API",
    description="Check thesis PDF formatting compliance against university style requirements",
    version=__version__,
)

# CORS for frontend access - configured via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpecInfo(BaseModel):
    """Information about a style specification."""

    name: str
    university: str
    description: str
    version: str
    rule_count: int


class CheckResponse(BaseModel):
    """Response from the check endpoint."""

    pdf_name: str
    spec_name: str
    pages_checked: int
    rules_checked: int
    passed: bool
    error_count: int
    warning_count: int
    violations: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/specs", response_model=list[SpecInfo])
async def list_specs() -> list[SpecInfo]:
    """List available style specifications."""
    specs = []
    for name in SpecLoader.list_builtin_specs():
        try:
            spec = SpecLoader.load(name)
            specs.append(
                SpecInfo(
                    name=spec.name,
                    university=spec.university,
                    description=spec.description,
                    version=spec.version,
                    rule_count=spec.rule_count,
                )
            )
        except Exception:
            pass
    return specs


@app.get("/specs/{name}", response_model=SpecInfo)
async def get_spec(name: str) -> SpecInfo:
    """Get information about a specific specification."""
    try:
        spec = SpecLoader.load(name)
        return SpecInfo(
            name=spec.name,
            university=spec.university,
            description=spec.description,
            version=spec.version,
            rule_count=spec.rule_count,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Spec not found: {name}")


@app.post("/check", response_model=CheckResponse)
async def check_thesis(
    file: Annotated[UploadFile, File(description="Thesis PDF file")],
    spec: Annotated[str, Form(description="Style specification name")] = "rackham",
    pages: Annotated[str | None, Form(description="Page range to check")] = None,
) -> CheckResponse:
    """Check a thesis PDF for formatting compliance.

    Upload a PDF file and specify the style specification to check against.
    Returns a detailed compliance report with any violations found.

    Parameters:
    - file: The thesis PDF file
    - spec: Style specification name (default: rackham)
    - pages: Optional page range (e.g., "1-10,20")
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate spec exists
    try:
        style_spec = SpecLoader.load(spec)
    except FileNotFoundError:
        available = SpecLoader.list_builtin_specs()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown spec: {spec}. Available: {', '.join(available)}",
        )

    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Run compliance check
    try:
        with ThesisChecker(tmp_path, style_spec) as checker:
            report = checker.check(pages)

        return CheckResponse(
            pdf_name=file.filename,
            spec_name=report.spec_name,
            pages_checked=report.pages_checked,
            rules_checked=report.rules_checked,
            passed=report.passed,
            error_count=len(report.errors),
            warning_count=len(report.warnings),
            violations=[v.to_dict() for v in report.violations],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {e}")
    finally:
        # Clean up temp file
        try:
            tmp_path.unlink()
        except Exception:
            pass


def _validate_url(url: str) -> None:
    """Validate URL to prevent SSRF attacks.

    Args:
        url: URL to validate.

    Raises:
        ValueError: If URL is not allowed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")

    # Block private/loopback IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            raise ValueError("Private/loopback/reserved IPs not allowed")
    except ValueError as e:
        if "not allowed" in str(e):
            raise
        # Not an IP address (it's a hostname) - that's OK


@app.post("/check/url", response_model=CheckResponse)
async def check_thesis_url(
    url: str,
    spec: str = "rackham",
    pages: str | None = None,
) -> CheckResponse:
    """Check a thesis PDF from a URL.

    Provide a URL to a PDF file and specify the style specification.

    Parameters:
    - url: URL to the thesis PDF
    - spec: Style specification name (default: rackham)
    - pages: Optional page range (e.g., "1-10,20")
    """
    import urllib.request

    # Validate URL to prevent SSRF
    try:
        _validate_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate spec exists
    try:
        style_spec = SpecLoader.load(spec)
    except FileNotFoundError:
        available = SpecLoader.list_builtin_specs()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown spec: {spec}. Available: {', '.join(available)}",
        )

    # Initialize tmp_path before try block to avoid NameError in finally
    tmp_path: Path | None = None

    # Download PDF
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            tmp_path = Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {e}")

    # Run compliance check
    try:
        with ThesisChecker(tmp_path, style_spec) as checker:
            report = checker.check(pages)

        # Extract filename from URL
        pdf_name = url.split("/")[-1] or "thesis.pdf"

        return CheckResponse(
            pdf_name=pdf_name,
            spec_name=report.spec_name,
            pages_checked=report.pages_checked,
            rules_checked=report.rules_checked,
            passed=report.passed,
            error_count=len(report.errors),
            warning_count=len(report.warnings),
            violations=[v.to_dict() for v in report.violations],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {e}")
    finally:
        # Clean up temp file
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
