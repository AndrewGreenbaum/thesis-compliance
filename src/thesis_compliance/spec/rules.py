"""Style specification rule models."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class MarginRule:
    """Margin requirements specification."""

    left: float = 1.5  # inches (binding margin)
    right: float = 1.0  # inches
    top: float = 1.0  # inches
    bottom: float = 1.0  # inches
    tolerance: float = 0.05  # inches

    # Applies to specific pages
    applies_to: Literal["all", "front_matter", "body", "title_page"] = "all"


@dataclass
class FontRule:
    """Font requirements specification."""

    # Allowed font families (base names)
    allowed_fonts: list[str] = field(
        default_factory=lambda: ["Times", "Times New Roman", "Arial", "Helvetica"]
    )

    # Required body text size
    body_size: float = 12.0  # points
    size_tolerance: float = 0.5  # points

    # Minimum font size anywhere in document
    min_size: float = 10.0  # points

    # Applies to specific pages
    applies_to: Literal["all", "body"] = "all"


@dataclass
class SpacingRule:
    """Line spacing requirements specification."""

    # Required spacing ratio (2.0 = double, 1.5 = 1.5-spaced)
    required_ratio: float = 2.0
    tolerance: float = 0.2

    # Applies to specific pages
    applies_to: Literal["all", "body"] = "body"


@dataclass
class PageNumberRule:
    """Page number requirements specification."""

    # Front matter requirements
    front_matter_style: Literal["roman", "arabic", "none"] = "roman"
    front_matter_position: Literal["top", "bottom"] = "bottom"
    front_matter_alignment: Literal["left", "center", "right"] = "center"

    # Body requirements
    body_style: Literal["arabic"] = "arabic"
    body_position: Literal["top", "bottom"] = "bottom"
    body_alignment: Literal["left", "center", "right"] = "center"
    body_starts_at: int = 1  # What number body pages start at


@dataclass
class TitlePageRule:
    """Title page specific requirements."""

    # Top margin for title page (often larger than regular pages)
    top_margin: float = 2.0  # inches
    margin_tolerance: float = 0.1  # inches

    # Should title page have a page number?
    has_page_number: bool = False


@dataclass
class HeadingRule:
    """Chapter and section heading requirements."""

    # Chapter heading (level 1) requirements
    chapter_font_size: float = 14.0  # points
    chapter_bold: bool = True
    chapter_all_caps: bool = True

    # Section heading (level 2) requirements
    section_font_size: float = 12.0  # points
    section_bold: bool = True

    # Subsection heading (level 3) requirements
    subsection_font_size: float = 12.0  # points
    subsection_bold: bool = False
    subsection_italic: bool = True

    # Spacing before headings
    space_before_chapter: float = 2.0  # inches from top of page
    space_before_section: float = 24.0  # points
    space_before_subsection: float = 12.0  # points

    # Size tolerance
    size_tolerance: float = 0.5  # points


@dataclass
class CaptionRule:
    """Figure and table caption requirements."""

    # Caption font size
    font_size: float = 10.0  # points (often smaller than body)
    size_tolerance: float = 0.5  # points

    # Caption positioning
    figure_position: Literal["above", "below"] = "below"
    table_position: Literal["above", "below"] = "above"

    # Label format
    figure_label: str = "Figure"  # e.g., "Figure 1:" or "Fig. 1."
    table_label: str = "Table"

    # Numbering style
    numbering: Literal["continuous", "by_chapter"] = "continuous"


@dataclass
class BibliographyRule:
    """Bibliography/references requirements."""

    # Hanging indent for entries
    hanging_indent: float = 0.5  # inches
    indent_tolerance: float = 0.1  # inches

    # Line spacing within entries
    entry_spacing: float = 1.0  # single-spaced within entries
    between_entries: float = 2.0  # double-spaced between entries
    spacing_tolerance: float = 0.2

    # Font requirements (often same as body, but can differ)
    font_size: float = 12.0  # points
    size_tolerance: float = 0.5  # points


@dataclass
class StyleSpec:
    """Complete style specification for a thesis format."""

    # Metadata
    name: str
    university: str
    description: str = ""
    version: str = "1.0"
    url: str = ""  # Link to official requirements

    # Rules
    margins: MarginRule = field(default_factory=MarginRule)
    fonts: FontRule = field(default_factory=FontRule)
    spacing: SpacingRule = field(default_factory=SpacingRule)
    page_numbers: PageNumberRule = field(default_factory=PageNumberRule)
    title_page: TitlePageRule = field(default_factory=TitlePageRule)

    # Optional extended rules
    headings: HeadingRule | None = None
    captions: CaptionRule | None = None
    bibliography: BibliographyRule | None = None

    # Additional margin rules (e.g., different margins for title page)
    additional_margins: list[MarginRule] = field(default_factory=list)

    @property
    def rule_count(self) -> int:
        """Count total number of rules in this spec."""
        count = 0

        # Margin rules (4 per MarginRule)
        count += 4
        count += len(self.additional_margins) * 4

        # Font rules (font family, size, min size)
        count += 3

        # Spacing rule
        count += 1

        # Page number rules (front matter + body)
        count += 6

        # Title page rules
        count += 2

        # Heading rules (if present)
        if self.headings is not None:
            count += 6  # chapter, section, subsection font/style

        # Caption rules (if present)
        if self.captions is not None:
            count += 3  # font size, position, numbering

        # Bibliography rules (if present)
        if self.bibliography is not None:
            count += 3  # hanging indent, spacing, font size

        return count

    def get_margin_rule_for_page(
        self, page_type: Literal["title_page", "front_matter", "body"]
    ) -> MarginRule:
        """Get the appropriate margin rule for a page type.

        Args:
            page_type: Type of page.

        Returns:
            MarginRule that applies to this page type.
        """
        # Check additional rules first
        for rule in self.additional_margins:
            if rule.applies_to == page_type:
                return rule

        # Fall back to main rule
        return self.margins
