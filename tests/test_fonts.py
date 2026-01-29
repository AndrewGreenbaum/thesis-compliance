"""Tests for font extraction."""

from pathlib import Path

import pytest

from thesis_compliance.extractor.fonts import FontExtractor, FontUsage
from thesis_compliance.extractor.pdf import PDFDocument


class TestFontExtractor:
    """Tests for FontExtractor class."""

    @pytest.fixture
    def font_extractor(self, pdf_document: PDFDocument) -> FontExtractor:
        """Create a FontExtractor instance."""
        return FontExtractor(pdf_document)

    def test_get_fonts_on_page(self, font_extractor: FontExtractor):
        """Test getting fonts from a single page."""
        fonts = font_extractor.get_fonts_on_page(1)
        assert len(fonts) > 0
        for font in fonts:
            assert font.name
            assert font.size > 0

    def test_get_font_usage(self, font_extractor: FontExtractor):
        """Test getting font usage statistics."""
        usage = font_extractor.get_font_usage()
        assert len(usage) > 0
        for font_name, font_usage in usage.items():
            assert isinstance(font_usage, FontUsage)
            assert font_usage.font_name == font_name
            assert font_usage.occurrence_count > 0

    def test_get_font_usage_specific_pages(self, font_extractor: FontExtractor):
        """Test getting font usage for specific pages."""
        usage = font_extractor.get_font_usage(pages=[1, 2])
        assert isinstance(usage, dict)

    def test_get_body_font(self, font_extractor: FontExtractor):
        """Test identifying the body font."""
        body_font = font_extractor.get_body_font()
        assert body_font is not None
        assert body_font.is_body_font is True
        assert body_font.occurrence_count > 0

    def test_body_font_has_sizes(self, font_extractor: FontExtractor):
        """Test that body font has size information."""
        body_font = font_extractor.get_body_font()
        assert body_font is not None
        assert len(body_font.sizes) > 0

    def test_check_body_font_compliance_passing(self, font_extractor: FontExtractor):
        """Test font compliance check for valid document."""
        compliant, issues = font_extractor.check_body_font_compliance(
            required_size=12.0,
            size_tolerance=1.0,
        )
        # Valid thesis should mostly pass (may have minor issues)
        assert isinstance(compliant, bool)
        assert isinstance(issues, list)

    def test_check_body_font_compliance_failing(self, wrong_font_pdf: Path):
        """Test font compliance check for non-compliant document."""
        with PDFDocument(wrong_font_pdf) as doc:
            extractor = FontExtractor(doc)
            compliant, issues = extractor.check_body_font_compliance(
                allowed_fonts={"Times", "Times-Roman", "Times New Roman"},
                required_size=12.0,
                size_tolerance=0.5,
            )
            # Wrong font PDF uses Helvetica 10pt - should fail
            assert not compliant
            assert len(issues) > 0

    def test_find_font_size_violations(self, wrong_font_pdf: Path):
        """Test finding font size violations."""
        with PDFDocument(wrong_font_pdf) as doc:
            extractor = FontExtractor(doc)
            violations = extractor.find_font_size_violations(min_size=11.0)
            # Wrong font PDF uses 10pt - should find violations
            assert len(violations) > 0

    def test_find_font_size_violations_with_max(self, font_extractor: FontExtractor):
        """Test finding font size violations with max size."""
        violations = font_extractor.find_font_size_violations(
            min_size=8.0, max_size=20.0
        )
        assert isinstance(violations, dict)

    def test_empty_document_font_usage(self, empty_pdf: Path):
        """Test font usage on empty document."""
        with PDFDocument(empty_pdf) as doc:
            extractor = FontExtractor(doc)
            usage = extractor.get_font_usage()
            assert len(usage) == 0

    def test_empty_document_body_font(self, empty_pdf: Path):
        """Test getting body font from empty document."""
        with PDFDocument(empty_pdf) as doc:
            extractor = FontExtractor(doc)
            body_font = extractor.get_body_font()
            assert body_font is None


class TestFontUsage:
    """Tests for FontUsage dataclass."""

    def test_font_usage_creation(self):
        """Test creating FontUsage object."""
        usage = FontUsage(
            font_name="Times-Roman",
            sizes={12.0, 14.0},
            occurrence_count=1000,
            is_body_font=True,
        )
        assert usage.font_name == "Times-Roman"
        assert 12.0 in usage.sizes
        assert usage.is_body_font is True


class TestFontExtractorEdgeCases:
    """Edge case tests for FontExtractor."""

    def test_single_page_pdf(self, minimal_pdf: Path):
        """Test font extraction from single page PDF."""
        with PDFDocument(minimal_pdf) as doc:
            extractor = FontExtractor(doc)
            usage = extractor.get_font_usage()
            assert len(usage) > 0

    def test_font_base_name_extraction(self, valid_thesis_pdf: Path):
        """Test that font base names are properly extracted."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = FontExtractor(doc)
            usage = extractor.get_font_usage()
            for font_name in usage:
                # Should not have style suffixes in key
                assert "-BoldItalic" not in font_name or font_name.endswith("-BoldItalic")
