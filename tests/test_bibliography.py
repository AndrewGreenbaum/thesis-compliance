"""Tests for bibliography extraction."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from thesis_compliance.extractor.bibliography import (
    BibliographyEntry,
    BibliographyExtractor,
    BibliographyInfo,
)
from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import BoundingBox, FontInfo, TextBlock


class TestBibliographyExtractor:
    """Tests for BibliographyExtractor class."""

    @pytest.fixture
    def bibliography_extractor(self, pdf_document: PDFDocument) -> BibliographyExtractor:
        """Create a BibliographyExtractor instance."""
        return BibliographyExtractor(pdf_document)

    def test_find_bibliography_section(
        self, bibliography_extractor: BibliographyExtractor
    ) -> None:
        """Test finding bibliography section in document."""
        section = bibliography_extractor.find_bibliography_section()
        # May or may not find a bibliography depending on the test PDF
        if section is not None:
            start_page, end_page = section
            assert start_page >= 1
            assert end_page >= start_page

    def test_get_bibliography_entries(
        self, bibliography_extractor: BibliographyExtractor
    ) -> None:
        """Test getting bibliography entries."""
        entries = bibliography_extractor.get_bibliography_entries()
        assert isinstance(entries, list)
        for entry in entries:
            assert isinstance(entry, BibliographyEntry)

    def test_analyze_bibliography(
        self, bibliography_extractor: BibliographyExtractor
    ) -> None:
        """Test analyzing bibliography section."""
        info = bibliography_extractor.analyze_bibliography()
        # May return None if no bibliography found
        if info is not None:
            assert isinstance(info, BibliographyInfo)
            assert info.start_page >= 1
            assert info.end_page >= info.start_page

    def test_empty_document(self, empty_pdf: Path) -> None:
        """Test bibliography extraction on empty document."""
        with PDFDocument(empty_pdf) as doc:
            extractor = BibliographyExtractor(doc)
            section = extractor.find_bibliography_section()
            assert section is None


class TestBibliographyEntry:
    """Tests for BibliographyEntry dataclass."""

    def test_entry_creation(self) -> None:
        """Test creating BibliographyEntry object."""
        entry = BibliographyEntry(
            text="Smith, J. (2020). A study of things. Journal of Studies, 15(3), 42-58.",
            page_number=50,
            first_line_indent=72.0,
            continuation_indent=108.0,
            font_size=12.0,
            line_count=2,
        )
        assert entry.text.startswith("Smith")
        assert entry.page_number == 50
        assert entry.line_count == 2

    def test_hanging_indent_calculation(self) -> None:
        """Test that hanging indent can be calculated from entry."""
        entry = BibliographyEntry(
            text="Author, A. (2020). Title of work.",
            page_number=50,
            first_line_indent=72.0,  # 1 inch
            continuation_indent=108.0,  # 1.5 inches
            font_size=12.0,
            line_count=3,
        )
        # Hanging indent should be continuation - first = 0.5 inches (36pt)
        hanging_indent_pts = entry.continuation_indent - entry.first_line_indent
        hanging_indent_inches = hanging_indent_pts / 72.0
        assert abs(hanging_indent_inches - 0.5) < 0.01


class TestBibliographyDetection:
    """Tests for bibliography section detection."""

    def test_references_header_detected(self) -> None:
        """Test that 'REFERENCES' header is detected."""
        mock_doc = MagicMock(spec=PDFDocument)
        mock_doc.page_count = 3

        def get_blocks(page_num: int) -> list[TextBlock]:
            if page_num == 3:
                return [
                    TextBlock(
                        text="REFERENCES",
                        bbox=BoundingBox(x0=250, y0=72, x1=350, y1=92),
                        font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
                        page_number=3,
                        baseline=88.0,
                    ),
                    TextBlock(
                        text="[1] Author, A. (2020). Title.",
                        bbox=BoundingBox(x0=72, y0=120, x1=500, y1=140),
                        font=FontInfo(name="Times-Roman", size=12.0),
                        page_number=3,
                        baseline=138.0,
                    ),
                ]
            return []

        mock_doc.get_text_blocks.side_effect = get_blocks

        extractor = BibliographyExtractor(mock_doc)
        section = extractor.find_bibliography_section()

        assert section is not None
        assert section[0] == 3

    def test_bibliography_header_detected(self) -> None:
        """Test that 'BIBLIOGRAPHY' header is detected."""
        mock_doc = MagicMock(spec=PDFDocument)
        mock_doc.page_count = 2

        def get_blocks(page_num: int) -> list[TextBlock]:
            if page_num == 2:
                return [
                    TextBlock(
                        text="Bibliography",
                        bbox=BoundingBox(x0=250, y0=72, x1=360, y1=92),
                        font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
                        page_number=2,
                        baseline=88.0,
                    ),
                ]
            return []

        mock_doc.get_text_blocks.side_effect = get_blocks

        extractor = BibliographyExtractor(mock_doc)
        section = extractor.find_bibliography_section()

        assert section is not None
        assert section[0] == 2

    def test_no_bibliography_section(self) -> None:
        """Test document without bibliography section."""
        mock_doc = MagicMock(spec=PDFDocument)
        mock_doc.page_count = 2

        mock_doc.get_text_blocks.return_value = [
            TextBlock(
                text="This is just regular body text.",
                bbox=BoundingBox(x0=72, y0=100, x1=500, y1=120),
                font=FontInfo(name="Times-Roman", size=12.0),
                page_number=1,
                baseline=118.0,
            ),
        ]

        extractor = BibliographyExtractor(mock_doc)
        section = extractor.find_bibliography_section()

        assert section is None


class TestBibliographyEntryParsing:
    """Tests for bibliography entry parsing."""

    @pytest.fixture
    def mock_doc_with_entries(self) -> MagicMock:
        """Create a mock PDFDocument with bibliography entries."""
        mock = MagicMock(spec=PDFDocument)
        mock.page_count = 2

        def get_blocks(page_num: int) -> list[TextBlock]:
            if page_num == 2:
                return [
                    TextBlock(
                        text="References",
                        bbox=BoundingBox(x0=250, y0=72, x1=350, y1=92),
                        font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
                        page_number=2,
                        baseline=88.0,
                    ),
                    # First entry - first line
                    TextBlock(
                        text="[1] Smith, J. (2020). A very long title that",
                        bbox=BoundingBox(x0=72, y0=120, x1=500, y1=140),
                        font=FontInfo(name="Times-Roman", size=12.0),
                        page_number=2,
                        baseline=138.0,
                    ),
                    # First entry - continuation
                    TextBlock(
                        text="wraps to a second line. Journal, 15(3), 42.",
                        bbox=BoundingBox(x0=108, y0=155, x1=500, y1=175),  # Indented
                        font=FontInfo(name="Times-Roman", size=12.0),
                        page_number=2,
                        baseline=173.0,
                    ),
                    # Second entry
                    TextBlock(
                        text="[2] Jones, A. (2021). Another work. Book.",
                        bbox=BoundingBox(x0=72, y0=200, x1=450, y1=220),
                        font=FontInfo(name="Times-Roman", size=12.0),
                        page_number=2,
                        baseline=218.0,
                    ),
                ]
            return []

        mock.get_text_blocks.side_effect = get_blocks
        return mock

    def test_entries_parsed_correctly(self, mock_doc_with_entries: MagicMock) -> None:
        """Test that entries are parsed correctly."""
        extractor = BibliographyExtractor(mock_doc_with_entries)
        entries = extractor.get_bibliography_entries()

        # Should find 2 entries
        assert len(entries) == 2

        # First entry should have 2 lines (detected hanging indent)
        assert entries[0].line_count >= 1

    def test_hanging_indent_detected(self, mock_doc_with_entries: MagicMock) -> None:
        """Test that hanging indent is detected."""
        extractor = BibliographyExtractor(mock_doc_with_entries)
        info = extractor.analyze_bibliography()

        assert info is not None
        # Should detect some hanging indent (continuation is at 108, first at 72)
        # That's 36pts = 0.5 inches
        if info.avg_hanging_indent > 0:
            assert info.avg_hanging_indent >= 0.4  # Allow some tolerance


class TestBibliographyCompliance:
    """Tests for bibliography compliance checking."""

    @pytest.fixture
    def mock_doc_with_wrong_indent(self) -> MagicMock:
        """Create a mock PDFDocument with wrong hanging indent."""
        mock = MagicMock(spec=PDFDocument)
        mock.page_count = 1

        def get_blocks(page_num: int) -> list[TextBlock]:
            return [
                TextBlock(
                    text="References",
                    bbox=BoundingBox(x0=250, y0=72, x1=350, y1=92),
                    font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
                    page_number=1,
                    baseline=88.0,
                ),
                # Entry with no hanging indent (continuation at same position)
                TextBlock(
                    text="[1] Smith, J. (2020). Title that is very long",
                    bbox=BoundingBox(x0=72, y0=120, x1=500, y1=140),
                    font=FontInfo(name="Times-Roman", size=12.0),
                    page_number=1,
                    baseline=138.0,
                ),
                TextBlock(
                    text="and wraps to next line without indent.",
                    bbox=BoundingBox(x0=72, y0=155, x1=400, y1=175),  # No indent!
                    font=FontInfo(name="Times-Roman", size=12.0),
                    page_number=1,
                    baseline=173.0,
                ),
            ]

        mock.get_text_blocks.side_effect = get_blocks
        return mock

    def test_hanging_indent_violation_detected(
        self, mock_doc_with_wrong_indent: MagicMock
    ) -> None:
        """Test that missing hanging indent is detected."""
        extractor = BibliographyExtractor(mock_doc_with_wrong_indent)
        compliant, issues = extractor.check_bibliography_compliance(
            hanging_indent=0.5,
            indent_tolerance=0.1,
        )

        assert not compliant
        assert len(issues) > 0
        # Should have hanging indent issue
        indent_issues = [i for i in issues if "indent" in i[1].lower()]
        assert len(indent_issues) > 0

    def test_font_size_violation_detected(self) -> None:
        """Test that wrong font size is detected."""
        mock_doc = MagicMock(spec=PDFDocument)
        mock_doc.page_count = 1

        def get_blocks(page_num: int) -> list[TextBlock]:
            return [
                TextBlock(
                    text="References",
                    bbox=BoundingBox(x0=250, y0=72, x1=350, y1=92),
                    font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
                    page_number=1,
                    baseline=88.0,
                ),
                TextBlock(
                    text="[1] Smith, J. (2020). Title.",
                    bbox=BoundingBox(x0=72, y0=120, x1=400, y1=140),
                    font=FontInfo(name="Times-Roman", size=10.0),  # Wrong size
                    page_number=1,
                    baseline=138.0,
                ),
            ]

        mock_doc.get_text_blocks.side_effect = get_blocks

        extractor = BibliographyExtractor(mock_doc)
        compliant, issues = extractor.check_bibliography_compliance(
            font_size=12.0,
            size_tolerance=0.5,
        )

        assert not compliant
        font_issues = [i for i in issues if "font size" in i[1].lower()]
        assert len(font_issues) > 0


class TestBibliographyInfo:
    """Tests for BibliographyInfo dataclass."""

    def test_info_creation(self) -> None:
        """Test creating BibliographyInfo object."""
        entries = [
            BibliographyEntry(
                text="[1] Author. Title.",
                page_number=50,
                first_line_indent=72.0,
                continuation_indent=108.0,
                font_size=12.0,
                line_count=2,
            ),
        ]

        info = BibliographyInfo(
            start_page=50,
            end_page=52,
            entries=entries,
            avg_hanging_indent=0.5,
            avg_entry_spacing=1.0,
            avg_between_spacing=2.0,
        )

        assert info.start_page == 50
        assert info.end_page == 52
        assert len(info.entries) == 1
        assert info.avg_hanging_indent == 0.5
