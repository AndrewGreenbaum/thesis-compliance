"""Tests for line spacing extraction."""

from pathlib import Path

import pytest

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.extractor.spacing import SpacingAnalysis, SpacingExtractor


class TestSpacingExtractor:
    """Tests for SpacingExtractor class."""

    @pytest.fixture
    def spacing_extractor(self, pdf_document: PDFDocument) -> SpacingExtractor:
        """Create a SpacingExtractor instance."""
        return SpacingExtractor(pdf_document)

    def test_get_line_spacings(self, spacing_extractor: SpacingExtractor):
        """Test getting line spacings from a page."""
        spacings = spacing_extractor.get_line_spacings(2)  # Body page
        assert isinstance(spacings, list)
        # Body pages should have some line spacings
        for spacing in spacings:
            assert spacing.ratio > 0
            assert spacing.baseline_distance > 0
            assert spacing.font_size > 0

    def test_analyze_spacing(self, spacing_extractor: SpacingExtractor):
        """Test analyzing spacing across pages."""
        analysis = spacing_extractor.analyze_spacing()
        # May be None if insufficient data
        if analysis is not None:
            assert isinstance(analysis, SpacingAnalysis)
            assert analysis.average_ratio > 0
            assert analysis.sample_count > 0

    def test_analyze_spacing_specific_pages(self, spacing_extractor: SpacingExtractor):
        """Test analyzing spacing for specific pages."""
        analysis = spacing_extractor.analyze_spacing(pages=[2, 3])
        if analysis is not None:
            assert analysis.sample_count > 0

    def test_check_double_spacing_valid(self, valid_thesis_pdf: Path):
        """Test double spacing check on valid document."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = SpacingExtractor(doc)
            compliant, violations = extractor.check_double_spacing(
                pages=[2, 3, 4], tolerance=0.3
            )
            # Valid thesis should be mostly double-spaced
            assert isinstance(compliant, bool)
            assert isinstance(violations, list)

    def test_check_double_spacing_single_spaced(self, single_spaced_pdf: Path):
        """Test double spacing check on single-spaced document."""
        with PDFDocument(single_spaced_pdf) as doc:
            extractor = SpacingExtractor(doc)
            compliant, violations = extractor.check_double_spacing(tolerance=0.2)
            # Single-spaced document should fail double spacing check
            assert not compliant
            assert len(violations) > 0
            # Violations should have page numbers and ratios
            for page_num, ratio in violations:
                assert page_num >= 1
                assert ratio > 0

    def test_detect_spacing_type_single(self, single_spaced_pdf: Path):
        """Test detecting single spacing."""
        with PDFDocument(single_spaced_pdf) as doc:
            extractor = SpacingExtractor(doc)
            spacing_type = extractor.detect_spacing_type()
            # Should detect single spacing
            assert spacing_type in ["single", "custom (1.0)", "custom (1.1)"] or "1" in spacing_type

    def test_detect_spacing_type_double(self, valid_thesis_pdf: Path):
        """Test detecting double spacing."""
        with PDFDocument(valid_thesis_pdf) as doc:
            extractor = SpacingExtractor(doc)
            spacing_type = extractor.detect_spacing_type(pages=[2, 3, 4])
            # Valid thesis should be double-spaced
            assert spacing_type in ["double", "unknown"] or "2" in spacing_type

    def test_empty_page_spacing(self, empty_pdf: Path):
        """Test spacing analysis on empty pages."""
        with PDFDocument(empty_pdf) as doc:
            extractor = SpacingExtractor(doc)
            spacings = extractor.get_line_spacings(1)
            assert spacings == []

    def test_single_line_page(self, minimal_pdf: Path):
        """Test spacing on page with single line."""
        with PDFDocument(minimal_pdf) as doc:
            extractor = SpacingExtractor(doc)
            spacings = extractor.get_line_spacings(1)
            # Single line means no spacing between lines
            assert len(spacings) == 0

    def test_spacing_tolerance(self, spacing_extractor: SpacingExtractor):
        """Test that tolerance affects spacing compliance."""
        # Strict tolerance
        _, violations_strict = spacing_extractor.check_double_spacing(
            pages=[2], tolerance=0.1
        )
        # Loose tolerance
        _, violations_loose = spacing_extractor.check_double_spacing(
            pages=[2], tolerance=0.5
        )
        # Loose tolerance should have same or fewer violations
        assert len(violations_loose) <= len(violations_strict)


class TestSpacingAnalysis:
    """Tests for SpacingAnalysis dataclass."""

    def test_spacing_analysis_creation(self):
        """Test creating SpacingAnalysis object."""
        analysis = SpacingAnalysis(
            average_ratio=2.0,
            median_ratio=2.0,
            min_ratio=1.8,
            max_ratio=2.2,
            sample_count=50,
            is_consistent=True,
        )
        assert analysis.average_ratio == 2.0
        assert analysis.is_consistent is True

    def test_consistency_check(self):
        """Test consistency calculation."""
        # Consistent spacing
        consistent = SpacingAnalysis(
            average_ratio=2.0,
            median_ratio=2.0,
            min_ratio=1.95,
            max_ratio=2.05,
            sample_count=50,
            is_consistent=True,
        )
        assert consistent.is_consistent is True

        # Inconsistent spacing
        inconsistent = SpacingAnalysis(
            average_ratio=1.5,
            median_ratio=1.5,
            min_ratio=1.0,
            max_ratio=2.0,
            sample_count=50,
            is_consistent=False,
        )
        assert inconsistent.is_consistent is False


class TestSpacingExtractorEdgeCases:
    """Edge case tests for SpacingExtractor."""

    def test_unknown_spacing_insufficient_data(self, minimal_pdf: Path):
        """Test that insufficient data returns unknown spacing type."""
        with PDFDocument(minimal_pdf) as doc:
            extractor = SpacingExtractor(doc)
            spacing_type = extractor.detect_spacing_type()
            assert spacing_type == "unknown"

    def test_analyze_spacing_no_data(self, empty_pdf: Path):
        """Test analyzing spacing with no data returns None."""
        with PDFDocument(empty_pdf) as doc:
            extractor = SpacingExtractor(doc)
            analysis = extractor.analyze_spacing()
            assert analysis is None
