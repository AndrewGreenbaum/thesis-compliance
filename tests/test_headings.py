"""Tests for heading extraction."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from thesis_compliance.extractor.headings import HeadingExtractor, HeadingInfo
from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import BoundingBox, FontInfo, TextBlock


class TestHeadingExtractor:
    """Tests for HeadingExtractor class."""

    @pytest.fixture
    def heading_extractor(self, pdf_document: PDFDocument) -> HeadingExtractor:
        """Create a HeadingExtractor instance."""
        return HeadingExtractor(pdf_document)

    def test_get_headings_on_page(self, heading_extractor: HeadingExtractor) -> None:
        """Test getting headings from a single page."""
        headings = heading_extractor.get_headings_on_page(1)
        assert isinstance(headings, list)
        for heading in headings:
            assert isinstance(heading, HeadingInfo)
            assert heading.level in (1, 2, 3)
            assert heading.page_number == 1

    def test_get_all_headings(self, heading_extractor: HeadingExtractor) -> None:
        """Test getting all headings in document."""
        all_headings = heading_extractor.get_all_headings()
        assert isinstance(all_headings, dict)
        for page_num, headings in all_headings.items():
            assert isinstance(page_num, int)
            assert isinstance(headings, list)

    def test_get_headings_specific_pages(self, heading_extractor: HeadingExtractor) -> None:
        """Test getting headings for specific pages."""
        headings = heading_extractor.get_all_headings(pages=[1, 2])
        assert isinstance(headings, dict)
        # Should only have pages 1 and/or 2
        for page_num in headings:
            assert page_num in (1, 2)

    def test_check_heading_compliance(self, heading_extractor: HeadingExtractor) -> None:
        """Test checking heading compliance."""
        compliant, issues = heading_extractor.check_heading_compliance(
            chapter_font_size=14.0,
            chapter_bold=True,
            chapter_all_caps=True,
            section_font_size=12.0,
            section_bold=True,
            size_tolerance=1.0,
        )
        assert isinstance(compliant, bool)
        assert isinstance(issues, list)

    def test_empty_document(self, empty_pdf: Path) -> None:
        """Test heading extraction on empty document."""
        with PDFDocument(empty_pdf) as doc:
            extractor = HeadingExtractor(doc)
            headings = extractor.get_all_headings()
            assert len(headings) == 0


class TestHeadingInfo:
    """Tests for HeadingInfo dataclass."""

    def test_heading_info_creation(self) -> None:
        """Test creating HeadingInfo object."""
        heading = HeadingInfo(
            text="CHAPTER 1: INTRODUCTION",
            level=1,
            page_number=5,
            font_size=14.0,
            is_bold=True,
            is_italic=False,
            is_all_caps=True,
            y_position=144.0,
            space_before=144.0,
        )
        assert heading.text == "CHAPTER 1: INTRODUCTION"
        assert heading.level == 1
        assert heading.is_bold is True
        assert heading.is_all_caps is True


class TestHeadingClassification:
    """Tests for heading classification logic."""

    @pytest.fixture
    def mock_doc(self) -> MagicMock:
        """Create a mock PDFDocument."""
        mock = MagicMock(spec=PDFDocument)
        mock.page_count = 10
        return mock

    def test_chapter_pattern_detected(self, mock_doc: MagicMock) -> None:
        """Test that CHAPTER X pattern is detected as level 1."""
        # Create a text block that looks like a chapter heading
        chapter_block = TextBlock(
            text="CHAPTER 1",
            bbox=BoundingBox(x0=72, y0=100, x1=200, y1=120),
            font=FontInfo(name="Times-Bold", size=14.0, is_bold=True),
            page_number=5,
            baseline=118.0,
        )

        mock_doc.get_text_blocks.return_value = [chapter_block]
        mock_doc.get_page_info.return_value = MagicMock(height_pt=792.0)

        extractor = HeadingExtractor(mock_doc)
        headings = extractor.get_headings_on_page(5)

        assert len(headings) == 1
        assert headings[0].level == 1
        assert headings[0].text == "CHAPTER 1"

    def test_section_pattern_detected(self, mock_doc: MagicMock) -> None:
        """Test that 1.1 Section pattern is detected as level 2."""
        section_block = TextBlock(
            text="1.1 Background",
            bbox=BoundingBox(x0=72, y0=200, x1=300, y1=220),
            font=FontInfo(name="Times-Bold", size=12.0, is_bold=True),
            page_number=6,
            baseline=218.0,
        )

        mock_doc.get_text_blocks.return_value = [section_block]
        mock_doc.get_page_info.return_value = MagicMock(height_pt=792.0)

        extractor = HeadingExtractor(mock_doc)
        headings = extractor.get_headings_on_page(6)

        assert len(headings) == 1
        assert headings[0].level == 2

    def test_subsection_pattern_detected(self, mock_doc: MagicMock) -> None:
        """Test that 1.1.1 Subsection pattern is detected as level 3."""
        subsection_block = TextBlock(
            text="1.1.1 Detailed Background",
            bbox=BoundingBox(x0=72, y0=300, x1=350, y1=320),
            font=FontInfo(name="Times-Italic", size=12.0, is_italic=True),
            page_number=6,
            baseline=318.0,
        )

        mock_doc.get_text_blocks.return_value = [subsection_block]
        mock_doc.get_page_info.return_value = MagicMock(height_pt=792.0)

        extractor = HeadingExtractor(mock_doc)
        headings = extractor.get_headings_on_page(6)

        assert len(headings) == 1
        assert headings[0].level == 3

    def test_regular_text_not_heading(self, mock_doc: MagicMock) -> None:
        """Test that regular body text is not classified as heading."""
        body_block = TextBlock(
            text="This is regular body text that should not be a heading.",
            bbox=BoundingBox(x0=72, y0=400, x1=500, y1=420),
            font=FontInfo(name="Times-Roman", size=12.0, is_bold=False),
            page_number=6,
            baseline=418.0,
        )

        mock_doc.get_text_blocks.return_value = [body_block]
        mock_doc.get_page_info.return_value = MagicMock(height_pt=792.0)

        extractor = HeadingExtractor(mock_doc)
        headings = extractor.get_headings_on_page(6)

        assert len(headings) == 0


class TestHeadingCompliance:
    """Tests for heading compliance checking."""

    @pytest.fixture
    def mock_doc(self) -> MagicMock:
        """Create a mock PDFDocument with chapter heading."""
        mock = MagicMock(spec=PDFDocument)
        mock.page_count = 1

        # Create a chapter heading with wrong font size
        chapter_block = TextBlock(
            text="CHAPTER 1: INTRODUCTION",
            bbox=BoundingBox(x0=72, y0=100, x1=300, y1=125),
            font=FontInfo(name="Times-Bold", size=12.0, is_bold=True),  # Should be 14pt
            page_number=1,
            baseline=120.0,
        )

        mock.get_text_blocks.return_value = [chapter_block]
        mock.get_page_info.return_value = MagicMock(height_pt=792.0)

        return mock

    def test_font_size_violation_detected(self, mock_doc: MagicMock) -> None:
        """Test that wrong font size is detected."""
        extractor = HeadingExtractor(mock_doc)
        compliant, issues = extractor.check_heading_compliance(
            chapter_font_size=14.0,
            chapter_bold=True,
            chapter_all_caps=True,
            size_tolerance=0.5,
        )

        assert not compliant
        assert len(issues) > 0
        assert "font size" in issues[0][2].lower()

    def test_missing_bold_detected(self) -> None:
        """Test that missing bold is detected."""
        mock_doc = MagicMock(spec=PDFDocument)
        mock_doc.page_count = 1

        # Chapter heading without bold
        chapter_block = TextBlock(
            text="CHAPTER 1: INTRODUCTION",
            bbox=BoundingBox(x0=72, y0=100, x1=300, y1=125),
            font=FontInfo(name="Times-Roman", size=14.0, is_bold=False),  # Not bold
            page_number=1,
            baseline=120.0,
        )

        mock_doc.get_text_blocks.return_value = [chapter_block]
        mock_doc.get_page_info.return_value = MagicMock(height_pt=792.0)

        extractor = HeadingExtractor(mock_doc)
        compliant, issues = extractor.check_heading_compliance(
            chapter_font_size=14.0,
            chapter_bold=True,
            chapter_all_caps=True,
            size_tolerance=0.5,
        )

        assert not compliant
        # Should have at least one bold-related issue
        bold_issues = [i for i in issues if "bold" in i[2].lower()]
        assert len(bold_issues) > 0
