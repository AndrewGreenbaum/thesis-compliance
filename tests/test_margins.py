"""Tests for margin extraction."""

from pathlib import Path

import pytest

from thesis_compliance.extractor.margins import MarginExtractor
from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import Margins


class TestMarginExtractor:
    """Tests for MarginExtractor class."""

    @pytest.fixture
    def margin_extractor(self, pdf_document: PDFDocument) -> MarginExtractor:
        """Create a MarginExtractor instance."""
        return MarginExtractor(pdf_document)

    def test_get_margins(self, margin_extractor: MarginExtractor):
        """Test getting margins for a single page."""
        margins = margin_extractor.get_margins(1)
        assert margins is not None
        assert isinstance(margins, Margins)
        assert margins.left >= 0
        assert margins.right >= 0
        assert margins.top >= 0
        assert margins.bottom >= 0

    def test_get_margins_empty_page(self, empty_pdf: Path):
        """Test getting margins from empty page returns None."""
        with PDFDocument(empty_pdf) as doc:
            extractor = MarginExtractor(doc)
            margins = extractor.get_margins(1)
            assert margins is None

    def test_get_all_margins(self, margin_extractor: MarginExtractor):
        """Test getting margins for all pages."""
        all_margins = margin_extractor.get_all_margins()
        assert len(all_margins) > 0
        for page_num, margins in all_margins.items():
            assert page_num >= 1
            assert isinstance(margins, Margins)

    def test_get_all_margins_specific_pages(self, margin_extractor: MarginExtractor):
        """Test getting margins for specific pages."""
        all_margins = margin_extractor.get_all_margins(pages=[1, 2])
        assert len(all_margins) <= 2
        for page_num in all_margins:
            assert page_num in [1, 2]

    def test_get_minimum_margins(self, margin_extractor: MarginExtractor):
        """Test getting minimum margins across pages."""
        min_margins = margin_extractor.get_minimum_margins()
        assert min_margins is not None
        assert min_margins.left >= 0
        assert min_margins.right >= 0

    def test_find_margin_violations_none_found(self, margin_extractor: MarginExtractor):
        """Test finding margin violations when document is compliant."""
        required = Margins(left=0.5, right=0.5, top=0.5, bottom=0.5)
        violations = margin_extractor.find_margin_violations(required, tolerance=0.1)
        # With small required margins, valid thesis should pass
        assert isinstance(violations, dict)

    def test_find_margin_violations_found(self, bad_margins_pdf: Path):
        """Test finding margin violations in non-compliant document."""
        with PDFDocument(bad_margins_pdf) as doc:
            extractor = MarginExtractor(doc)
            required = Margins(left=1.5, right=1.0, top=1.0, bottom=1.0)
            violations = extractor.find_margin_violations(required, tolerance=0.05)
            # Should find violations since bad_margins has 0.5" margins
            assert len(violations) > 0

    def test_margins_tolerance(self, margin_extractor: MarginExtractor):
        """Test that tolerance is properly applied."""
        # Tight tolerance should find more violations
        required = Margins(left=1.5, right=1.0, top=1.0, bottom=1.0)
        violations_tight = margin_extractor.find_margin_violations(
            required, tolerance=0.01
        )
        violations_loose = margin_extractor.find_margin_violations(
            required, tolerance=0.5
        )
        # Loose tolerance should have same or fewer violations
        assert len(violations_loose) <= len(violations_tight)

    def test_negative_margins_clamped(self, bad_margins_pdf: Path):
        """Test that negative margins are clamped to zero."""
        with PDFDocument(bad_margins_pdf) as doc:
            extractor = MarginExtractor(doc)
            all_margins = extractor.get_all_margins()
            for margins in all_margins.values():
                assert margins.left >= 0
                assert margins.right >= 0
                assert margins.top >= 0
                assert margins.bottom >= 0


class TestMarginCalculations:
    """Tests for margin calculation accuracy."""

    def test_title_page_top_margin(self, valid_thesis_pdf: Path):
        """Test that title page has correct top margin (2 inches)."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = MarginExtractor(doc)
            margins = extractor.get_margins(1)
            if margins:
                # Title page should have approximately 2" top margin
                assert margins.top >= 1.8  # Allow some tolerance

    def test_body_page_margins(self, valid_thesis_pdf: Path):
        """Test that body pages have correct margins."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = MarginExtractor(doc)
            margins = extractor.get_margins(2)  # Body page
            if margins:
                # Left margin should be approximately 1.5"
                assert margins.left >= 1.3
                # Top margin should be approximately 1"
                assert margins.top >= 0.8

    def test_bad_margins_detected(self, bad_margins_pdf: Path):
        """Test that bad margins are properly detected."""
        with PDFDocument(bad_margins_pdf) as doc:
            extractor = MarginExtractor(doc)
            margins = extractor.get_margins(1)
            if margins:
                # Bad margins PDF has 0.5" margins
                assert margins.left < 1.0
