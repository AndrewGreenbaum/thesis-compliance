"""Rule evaluation logic for compliance checking."""

from statistics import median

from thesis_compliance.extractor import (
    BibliographyExtractor,
    CaptionExtractor,
    FontExtractor,
    HeadingExtractor,
    MarginExtractor,
    PageNumberExtractor,
    PDFDocument,
    SpacingExtractor,
)
from thesis_compliance.models import Margins, RuleType, Severity, Violation
from thesis_compliance.spec.rules import HeadingRule, StyleSpec

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
        self.heading_extractor = HeadingExtractor(doc)
        self.caption_extractor = CaptionExtractor(doc)
        self.bibliography_extractor = BibliographyExtractor(doc)

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
                allowed.lower() in body_font.font_name.lower() for allowed in rule.allowed_fonts
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
                s for s in body_font.sizes if abs(s - rule.body_size) <= rule.size_tolerance
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

    def evaluate_headings(
        self,
        pages: list[int] | None = None,
    ) -> list[Violation]:
        """Evaluate heading compliance.

        Args:
            pages: Pages to check (None for all).

        Returns:
            List of violations found.
        """
        if self.spec.headings is None:
            return []

        violations: list[Violation] = []
        rule = self.spec.headings

        compliant, issues = self.heading_extractor.check_heading_compliance(
            chapter_font_size=rule.chapter_font_size,
            chapter_bold=rule.chapter_bold,
            chapter_all_caps=rule.chapter_all_caps,
            section_font_size=rule.section_font_size,
            section_bold=rule.section_bold,
            subsection_font_size=rule.subsection_font_size,
            subsection_italic=rule.subsection_italic,
            size_tolerance=rule.size_tolerance,
            pages=pages,
        )

        for page_num, heading, issue in issues:
            # Determine if it's a font size or style issue
            if "font size" in issue.lower():
                # Extract expected size from issue text
                violations.append(
                    ViolationBuilder.heading_font_size_violation(
                        page=page_num,
                        heading_level=heading.level,
                        heading_text=heading.text,
                        expected_size=self._get_expected_heading_size(heading.level, rule),
                        found_size=heading.font_size,
                    )
                )
            else:
                # Style issue (bold, italic, caps)
                missing_style = self._extract_missing_style(issue)
                violations.append(
                    ViolationBuilder.heading_style_violation(
                        page=page_num,
                        heading_level=heading.level,
                        heading_text=heading.text,
                        missing_style=missing_style,
                    )
                )

        return violations

    def _get_expected_heading_size(self, level: int, rule: HeadingRule) -> float:
        """Get expected font size for a heading level."""
        if level == 1:
            return rule.chapter_font_size
        elif level == 2:
            return rule.section_font_size
        else:
            return rule.subsection_font_size

    def _extract_missing_style(self, issue: str) -> str:
        """Extract the missing style from an issue string."""
        issue_lower = issue.lower()
        if "bold" in issue_lower:
            return "bold"
        elif "caps" in issue_lower:
            return "ALL CAPS"
        elif "italic" in issue_lower:
            return "italic"
        return "proper formatting"

    def evaluate_captions(
        self,
        pages: list[int] | None = None,
    ) -> list[Violation]:
        """Evaluate caption compliance.

        Args:
            pages: Pages to check (None for all).

        Returns:
            List of violations found.
        """
        if self.spec.captions is None:
            return []

        violations: list[Violation] = []
        rule = self.spec.captions

        compliant, issues = self.caption_extractor.check_caption_compliance(
            font_size=rule.font_size,
            size_tolerance=rule.size_tolerance,
            figure_label=rule.figure_label,
            table_label=rule.table_label,
            numbering=rule.numbering,
            pages=pages,
        )

        for page_num, caption, issue in issues:
            issue_lower = issue.lower()

            if "font size" in issue_lower:
                violations.append(
                    ViolationBuilder.caption_font_size_violation(
                        page=page_num if page_num > 0 else caption.page_number,
                        caption_type=caption.caption_type,
                        caption_number=caption.number,
                        expected_size=rule.font_size,
                        found_size=caption.font_size,
                    )
                )
            elif "label" in issue_lower:
                expected = (
                    rule.figure_label if caption.caption_type == "figure" else rule.table_label
                )
                violations.append(
                    ViolationBuilder.caption_label_violation(
                        page=page_num if page_num > 0 else caption.page_number,
                        caption_type=caption.caption_type,
                        expected_label=expected,
                        found_label=caption.label_format,
                    )
                )
            elif "numbering should be" in issue_lower:
                found_style = "by_chapter" if rule.numbering == "continuous" else "continuous"
                violations.append(
                    ViolationBuilder.caption_numbering_violation(
                        caption_type=caption.caption_type,
                        expected_style=rule.numbering,
                        found_style=found_style,
                    )
                )
            else:
                # Sequence issue
                violations.append(
                    ViolationBuilder.caption_sequence_violation(
                        page=page_num if page_num > 0 else caption.page_number,
                        caption_type=caption.caption_type,
                        issue=issue,
                    )
                )

        return violations

    def evaluate_bibliography(self) -> list[Violation]:
        """Evaluate bibliography compliance.

        Returns:
            List of violations found.
        """
        if self.spec.bibliography is None:
            return []

        violations: list[Violation] = []
        rule = self.spec.bibliography

        compliant, issues = self.bibliography_extractor.check_bibliography_compliance(
            hanging_indent=rule.hanging_indent,
            indent_tolerance=rule.indent_tolerance,
            font_size=rule.font_size,
            size_tolerance=rule.size_tolerance,
        )

        for page_num, issue in issues:
            issue_lower = issue.lower()

            if "hanging indent" in issue_lower:
                # Extract found indent from issue
                info = self.bibliography_extractor.analyze_bibliography()
                found_indent = info.avg_hanging_indent if info else 0.0
                violations.append(
                    ViolationBuilder.bibliography_indent_violation(
                        page=page_num,
                        expected_indent=rule.hanging_indent,
                        found_indent=found_indent,
                    )
                )
            elif "font size" in issue_lower:
                # Find the font size from the issue text or use rule default
                violations.append(
                    ViolationBuilder.bibliography_font_size_violation(
                        page=page_num,
                        expected_size=rule.font_size,
                        found_size=0.0,  # Will be overwritten by actual
                    )
                )
            else:
                # Generic bibliography issue
                violations.append(
                    ViolationBuilder.custom_violation(
                        rule_id="bibliography.general",
                        rule_type=RuleType.BIBLIOGRAPHY,
                        severity=Severity.WARNING,
                        message=issue,
                        page=page_num if page_num > 0 else None,
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

        # Extended evaluators (only run if rules are defined in spec)
        violations.extend(self.evaluate_headings(pages))
        violations.extend(self.evaluate_captions(pages))
        violations.extend(self.evaluate_bibliography())

        return violations
