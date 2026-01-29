"""Rule evaluation logic for compliance checking."""

from statistics import median

from thesis_compliance.extractor import (
    FontExtractor,
    MarginExtractor,
    PageNumberExtractor,
    PDFDocument,
    SpacingExtractor,
)
from thesis_compliance.models import Margins, RuleType, Severity, Violation
from thesis_compliance.spec.rules import (
    FontRule,
    MarginRule,
    PageNumberRule,
    SpacingRule,
    StyleSpec,
    TitlePageRule,
)

from .violations import ViolationBuilder


class RuleEvaluator:
    """Evaluates style rules against PDF content."""

    def __init__(self, doc: PDFDocument, spec: StyleSpec):
        """Initialize evaluator with document and spec.

        Args:
            doc: Open PDFDocument.
            spec: Style specification to check against.
        """
        self.doc = doc
        self.spec = spec

        # Initialize extractors
        self.margin_extractor = MarginExtractor(doc)
        self.font_extractor = FontExtractor(doc)
        self.spacing_extractor = SpacingExtractor(doc)
        self.page_number_extractor = PageNumberExtractor(doc)

    def evaluate_margins(
        self,
        pages: list[int] | None = None,
        exclude_title_page: bool = True,
    ) -> list[Violation]:
        """Evaluate margin compliance.

        Args:
            pages: Pages to check (None for all).
            exclude_title_page: Whether to skip page 1 (checked separately).

        Returns:
            List of violations found.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        if exclude_title_page and 1 in pages:
            pages = [p for p in pages if p != 1]

        violations: list[Violation] = []
        rule = self.spec.margins
        required = Margins(
            left=rule.left,
            right=rule.right,
            top=rule.top,
            bottom=rule.bottom,
        )

        margin_violations = self.margin_extractor.find_margin_violations(
            required=required,
            pages=pages,
            tolerance=rule.tolerance,
        )

        for page_num, page_violations in margin_violations.items():
            for margin_name, (expected, actual) in page_violations.items():
                violations.append(
                    ViolationBuilder.margin_violation(
                        page=page_num,
                        margin_name=margin_name,
                        expected=expected,
                        found=actual,
                    )
                )

        return violations

    def evaluate_title_page(self) -> list[Violation]:
        """Evaluate title page compliance.

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        rule = self.spec.title_page

        # Check title page top margin
        margins = self.margin_extractor.get_margins(1)
        if margins is not None:
            if margins.top < rule.top_margin - rule.margin_tolerance:
                violations.append(
                    ViolationBuilder.title_page_margin_violation(
                        expected=rule.top_margin,
                        found=margins.top,
                    )
                )

        return violations

    def evaluate_fonts(
        self,
        pages: list[int] | None = None,
    ) -> list[Violation]:
        """Evaluate font compliance.

        Args:
            pages: Pages to check (None for all).

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        rule = self.spec.fonts

        # Check body font
        body_font = self.font_extractor.get_body_font(pages)
        if body_font is not None:
            # Check font family
            font_allowed = any(
                allowed.lower() in body_font.font_name.lower()
                for allowed in rule.allowed_fonts
            )
            if not font_allowed:
                violations.append(
                    ViolationBuilder.font_violation(
                        page=None,
                        font_name=body_font.font_name,
                        allowed_fonts=rule.allowed_fonts,
                    )
                )

            # Check if primary body size is correct
            primary_sizes = [
                s for s in body_font.sizes
                if abs(s - rule.body_size) <= rule.size_tolerance
            ]
            if not primary_sizes:
                # Find the most common size (use median as approximation)
                most_common_size = median(sorted(body_font.sizes))
                if abs(most_common_size - rule.body_size) > rule.size_tolerance:
                    violations.append(
                        ViolationBuilder.font_size_violation(
                            page=None,
                            expected_size=rule.body_size,
                            found_size=most_common_size,
                        )
                    )

        return violations

    def evaluate_spacing(
        self,
        pages: list[int] | None = None,
    ) -> list[Violation]:
        """Evaluate line spacing compliance.

        Args:
            pages: Pages to check (None for all body pages).

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        rule = self.spec.spacing

        # Determine which pages to check
        if pages is None:
            if rule.applies_to == "body":
                # Try to detect body pages from page numbering
                analysis = self.page_number_extractor.analyze_page_numbers()
                if analysis.body_pages:
                    pages = analysis.body_pages
                else:
                    # Fall back to all pages except first few
                    pages = list(range(5, self.doc.page_count + 1))
            else:
                pages = list(range(1, self.doc.page_count + 1))

        # Check each page
        compliant, spacing_violations = self.spacing_extractor.check_double_spacing(
            pages=pages,
            tolerance=rule.tolerance,
        )

        if not compliant:
            for page_num, ratio in spacing_violations:
                violations.append(
                    ViolationBuilder.spacing_violation(
                        page=page_num,
                        expected_ratio=rule.required_ratio,
                        found_ratio=ratio,
                    )
                )

        return violations

    def evaluate_page_numbers(self) -> list[Violation]:
        """Evaluate page number compliance.

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        rule = self.spec.page_numbers

        analysis = self.page_number_extractor.analyze_page_numbers()

        # Check front matter style
        for page_num in analysis.front_matter_pages:
            page_number = self.page_number_extractor.get_page_number(page_num)
            if page_number:
                # Check alignment
                if page_number.alignment != rule.front_matter_alignment:
                    violations.append(
                        ViolationBuilder.page_number_alignment_violation(
                            page=page_num,
                            expected_alignment=rule.front_matter_alignment,
                            found_alignment=page_number.alignment,
                        )
                    )

        # Check body style
        for page_num in analysis.body_pages:
            page_number = self.page_number_extractor.get_page_number(page_num)
            if page_number:
                # Check alignment
                if page_number.alignment != rule.body_alignment:
                    violations.append(
                        ViolationBuilder.page_number_alignment_violation(
                            page=page_num,
                            expected_alignment=rule.body_alignment,
                            found_alignment=page_number.alignment,
                        )
                    )

        # Add any issues found during analysis
        for issue in analysis.issues:
            violations.append(
                ViolationBuilder.custom_violation(
                    rule_id="page_number.sequence",
                    rule_type=RuleType.PAGE_NUMBER,
                    severity=Severity.WARNING,
                    message=issue,
                )
            )

        return violations

    def evaluate_all(
        self,
        pages: list[int] | None = None,
    ) -> list[Violation]:
        """Evaluate all rules.

        Args:
            pages: Pages to check (None for all).

        Returns:
            List of all violations found.
        """
        violations: list[Violation] = []

        violations.extend(self.evaluate_title_page())
        violations.extend(self.evaluate_margins(pages))
        violations.extend(self.evaluate_fonts(pages))
        violations.extend(self.evaluate_spacing(pages))
        violations.extend(self.evaluate_page_numbers())

        return violations
