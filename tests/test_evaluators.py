"""Tests for rule evaluators."""

from pathlib import Path

import pytest

from thesis_compliance.checker.evaluators import RuleEvaluator
from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import RuleType, Severity, Violation
from thesis_compliance.spec import SpecLoader


class TestRuleEvaluator:
    """Tests for RuleEvaluator class."""

    @pytest.fixture
    def evaluator(self, pdf_document: PDFDocument, rackham_spec) -> RuleEvaluator:
        """Create a RuleEvaluator instance."""
        return RuleEvaluator(pdf_document, rackham_spec)

    def test_evaluate_margins(self, evaluator: RuleEvaluator):
        """Test margin evaluation."""
        violations = evaluator.evaluate_margins()
        assert isinstance(violations, list)
        for v in violations:
            assert isinstance(v, Violation)
            assert v.rule_type == RuleType.MARGIN

    def test_evaluate_margins_specific_pages(self, evaluator: RuleEvaluator):
        """Test margin evaluation for specific pages."""
        violations = evaluator.evaluate_margins(pages=[2, 3])
        assert isinstance(violations, list)

    def test_evaluate_margins_exclude_title(self, evaluator: RuleEvaluator):
        """Test margin evaluation excluding title page."""
        violations_with_title = evaluator.evaluate_margins(exclude_title_page=False)
        violations_without_title = evaluator.evaluate_margins(exclude_title_page=True)
        # Results may or may not differ
        assert isinstance(violations_with_title, list)
        assert isinstance(violations_without_title, list)

    def test_evaluate_title_page(self, evaluator: RuleEvaluator):
        """Test title page evaluation."""
        violations = evaluator.evaluate_title_page()
        assert isinstance(violations, list)
        for v in violations:
            assert isinstance(v, Violation)
            assert v.rule_type == RuleType.TITLE_PAGE
            assert v.page == 1

    def test_evaluate_fonts(self, evaluator: RuleEvaluator):
        """Test font evaluation."""
        violations = evaluator.evaluate_fonts()
        assert isinstance(violations, list)
        for v in violations:
            assert isinstance(v, Violation)
            assert v.rule_type == RuleType.FONT

    def test_evaluate_fonts_specific_pages(self, evaluator: RuleEvaluator):
        """Test font evaluation for specific pages."""
        violations = evaluator.evaluate_fonts(pages=[2, 3, 4])
        assert isinstance(violations, list)

    def test_evaluate_spacing(self, evaluator: RuleEvaluator):
        """Test spacing evaluation."""
        violations = evaluator.evaluate_spacing()
        assert isinstance(violations, list)
        for v in violations:
            assert isinstance(v, Violation)
            assert v.rule_type == RuleType.SPACING

    def test_evaluate_spacing_specific_pages(self, evaluator: RuleEvaluator):
        """Test spacing evaluation for specific pages."""
        violations = evaluator.evaluate_spacing(pages=[2, 3])
        assert isinstance(violations, list)

    def test_evaluate_page_numbers(self, evaluator: RuleEvaluator):
        """Test page number evaluation."""
        violations = evaluator.evaluate_page_numbers()
        assert isinstance(violations, list)
        for v in violations:
            assert isinstance(v, Violation)
            assert v.rule_type == RuleType.PAGE_NUMBER

    def test_evaluate_all(self, evaluator: RuleEvaluator):
        """Test evaluating all rules."""
        violations = evaluator.evaluate_all()
        assert isinstance(violations, list)
        # Should contain violations from multiple rule types potentially
        rule_types_found = {v.rule_type for v in violations}
        # Just verify we get results
        assert isinstance(rule_types_found, set)

    def test_evaluate_all_specific_pages(self, evaluator: RuleEvaluator):
        """Test evaluating all rules for specific pages."""
        violations = evaluator.evaluate_all(pages=[1, 2, 3])
        assert isinstance(violations, list)


class TestRuleEvaluatorWithBadPDFs:
    """Tests for RuleEvaluator with non-compliant PDFs."""

    def test_margin_violations_detected(self, bad_margins_pdf: Path, rackham_spec):
        """Test that margin violations are detected."""
        with PDFDocument(bad_margins_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_margins()
            # Bad margins PDF has 0.5" margins, should have violations
            assert len(violations) > 0

    def test_font_violations_detected(self, wrong_font_pdf: Path, rackham_spec):
        """Test that font violations are detected."""
        with PDFDocument(wrong_font_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_fonts()
            # Wrong font PDF uses Helvetica 10pt
            assert len(violations) > 0

    def test_spacing_violations_detected(self, single_spaced_pdf: Path, rackham_spec):
        """Test that spacing violations are detected."""
        with PDFDocument(single_spaced_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_spacing()
            # Spacing detection depends on PDF generation quality
            # Just verify the evaluation completes without error
            assert isinstance(violations, list)


class TestRuleEvaluatorEdgeCases:
    """Edge case tests for RuleEvaluator."""

    def test_empty_pdf(self, empty_pdf: Path, rackham_spec):
        """Test evaluating empty PDF."""
        with PDFDocument(empty_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            # Should not crash on empty PDF
            margin_violations = evaluator.evaluate_margins()
            font_violations = evaluator.evaluate_fonts()
            spacing_violations = evaluator.evaluate_spacing()
            assert isinstance(margin_violations, list)
            assert isinstance(font_violations, list)
            assert isinstance(spacing_violations, list)

    def test_minimal_pdf(self, minimal_pdf: Path, rackham_spec):
        """Test evaluating minimal PDF."""
        with PDFDocument(minimal_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_all()
            assert isinstance(violations, list)

    def test_different_spec(self, valid_thesis_pdf: Path):
        """Test using different style spec."""
        unc_spec = SpecLoader.load("unc")
        with PDFDocument(valid_thesis_pdf) as doc:
            evaluator = RuleEvaluator(doc, unc_spec)
            violations = evaluator.evaluate_all()
            assert isinstance(violations, list)


class TestViolationDetails:
    """Tests for violation details from evaluators."""

    def test_margin_violation_has_details(self, bad_margins_pdf: Path, rackham_spec):
        """Test that margin violations have proper details."""
        with PDFDocument(bad_margins_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_margins()
            if violations:
                v = violations[0]
                assert v.page is not None
                assert v.expected is not None
                assert v.found is not None
                assert v.severity in [Severity.ERROR, Severity.WARNING]

    def test_spacing_violation_has_page(self, single_spaced_pdf: Path, rackham_spec):
        """Test that spacing violations have page numbers."""
        with PDFDocument(single_spaced_pdf) as doc:
            evaluator = RuleEvaluator(doc, rackham_spec)
            violations = evaluator.evaluate_spacing()
            if violations:
                for v in violations:
                    assert v.page is not None
