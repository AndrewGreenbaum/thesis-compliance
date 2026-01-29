"""Tests for violation builders."""

import pytest

from thesis_compliance.checker.violations import ViolationBuilder
from thesis_compliance.models import RuleType, Severity


class TestViolationBuilder:
    """Tests for ViolationBuilder."""

    def test_margin_violation(self):
        v = ViolationBuilder.margin_violation(
            page=5,
            margin_name="left",
            expected=1.5,
            found=1.2,
        )
        assert v.rule_id == "margin.left"
        assert v.rule_type == RuleType.MARGIN
        assert v.severity == Severity.ERROR
        assert v.page == 5
        assert "1.50" in v.expected
        assert "1.20" in v.found
        assert "suggestion" in v.suggestion.lower() or "move" in v.suggestion.lower()

    def test_title_page_margin_violation(self):
        v = ViolationBuilder.title_page_margin_violation(
            expected=2.0,
            found=1.75,
        )
        assert v.rule_id == "title_page.top_margin"
        assert v.rule_type == RuleType.TITLE_PAGE
        assert v.page == 1
        assert "2.0" in v.expected
        assert "1.75" in v.found

    def test_font_violation(self):
        v = ViolationBuilder.font_violation(
            page=None,
            font_name="Comic Sans",
            allowed_fonts=["Times", "Arial", "Helvetica"],
        )
        assert v.rule_id == "font.family"
        assert v.rule_type == RuleType.FONT
        assert "Comic Sans" in v.message
        assert v.page is None

    def test_spacing_violation(self):
        v = ViolationBuilder.spacing_violation(
            page=10,
            expected_ratio=2.0,
            found_ratio=1.5,
        )
        assert v.rule_id == "spacing.line"
        assert v.rule_type == RuleType.SPACING
        assert "double" in v.message.lower()
        assert v.page == 10

    def test_page_number_alignment_violation(self):
        v = ViolationBuilder.page_number_alignment_violation(
            page=3,
            expected_alignment="center",
            found_alignment="right",
        )
        assert v.rule_id == "page_number.alignment"
        assert v.severity == Severity.WARNING
        assert "center" in v.expected
        assert "right" in v.found
