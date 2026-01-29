"""Tests for PDF document extraction."""

from pathlib import Path

import pytest

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import BoundingBox, PageInfo


class TestPDFDocument:
    """Tests for PDFDocument class."""

    def test_open_valid_pdf(self, valid_thesis_pdf: Path):
        """Test opening a valid PDF file."""
        doc = PDFDocument(valid_thesis_pdf)
        assert doc.page_count > 0
        doc.close()

    def test_open_nonexistent_pdf(self):
        """Test opening a nonexistent PDF raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            PDFDocument("/nonexistent/path/to/file.pdf")

    def test_context_manager(self, valid_thesis_pdf: Path):
        """Test using PDFDocument as context manager."""
        with PDFDocument(valid_thesis_pdf) as doc:
            assert doc.page_count > 0

    def test_page_count(self, pdf_document: PDFDocument):
        """Test getting page count."""
        assert pdf_document.page_count == 5  # valid_thesis has 5 pages

    def test_get_page_info(self, pdf_document: PDFDocument):
        """Test getting page information."""
        page_info = pdf_document.get_page_info(1)
        assert isinstance(page_info, PageInfo)
        assert page_info.number == 1
        # US Letter size
        assert abs(page_info.width_inches - 8.5) < 0.1
        assert abs(page_info.height_inches - 11.0) < 0.1

    def test_iter_pages(self, pdf_document: PDFDocument):
        """Test iterating over pages."""
        pages = list(pdf_document.iter_pages())
        assert len(pages) == pdf_document.page_count
        for i, page in enumerate(pages, 1):
            assert page.number == i

    def test_get_text_blocks(self, pdf_document: PDFDocument):
        """Test extracting text blocks from a page."""
        blocks = pdf_document.get_text_blocks(1)
        assert len(blocks) > 0
        # Check that blocks have required attributes
        for block in blocks:
            assert block.text
            assert block.bbox is not None
            assert block.font is not None
            assert block.page_number == 1

    def test_get_content_bbox(self, pdf_document: PDFDocument):
        """Test getting content bounding box."""
        bbox = pdf_document.get_content_bbox(1)
        assert bbox is not None
        assert isinstance(bbox, BoundingBox)
        assert bbox.width > 0
        assert bbox.height > 0

    def test_get_content_bbox_empty_page(self, empty_pdf: Path):
        """Test getting content bbox from empty page returns None."""
        with PDFDocument(empty_pdf) as doc:
            bbox = doc.get_content_bbox(1)
            assert bbox is None

    def test_get_all_fonts(self, pdf_document: PDFDocument):
        """Test getting all fonts used in document."""
        fonts = pdf_document.get_all_fonts()
        assert len(fonts) > 0
        # Should have at least one font with sizes
        for font_name, sizes in fonts.items():
            assert isinstance(sizes, set)

    def test_get_page_text(self, pdf_document: PDFDocument):
        """Test getting plain text from a page."""
        text = pdf_document.get_page_text(1)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_text_block_font_info(self, pdf_document: PDFDocument):
        """Test that text blocks have proper font information."""
        blocks = pdf_document.get_text_blocks(2)  # Body page
        if blocks:
            block = blocks[0]
            assert block.font.name
            assert block.font.size > 0
            assert isinstance(block.font.is_bold, bool)
            assert isinstance(block.font.is_italic, bool)

    def test_text_block_baseline(self, pdf_document: PDFDocument):
        """Test that text blocks have baseline information."""
        blocks = pdf_document.get_text_blocks(1)
        if blocks:
            block = blocks[0]
            assert block.baseline > 0

    def test_minimal_pdf(self, minimal_pdf: Path):
        """Test handling minimal single-page PDF."""
        with PDFDocument(minimal_pdf) as doc:
            assert doc.page_count == 1
            blocks = doc.get_text_blocks(1)
            assert len(blocks) > 0

    def test_del_cleanup(self, valid_thesis_pdf: Path):
        """Test that __del__ properly cleans up resources."""
        doc = PDFDocument(valid_thesis_pdf)
        # This should not raise an exception
        del doc


class TestPDFDocumentEdgeCases:
    """Edge case tests for PDFDocument."""

    def test_page_number_bounds(self, pdf_document: PDFDocument):
        """Test accessing pages at boundaries."""
        # First page
        page = pdf_document.get_page_info(1)
        assert page.number == 1

        # Last page
        last = pdf_document.page_count
        page = pdf_document.get_page_info(last)
        assert page.number == last

    def test_empty_page_text_blocks(self, empty_pdf: Path):
        """Test getting text blocks from empty page."""
        with PDFDocument(empty_pdf) as doc:
            blocks = doc.get_text_blocks(1)
            assert blocks == []

    def test_empty_page_text(self, empty_pdf: Path):
        """Test getting text from empty page."""
        with PDFDocument(empty_pdf) as doc:
            text = doc.get_page_text(1)
            assert text.strip() == ""
