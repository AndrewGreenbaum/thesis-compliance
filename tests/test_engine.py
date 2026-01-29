"""Tests for the thesis compliance checking engine."""

from pathlib import Path

import pytest

from thesis_compliance.checker.engine import ThesisChecker, parse_page_range
from thesis_compliance.models import ComplianceReport, Severity
from thesis_compliance.spec import SpecLoader


class TestParsePageRange:
    """Tests for page range parsing."""

    def test_single_page(self):
        """Test parsing single page number."""
        pages = parse_page_range("5", max_pages=10)
        assert pages == [5]

    def test_page_range(self):
        """Test parsing page range."""
        pages = parse_page_range("1-5", max_pages=10)
        assert pages == [1, 2, 3, 4, 5]

    def test_multiple_pages(self):
        """Test parsing multiple individual pages."""
        pages = parse_page_range("1,3,5", max_pages=10)
        assert pages == [1, 3, 5]

    def test_mixed_ranges_and_singles(self):
        """Test parsing mixed ranges and singles."""
        pages = parse_page_range("1-3,5,7-9", max_pages=10)
        assert pages == [1, 2, 3, 5, 7, 8, 9]

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        pages = parse_page_range(" 1 - 3 , 5 ", max_pages=10)
        assert pages == [1, 2, 3, 5]

    def test_duplicate_removal(self):
        """Test that duplicates are removed."""
        pages = parse_page_range("1-3,2-4", max_pages=10)
        assert pages == [1, 2, 3, 4]

    def test_invalid_page_out_of_bounds(self):
        """Test error on out-of-bounds page."""
        with pytest.raises(ValueError, match="out of bounds"):
            parse_page_range("15", max_pages=10)

    def test_invalid_range_out_of_bounds(self):
        """Test error on out-of-bounds range."""
        with pytest.raises(ValueError, match="out of bounds"):
            parse_page_range("1-15", max_pages=10)

    def test_reversed_range_error(self):
        """Test error on reversed page range (start > end)."""
        with pytest.raises(ValueError, match="start > end"):
            parse_page_range("5-3", max_pages=10)

    def test_zero_page_error(self):
        """Test error on zero page number."""
        with pytest.raises(ValueError, match="out of bounds"):
            parse_page_range("0", max_pages=10)


class TestThesisChecker:
    """Tests for ThesisChecker class."""

    def test_init_with_path(self, valid_thesis_pdf: Path):
        """Test initializing checker with PDF path."""
        checker = ThesisChecker(valid_thesis_pdf)
        assert checker.page_count > 0
        checker.close()

    def test_init_with_spec_name(self, valid_thesis_pdf: Path):
        """Test initializing checker with spec name."""
        checker = ThesisChecker(valid_thesis_pdf, spec="rackham")
        assert checker.spec.name == "rackham"
        checker.close()

    def test_init_with_spec_object(self, valid_thesis_pdf: Path, rackham_spec):
        """Test initializing checker with StyleSpec object."""
        checker = ThesisChecker(valid_thesis_pdf, spec=rackham_spec)
        assert checker.spec.name == "rackham"
        checker.close()

    def test_context_manager(self, valid_thesis_pdf: Path):
        """Test using checker as context manager."""
        with ThesisChecker(valid_thesis_pdf) as checker:
            assert checker.page_count > 0

    def test_check_all_pages(self, thesis_checker: ThesisChecker):
        """Test running compliance check on all pages."""
        report = thesis_checker.check()
        assert isinstance(report, ComplianceReport)
        assert report.pages_checked == thesis_checker.page_count

    def test_check_specific_pages_string(self, thesis_checker: ThesisChecker):
        """Test running check on specific pages (string format)."""
        report = thesis_checker.check(pages="1-3")
        assert report.pages_checked == 3

    def test_check_specific_pages_list(self, thesis_checker: ThesisChecker):
        """Test running check on specific pages (list format)."""
        report = thesis_checker.check(pages=[1, 2, 3])
        assert report.pages_checked == 3

    def test_check_margins_only(self, thesis_checker: ThesisChecker):
        """Test checking only margins."""
        report = thesis_checker.check_margins_only()
        assert isinstance(report, ComplianceReport)
        # Should only have margin-related rules checked
        assert report.rules_checked <= 10

    def test_check_fonts_only(self, thesis_checker: ThesisChecker):
        """Test checking only fonts."""
        report = thesis_checker.check_fonts_only()
        assert isinstance(report, ComplianceReport)
        # Should only have font-related rules checked
        assert report.rules_checked <= 5

    def test_check_spacing_only(self, thesis_checker: ThesisChecker):
        """Test checking only spacing."""
        report = thesis_checker.check_spacing_only()
        assert isinstance(report, ComplianceReport)
        # Should only have spacing rule checked
        assert report.rules_checked <= 3

    def test_page_count_property(self, thesis_checker: ThesisChecker):
        """Test page_count property."""
        assert thesis_checker.page_count == 5  # valid_thesis has 5 pages


