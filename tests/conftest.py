"""Shared pytest fixtures for thesis compliance tests."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from thesis_compliance.checker.engine import ThesisChecker
from thesis_compliance.extractor import PDFDocument
from thesis_compliance.models import RuleType, Severity, Violation
from thesis_compliance.spec import SpecLoader, StyleSpec


# Directory containing test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def ensure_test_pdfs() -> None:
    """Ensure test PDF fixtures exist before running tests."""
    from tests.fixtures.generate_pdfs import generate_all

    # Check if any PDF exists; if not, generate all
    if not any(FIXTURES_DIR.glob("*.pdf")):
        generate_all()


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def valid_thesis_pdf() -> Path:
    """Return path to a valid thesis PDF."""
    path = FIXTURES_DIR / "valid_thesis.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_valid_thesis
        create_valid_thesis()
    return path


@pytest.fixture
def bad_margins_pdf() -> Path:
    """Return path to a PDF with bad margins."""
    path = FIXTURES_DIR / "bad_margins.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_bad_margins
        create_bad_margins()
    return path


@pytest.fixture
def wrong_font_pdf() -> Path:
    """Return path to a PDF with wrong font."""
    path = FIXTURES_DIR / "wrong_font.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_wrong_font
        create_wrong_font()
    return path


@pytest.fixture
def single_spaced_pdf() -> Path:
    """Return path to a single-spaced PDF."""
    path = FIXTURES_DIR / "single_spaced.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_single_spaced
        create_single_spaced()
    return path


@pytest.fixture
def no_page_nums_pdf() -> Path:
    """Return path to a PDF without page numbers."""
    path = FIXTURES_DIR / "no_page_nums.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_no_page_numbers
        create_no_page_numbers()
    return path


@pytest.fixture
def minimal_pdf() -> Path:
    """Return path to a minimal single-page PDF."""
    path = FIXTURES_DIR / "minimal.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_minimal_pdf
        create_minimal_pdf()
    return path


@pytest.fixture
def empty_pdf() -> Path:
    """Return path to an empty PDF (blank pages)."""
    path = FIXTURES_DIR / "empty.pdf"
    if not path.exists():
        from tests.fixtures.generate_pdfs import create_empty_pdf
        create_empty_pdf()
    return path


@pytest.fixture
def pdf_document(valid_thesis_pdf: Path) -> Generator[PDFDocument, None, None]:
    """Provide an open PDFDocument for testing."""
    doc = PDFDocument(valid_thesis_pdf)
    yield doc
    doc.close()


@pytest.fixture
def rackham_spec() -> StyleSpec:
    """Return the Rackham style specification."""
    return SpecLoader.load("rackham")


@pytest.fixture
def default_spec() -> StyleSpec:
    """Return the default style specification."""
    return SpecLoader.get_default_spec()


@pytest.fixture
def thesis_checker(valid_thesis_pdf: Path, rackham_spec: StyleSpec) -> Generator[ThesisChecker, None, None]:
    """Provide a ThesisChecker instance for testing."""
    checker = ThesisChecker(valid_thesis_pdf, rackham_spec)
    yield checker
    checker.close()


@pytest.fixture
def sample_violation() -> Violation:
    """Return a sample violation for testing."""
    return Violation(
        rule_id="test.rule",
        rule_type=RuleType.MARGIN,
        severity=Severity.ERROR,
        message="Test violation message",
        page=1,
        expected="expected value",
        found="found value",
        suggestion="Test suggestion",
    )


@pytest.fixture
def temp_pdf_path() -> Generator[Path, None, None]:
    """Provide a temporary path for creating test PDFs."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_yaml_path() -> Generator[Path, None, None]:
    """Provide a temporary path for creating test YAML specs."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()
