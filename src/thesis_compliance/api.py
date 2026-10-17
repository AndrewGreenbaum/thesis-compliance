"""FastAPI server for thesis compliance checking."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import unquote, urlsplit

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from thesis_compliance import __version__
from thesis_compliance.checker.engine import ThesisChecker
from thesis_compliance.download import (
    CHUNK_BYTES,
    MAX_PDF_BYTES,
    DownloadError,
    PDFTooLargeError,
    download_pdf,
    validate_url,
)
from thesis_compliance.spec import SpecLoader, StyleSpec

logger = logging.getLogger(__name__)

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
    violations: list[dict[str, Any]]


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
    if name not in SpecLoader.list_builtin_specs():
        raise HTTPException(status_code=404, detail=f"Spec not found: {name}")
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


def _load_spec(name: str) -> StyleSpec:
    available = SpecLoader.list_builtin_specs()
    if name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown spec: {name}. Available: {', '.join(available)}",
        )
    return SpecLoader.load(name)


def _check_pdf(path: Path, style_spec: StyleSpec, pages: str | None, name: str) -> CheckResponse:
    try:
        checker = ThesisChecker(path, style_spec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="File is not a readable PDF") from exc
    with checker:
        try:
            report = checker.check(pages)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckResponse(
        pdf_name=name,
        spec_name=report.spec_name,
        pages_checked=report.pages_checked,
        rules_checked=report.rules_checked,
        passed=report.passed,
        error_count=len(report.errors),
        warning_count=len(report.warnings),
        violations=[v.to_dict() for v in report.violations],
    )


@app.post("/check", response_model=CheckResponse)
async def check_thesis(
    file: Annotated[UploadFile, File(description="Thesis PDF file (up to 20 MiB)")],
    spec: Annotated[str, Form(description="Style specification name")] = "rackham",
    pages: Annotated[str | None, Form(description="Page range to check")] = None,
) -> CheckResponse:
    """Check an uploaded PDF against a built-in style specification."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    style_spec = _load_spec(spec)
    if file.size is not None and file.size > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the size limit")
    try:
        with tempfile.TemporaryDirectory(prefix="thesis-check-") as directory:
            tmp_path = Path(directory) / "upload.pdf"
            total = 0
            with tmp_path.open("wb") as output:
                while chunk := await file.read(CHUNK_BYTES):
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        raise HTTPException(status_code=413, detail="PDF exceeds the size limit")
                    output.write(chunk)
            return await run_in_threadpool(_check_pdf, tmp_path, style_spec, pages, file.filename)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Uploaded PDF check failed")
        raise HTTPException(status_code=500, detail="Could not check the PDF") from exc


def _validate_url(url: str) -> None:
    """Validate syntax; the downloader also validates DNS before every connection."""
    validate_url(url)


@app.post("/check/url", response_model=CheckResponse)
def check_thesis_url(
    url: str,
    spec: str = "rackham",
    pages: str | None = None,
) -> CheckResponse:
    """Download a public PDF (up to 20 MiB) and check its formatting."""
    try:
        _validate_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    style_spec = _load_spec(spec)
    try:
        with tempfile.TemporaryDirectory(prefix="thesis-check-") as directory:
            tmp_path = Path(directory) / "download.pdf"
            download_pdf(url, tmp_path, max_bytes=MAX_PDF_BYTES)
            pdf_name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]) or "thesis.pdf"
            return _check_pdf(tmp_path, style_spec, pages, pdf_name)
    except PDFTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("URL PDF check failed")
        raise HTTPException(status_code=500, detail="Could not check the PDF") from exc


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API server on the local interface by default."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
