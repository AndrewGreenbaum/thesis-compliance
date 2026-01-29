"""Tests for data models."""

import pytest

from thesis_compliance.models import (
    BoundingBox,
    ComplianceReport,
    Margins,
    PageInfo,
    RuleType,
    Severity,
    Violation,
)
from pathlib import Path


class TestBoundingBox:
    """Tests for BoundingBox."""

    def test_dimensions(self):
        bbox = BoundingBox(x0=72, y0=72, x1=540, y1=720)
        assert bbox.width == 468
        assert bbox.height == 648

    def test_to_inches(self):
        bbox = BoundingBox(x0=72, y0=144, x1=540, y1=720)
        inches = bbox.to_inches()
        assert inches.x0 == 1.0
        assert inches.y0 == 2.0
        assert inches.x1 == 7.5
        assert inches.y1 == 10.0


class TestPageInfo:
    """Tests for PageInfo."""

    def test_from_points(self):
        # US Letter size in points
        page = PageInfo.from_points(1, 612, 792)
        assert page.number == 1
        assert page.width_pt == 612
        assert page.height_pt == 792
        assert page.width_inches == 8.5
        assert page.height_inches == 11.0


class TestMargins:
    """Tests for Margins."""

    def test_to_dict(self):
        margins = Margins(left=1.5, right=1.0, top=1.0, bottom=1.0)
        d = margins.to_dict()
        assert d == {
            "left": 1.5,
            "right": 1.0,
            "top": 1.0,
            "bottom": 1.0,
        }


class TestViolation:
    """Tests for Violation."""

    def test_to_dict(self):
        violation = Violation(
            rule_id="margin.left",
            rule_type=RuleType.MARGIN,
            severity=Severity.ERROR,
            message="Left margin too small",
            page=5,
            expected=">= 1.5 inches",
            found="1.2 inches",
            suggestion="Move content right",
        )
        d = violation.to_dict()
        assert d["rule_id"] == "margin.left"
        assert d["rule_type"] == "margin"
        assert d["severity"] == "error"
        assert d["page"] == 5

    def test_to_dict_minimal(self):
        violation = Violation(
            rule_id="test",
            rule_type=RuleType.FONT,
            severity=Severity.WARNING,
            message="Test message",
        )
        d = violation.to_dict()
        assert "page" not in d
        assert "expected" not in d


class TestComplianceReport:
    """Tests for ComplianceReport."""

    def test_passed_no_violations(self):
        report = ComplianceReport(
            pdf_path=Path("test.pdf"),
            spec_name="rackham",
            pages_checked=10,
            rules_checked=20,
            violations=[],
        )
        assert report.passed is True
        assert report.passed_strict is True

    def test_passed_with_warnings(self):
        report = ComplianceReport(
            pdf_path=Path("test.pdf"),
            spec_name="rackham",
            pages_checked=10,
            rules_checked=20,
            violations=[
                Violation(
                    rule_id="test",
                    rule_type=RuleType.FONT,
                    severity=Severity.WARNING,
                    message="Warning",
                )
            ],
        )
        assert report.passed is True
        assert report.passed_strict is False

    def test_failed_with_error(self):
        report = ComplianceReport(
            pdf_path=Path("test.pdf"),
            spec_name="rackham",
            pages_checked=10,
            rules_checked=20,
            violations=[
                Violation(
                    rule_id="test",
                    rule_type=RuleType.MARGIN,
                    severity=Severity.ERROR,
                    message="Error",
                )
            ],
        )
        assert report.passed is False
        assert len(report.errors) == 1
        assert len(report.warnings) == 0
