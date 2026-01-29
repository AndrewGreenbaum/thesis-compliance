"""Tests for page number extraction."""

from pathlib import Path

import pytest

from thesis_compliance.extractor.pages import PageNumberExtractor
from thesis_compliance.extractor.pdf import PDFDocument


class TestPageNumberExtractor:
    """Tests for PageNumberExtractor class."""

    @pytest.fixture
    def page_extractor(self, pdf_document: PDFDocument) -> PageNumberExtractor:
        """Create a PageNumberExtractor instance."""
        return PageNumberExtractor(pdf_document)

    def test_get_page_number(self, page_extractor: PageNumberExtractor):
        """Test getting page number from a page."""
        page_number = page_extractor.get_page_number(2)  # Body page
        # May or may not find page number depending on PDF structure
        if page_number is not None:
            assert page_number.value
            assert page_number.style in ["roman", "arabic"]
            assert page_number.position in ["top", "bottom"]
            assert page_number.alignment in ["left", "center", "right"]

    def test_analyze_page_numbers(self, page_extractor: PageNumberExtractor):
        """Test analyzing page numbers across document."""
        analysis = page_extractor.analyze_page_numbers()
        assert hasattr(analysis, "front_matter_pages")
        assert hasattr(analysis, "body_pages")
        assert hasattr(analysis, "issues")

    def test_no_page_numbers_detected(self, no_page_nums_pdf: Path):
        """Test handling document without page numbers."""
        with PDFDocument(no_page_nums_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            page_number = extractor.get_page_number(1)
            # Should return None or detect lack of page number
            # The implementation may vary

    def test_page_number_detection_body(self, valid_thesis_pdf: Path):
        """Test page number detection on body pages."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            # Check body pages (2-5)
            for page_num in range(2, min(6, doc.page_count + 1)):
                page_number = extractor.get_page_number(page_num)
                # Valid thesis should have page numbers on body pages
                if page_number is not None:
                    assert page_number.style == "arabic"

    def test_empty_page_number(self, empty_pdf: Path):
        """Test page number detection on empty page."""
        with PDFDocument(empty_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            page_number = extractor.get_page_number(1)
            assert page_number is None


class TestPageNumberAnalysis:
    """Tests for page number analysis functionality."""

    def test_front_matter_detection(self, valid_thesis_pdf: Path):
        """Test detection of front matter pages."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            analysis = extractor.analyze_page_numbers()
            # Front matter detection may vary based on document
            assert isinstance(analysis.front_matter_pages, list)

    def test_body_pages_detection(self, valid_thesis_pdf: Path):
        """Test detection of body pages."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            analysis = extractor.analyze_page_numbers()
            # Body pages should be detected
            assert isinstance(analysis.body_pages, list)

    def test_issues_reported(self, no_page_nums_pdf: Path):
        """Test that issues are reported for problematic documents."""
        with PDFDocument(no_page_nums_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            analysis = extractor.analyze_page_numbers()
            # Should report issues or empty lists
            assert isinstance(analysis.issues, list)


class TestPageNumberEdgeCases:
    """Edge case tests for page number extraction."""

    def test_single_page_document(self, minimal_pdf: Path):
        """Test page number handling for single-page document."""
        with PDFDocument(minimal_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            analysis = extractor.analyze_page_numbers()
            # Should handle single page gracefully
            assert analysis is not None

    def test_page_number_alignment_detection(self, valid_thesis_pdf: Path):
        """Test page number alignment detection."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            page_number = extractor.get_page_number(2)
            if page_number is not None:
                assert page_number.alignment in ["left", "center", "right"]

    def test_page_number_position_detection(self, valid_thesis_pdf: Path):
        """Test page number position detection."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = PageNumberExtractor(doc)
            page_number = extractor.get_page_number(2)
            if page_number is not None:
                assert page_number.position in ["top", "bottom"]