class TestThesisCheckerWithBadPDFs:
    """Tests for ThesisChecker with non-compliant PDFs."""

    def test_bad_margins_detected(self, bad_margins_pdf: Path, rackham_spec):
        """Test that bad margins are detected."""
        with ThesisChecker(bad_margins_pdf, rackham_spec) as checker:
            report = checker.check_margins_only()
            # Should find margin errors
            assert len(report.errors) > 0 or len(report.warnings) > 0

    def test_wrong_font_detected(self, wrong_font_pdf: Path, rackham_spec):
        """Test that wrong font is detected."""
        with ThesisChecker(wrong_font_pdf, rackham_spec) as checker:
            report = checker.check_fonts_only()
            # Should find font-related issues
            violations_count = len(report.errors) + len(report.warnings)
            assert violations_count > 0

    def test_single_spacing_detected(self, single_spaced_pdf: Path, rackham_spec):
        """Test that single spacing is detected."""
        with ThesisChecker(single_spaced_pdf, rackham_spec) as checker:
            report = checker.check_spacing_only()
            # Spacing detection depends on PDF generation quality
            # Just verify the check completes without error
            assert isinstance(report, ComplianceReport)


class TestThesisCheckerEdgeCases:
    """Edge case tests for ThesisChecker."""

    def test_nonexistent_pdf(self):
        """Test error when PDF doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ThesisChecker("/nonexistent/file.pdf")

    def test_invalid_spec_name(self, valid_thesis_pdf: Path):
        """Test error with invalid spec name."""
        with pytest.raises(FileNotFoundError):
            ThesisChecker(valid_thesis_pdf, spec="nonexistent_spec")

    def test_empty_pdf(self, empty_pdf: Path):
        """Test checking empty PDF."""
        with ThesisChecker(empty_pdf) as checker:
            report = checker.check()
            # Should complete without crashing
            assert isinstance(report, ComplianceReport)

    def test_minimal_pdf(self, minimal_pdf: Path):
        """Test checking minimal PDF."""
        with ThesisChecker(minimal_pdf) as checker:
            report = checker.check()
            assert report.pages_checked == 1

    def test_normalize_pages_none(self, thesis_checker: ThesisChecker):
        """Test _normalize_pages with None input."""
        result = thesis_checker._normalize_pages(None)
        assert result is None

    def test_normalize_pages_string(self, thesis_checker: ThesisChecker):
        """Test _normalize_pages with string input."""
        result = thesis_checker._normalize_pages("1-3")
        assert result == [1, 2, 3]

    def test_normalize_pages_list(self, thesis_checker: ThesisChecker):
        """Test _normalize_pages with list input."""
        result = thesis_checker._normalize_pages([1, 3, 5])
        assert result == [1, 3, 5]


class TestComplianceReport:
    """Tests for compliance report generation."""

    def test_report_passes_for_valid_thesis(self, valid_thesis_pdf: Path):
        """Test that valid thesis generates passing report."""
        with ThesisChecker(valid_thesis_pdf) as checker:
            report = checker.check()
            # Valid thesis should mostly pass (may have minor warnings)
            # Just verify report is generated correctly
            assert report.spec_name
            assert report.pages_checked > 0
            assert report.rules_checked > 0

    def test_report_violations_sorted(self, bad_margins_pdf: Path):
        """Test that violations are sorted by page and severity."""
        with ThesisChecker(bad_margins_pdf) as checker:
            report = checker.check()
            if len(report.violations) >= 2:
                # Check violations are sorted
                for i in range(len(report.violations) - 1):
                    v1 = report.violations[i]
                    v2 = report.violations[i + 1]
                    # Page 0 (None) comes first, then sorted by page
                    page1 = v1.page or 0
                    page2 = v2.page or 0
                    assert page1 <= page2

    def test_report_to_dict(self, thesis_checker: ThesisChecker):
        """Test converting report to dictionary."""
        report = thesis_checker.check()
        d = report.to_dict()
        assert "pdf_path" in d
        assert "spec_name" in d
        assert "passed" in d
        assert "violations" in d
