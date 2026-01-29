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
