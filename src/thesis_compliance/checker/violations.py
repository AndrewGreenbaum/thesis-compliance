"""Violation creation utilities."""

from typing import Any

from thesis_compliance.models import BoundingBox, RuleType, Severity, Violation


class ViolationBuilder:
    """Builder for creating compliance violations with consistent formatting."""

    @staticmethod
    def margin_violation(
        page: int,
        margin_name: str,
        expected: float,
        found: float,
        location: BoundingBox | None = None,
    ) -> Violation:
        """Create a margin violation.

        Args:
            page: Page number where violation occurred.
            margin_name: Which margin (left, right, top, bottom).
            expected: Expected minimum margin in inches.
            found: Actual margin in inches.
            location: Optional bounding box of violating content.

        Returns:
            Violation object.
        """
        diff_pts = (expected - found) * 72
        suggestion = f"Move content {diff_pts:.0f}pt away from the {margin_name} edge"

        return Violation(
            rule_id=f"margin.{margin_name}",
            rule_type=RuleType.MARGIN,
            severity=Severity.ERROR,
            message=f"{margin_name.capitalize()} margin must be at least {expected:.2f} inches",
            page=page,
            expected=f">= {expected:.2f} inches",
            found=f"{found:.2f} inches",
            suggestion=suggestion,
            location=location,
        )

    @staticmethod
    def title_page_margin_violation(
        expected: float,
        found: float,
    ) -> Violation:
        """Create a title page top margin violation.

        Args:
            expected: Expected minimum top margin in inches.
            found: Actual top margin in inches.

        Returns:
            Violation object.
        """
        diff_pts = (expected - found) * 72

        return Violation(
            rule_id="title_page.top_margin",
            rule_type=RuleType.TITLE_PAGE,
            severity=Severity.ERROR,
            message=f"Title page top margin must be at least {expected:.1f} inches",
            page=1,
            expected=f">= {expected:.1f} inches",
            found=f"{found:.2f} inches",
            suggestion=f"Add {diff_pts:.0f}pt of space before the title",
        )

    @staticmethod
    def font_violation(
        page: int | None,
        font_name: str,
        allowed_fonts: list[str],
    ) -> Violation:
        """Create a font family violation.

        Args:
            page: Page number (None for document-wide).
            font_name: Font that was found.
            allowed_fonts: List of allowed font names.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id="font.family",
            rule_type=RuleType.FONT,
            severity=Severity.ERROR,
            message=f"Body font '{font_name}' is not an approved font",
            page=page,
            expected=f"One of: {', '.join(allowed_fonts[:3])}"
            + ("..." if len(allowed_fonts) > 3 else ""),
            found=font_name,
            suggestion=f"Use {allowed_fonts[0]} for body text",
        )

    @staticmethod
    def font_size_violation(
        page: int | None,
        expected_size: float,
        found_size: float,
    ) -> Violation:
        """Create a font size violation.

        Args:
            page: Page number (None for document-wide).
            expected_size: Required font size in points.
            found_size: Actual font size found.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id="font.size",
            rule_type=RuleType.FONT,
            severity=Severity.ERROR,
            message=f"Body text must use {expected_size:.0f}pt font",
            page=page,
            expected=f"{expected_size:.0f}pt",
            found=f"{found_size:.1f}pt",
            suggestion=f"Change body text font size to {expected_size:.0f}pt",
        )

    @staticmethod
    def spacing_violation(
        page: int,
        expected_ratio: float,
        found_ratio: float,
    ) -> Violation:
        """Create a line spacing violation.

        Args:
            page: Page number where violation occurred.
            expected_ratio: Required spacing ratio (2.0 for double).
            found_ratio: Actual spacing ratio found.

        Returns:
            Violation object.
        """
        spacing_name = {
            1.0: "single",
            1.5: "1.5 lines",
            2.0: "double",
        }.get(expected_ratio, f"{expected_ratio}x")

        found_name = {
            1.0: "single",
            1.5: "1.5 lines",
            2.0: "double",
        }.get(round(found_ratio, 1), f"{found_ratio:.1f}x")

        return Violation(
            rule_id="spacing.line",
            rule_type=RuleType.SPACING,
            severity=Severity.ERROR,
            message=f"Body text must be {spacing_name}-spaced",
            page=page,
            expected=f"{expected_ratio:.1f} line spacing",
            found=f"{found_ratio:.2f} ({found_name})",
            suggestion=f'Check paragraph settings use "{spacing_name}" not "{found_name}"',
        )

    @staticmethod
    def page_number_style_violation(
        page: int,
        expected_style: str,
        found_style: str,
        section: str,
    ) -> Violation:
        """Create a page number style violation.

        Args:
            page: Page number where violation occurred.
            expected_style: Expected style (roman, arabic).
            found_style: Actual style found.
            section: Section name (front_matter, body).

        Returns:
            Violation object.
        """
        return Violation(
            rule_id=f"page_number.{section}.style",
            rule_type=RuleType.PAGE_NUMBER,
            severity=Severity.ERROR,
            message=f"{section.replace('_', ' ').title()} pages must use {expected_style} numerals",
            page=page,
            expected=expected_style,
            found=found_style,
            suggestion=f"Change page number style to {expected_style} numerals",
        )

    @staticmethod
    def page_number_alignment_violation(
        page: int,
        expected_alignment: str,
        found_alignment: str,
    ) -> Violation:
        """Create a page number alignment violation.

        Args:
            page: Page number where violation occurred.
            expected_alignment: Expected alignment (left, center, right).
            found_alignment: Actual alignment found.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id="page_number.alignment",
            rule_type=RuleType.PAGE_NUMBER,
            severity=Severity.WARNING,
            message=f"Page numbers should be {expected_alignment}-aligned",
            page=page,
            expected=expected_alignment,
            found=found_alignment,
            suggestion=f"Move page number to {expected_alignment} position",
        )

    @staticmethod
    def custom_violation(
        rule_id: str,
        rule_type: RuleType,
        severity: Severity,
        message: str,
        page: int | None = None,
        expected: Any = None,
        found: Any = None,
        suggestion: str | None = None,
    ) -> Violation:
        """Create a custom violation.

        Args:
            rule_id: Unique identifier for the rule.
            rule_type: Type of rule.
            severity: Severity level.
            message: Human-readable message.
            page: Page number (optional).
            expected: Expected value (optional).
            found: Found value (optional).
            suggestion: Fix suggestion (optional).

        Returns:
            Violation object.
        """
        return Violation(
            rule_id=rule_id,
            rule_type=rule_type,
            severity=severity,
            message=message,
            page=page,
            expected=expected,
            found=found,
            suggestion=suggestion,
        )

    @staticmethod
    def heading_font_size_violation(
        page: int,
        heading_level: int,
        heading_text: str,
        expected_size: float,
        found_size: float,
    ) -> Violation:
        """Create a heading font size violation.

        Args:
            page: Page number where violation occurred.
            heading_level: Heading level (1=chapter, 2=section, 3=subsection).
            heading_text: The heading text (truncated for display).
            expected_size: Expected font size in points.
            found_size: Actual font size in points.

        Returns:
            Violation object.
        """
        level_names = {1: "Chapter", 2: "Section", 3: "Subsection"}
        level_name = level_names.get(heading_level, "Heading")
        truncated = heading_text[:40] + "..." if len(heading_text) > 40 else heading_text

        return Violation(
            rule_id=f"heading.level{heading_level}.font_size",
            rule_type=RuleType.HEADING,
            severity=Severity.ERROR,
            message=f"{level_name} heading must use {expected_size:.0f}pt font",
            page=page,
            expected=f"{expected_size:.0f}pt",
            found=f"{found_size:.1f}pt",
            suggestion=f'Change "{truncated}" to {expected_size:.0f}pt',
        )

    @staticmethod
    def heading_style_violation(
        page: int,
        heading_level: int,
        heading_text: str,
        missing_style: str,
    ) -> Violation:
        """Create a heading style violation (bold, italic, caps).

        Args:
            page: Page number where violation occurred.
            heading_level: Heading level (1=chapter, 2=section, 3=subsection).
            heading_text: The heading text (truncated for display).
            missing_style: The style that's missing (e.g., "bold", "ALL CAPS").

        Returns:
            Violation object.
        """
        level_names = {1: "Chapter", 2: "Section", 3: "Subsection"}
        level_name = level_names.get(heading_level, "Heading")
        truncated = heading_text[:40] + "..." if len(heading_text) > 40 else heading_text

        return Violation(
            rule_id=f"heading.level{heading_level}.style",
            rule_type=RuleType.HEADING,
            severity=Severity.ERROR,
            message=f"{level_name} headings must be {missing_style}",
            page=page,
            expected=missing_style,
            found="missing",
            suggestion=f'Apply {missing_style} formatting to "{truncated}"',
        )

    @staticmethod
    def caption_font_size_violation(
        page: int,
        caption_type: str,
        caption_number: str,
        expected_size: float,
        found_size: float,
    ) -> Violation:
        """Create a caption font size violation.

        Args:
            page: Page number where violation occurred.
            caption_type: Type of caption ("figure" or "table").
            caption_number: The caption number (e.g., "1", "2.1").
            expected_size: Expected font size in points.
            found_size: Actual font size in points.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id=f"caption.{caption_type}.font_size",
            rule_type=RuleType.CAPTION,
            severity=Severity.WARNING,
            message=f"{caption_type.title()} captions must use {expected_size:.0f}pt font",
            page=page,
            expected=f"{expected_size:.0f}pt",
            found=f"{found_size:.1f}pt",
            suggestion=f"Change {caption_type.title()} {caption_number} caption "
            f"to {expected_size:.0f}pt",
        )

    @staticmethod
    def caption_label_violation(
        page: int,
        caption_type: str,
        expected_label: str,
        found_label: str,
    ) -> Violation:
        """Create a caption label format violation.

        Args:
            page: Page number where violation occurred.
            caption_type: Type of caption ("figure" or "table").
            expected_label: Expected label format (e.g., "Figure").
            found_label: Actual label found.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id=f"caption.{caption_type}.label",
            rule_type=RuleType.CAPTION,
            severity=Severity.WARNING,
            message=f"{caption_type.title()} captions should use '{expected_label}' label",
            page=page,
            expected=expected_label,
            found=found_label,
            suggestion=f"Change '{found_label}' to '{expected_label}'",
        )

    @staticmethod
    def caption_numbering_violation(
        caption_type: str,
        expected_style: str,
        found_style: str,
    ) -> Violation:
        """Create a caption numbering style violation.

        Args:
            caption_type: Type of caption ("figure" or "table").
            expected_style: Expected numbering style ("continuous" or "by_chapter").
            found_style: Actual numbering style.

        Returns:
            Violation object.
        """
        style_desc = {
            "continuous": "1, 2, 3...",
            "by_chapter": "1.1, 1.2, 2.1...",
        }

        return Violation(
            rule_id=f"caption.{caption_type}.numbering",
            rule_type=RuleType.CAPTION,
            severity=Severity.WARNING,
            message=f"{caption_type.title()} numbering should be {expected_style}",
            page=None,
            expected=f"{expected_style} ({style_desc.get(expected_style, '')})",
            found=found_style,
            suggestion=f"Renumber {caption_type}s using {expected_style} numbering",
        )

    @staticmethod
    def caption_sequence_violation(
        page: int,
        caption_type: str,
        issue: str,
    ) -> Violation:
        """Create a caption sequence/ordering violation.

        Args:
            page: Page number where violation occurred.
            caption_type: Type of caption ("figure" or "table").
            issue: Description of the sequence issue.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id=f"caption.{caption_type}.sequence",
            rule_type=RuleType.CAPTION,
            severity=Severity.WARNING,
            message=issue,
            page=page,
            suggestion=f"Check {caption_type} numbering sequence",
        )

    @staticmethod
    def bibliography_indent_violation(
        page: int,
        expected_indent: float,
        found_indent: float,
    ) -> Violation:
        """Create a bibliography hanging indent violation.

        Args:
            page: Page number (start of bibliography).
            expected_indent: Expected hanging indent in inches.
            found_indent: Actual hanging indent in inches.

        Returns:
            Violation object.
        """
        diff_pts = (expected_indent - found_indent) * 72

        return Violation(
            rule_id="bibliography.hanging_indent",
            rule_type=RuleType.BIBLIOGRAPHY,
            severity=Severity.ERROR,
            message=f'Bibliography entries must have {expected_indent:.2f}" hanging indent',
            page=page,
            expected=f'{expected_indent:.2f}"',
            found=f'{found_indent:.2f}"',
            suggestion=f"Adjust hanging indent by {diff_pts:.0f}pt",
        )

    @staticmethod
    def bibliography_font_size_violation(
        page: int,
        expected_size: float,
        found_size: float,
    ) -> Violation:
        """Create a bibliography font size violation.

        Args:
            page: Page number where violation occurred.
            expected_size: Expected font size in points.
            found_size: Actual font size in points.

        Returns:
            Violation object.
        """
        return Violation(
            rule_id="bibliography.font_size",
            rule_type=RuleType.BIBLIOGRAPHY,
            severity=Severity.ERROR,
            message=f"Bibliography must use {expected_size:.0f}pt font",
            page=page,
            expected=f"{expected_size:.0f}pt",
            found=f"{found_size:.1f}pt",
            suggestion=f"Change bibliography font to {expected_size:.0f}pt",
        )

    @staticmethod
    def bibliography_spacing_violation(
        page: int,
        spacing_type: str,
        expected_ratio: float,
        found_ratio: float,
    ) -> Violation:
        """Create a bibliography spacing violation.

        Args:
            page: Page number (start of bibliography).
            spacing_type: Type of spacing ("within_entry" or "between_entries").
            expected_ratio: Expected spacing ratio.
            found_ratio: Actual spacing ratio.

        Returns:
            Violation object.
        """
        spacing_names = {
            1.0: "single-spaced",
            1.5: "1.5-spaced",
            2.0: "double-spaced",
        }
        expected_name = spacing_names.get(expected_ratio, f"{expected_ratio}x spaced")

        type_desc = "within entries" if spacing_type == "within_entry" else "between entries"

        return Violation(
            rule_id=f"bibliography.spacing.{spacing_type}",
            rule_type=RuleType.BIBLIOGRAPHY,
            severity=Severity.WARNING,
            message=f"Bibliography {type_desc} should be {expected_name}",
            page=page,
            expected=f"{expected_ratio:.1f}x",
            found=f"{found_ratio:.1f}x",
            suggestion=f"Adjust bibliography spacing {type_desc}",
        )
