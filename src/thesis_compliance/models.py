"""Core data models for thesis compliance checking."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    """Severity level of a compliance violation."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleType(str, Enum):
    """Types of compliance rules."""

    MARGIN = "margin"
    FONT = "font"
    SPACING = "spacing"
    PAGE_NUMBER = "page_number"
    TITLE_PAGE = "title_page"
    HEADING = "heading"
    CAPTION = "caption"
    BIBLIOGRAPHY = "bibliography"


@dataclass
class PageInfo:
    """Information about a single PDF page."""

    number: int  # 1-indexed page number
    width_pt: float
    height_pt: float
    width_inches: float
    height_inches: float

    @classmethod
    def from_points(cls, number: int, width_pt: float, height_pt: float) -> "PageInfo":
        """Create PageInfo from point measurements."""
        return cls(
            number=number,
            width_pt=width_pt,
            height_pt=height_pt,
            width_inches=width_pt / 72.0,
            height_inches=height_pt / 72.0,
        )


@dataclass
class BoundingBox:
    """A bounding box in points (1/72 inch)."""

    x0: float  # left
    y0: float  # top
    x1: float  # right
    y1: float  # bottom

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def to_inches(self) -> "BoundingBox":
        """Convert to inches."""
        return BoundingBox(
            x0=self.x0 / 72.0,
            y0=self.y0 / 72.0,
            x1=self.x1 / 72.0,
            y1=self.y1 / 72.0,
        )


@dataclass
class Margins:
    """Page margins in inches."""

    left: float
    right: float
    top: float
    bottom: float

    def to_dict(self) -> dict[str, float]:
        return {
            "left": self.left,
            "right": self.right,
            "top": self.top,
            "bottom": self.bottom,
        }


@dataclass
class FontInfo:
    """Information about a font used in the document."""

    name: str
    size: float  # in points
    is_bold: bool = False
    is_italic: bool = False
    color: str = "#000000"

    @property
    def base_name(self) -> str:
        """Get the base font name without style suffixes."""
        name = self.name
        for suffix in ["-Bold", "-Italic", "-BoldItalic", "Bold", "Italic", ",Bold", ",Italic"]:
            name = name.replace(suffix, "")
        return name


@dataclass
class TextBlock:
    """A block of text with position and style information."""

    text: str
    bbox: BoundingBox
    font: FontInfo
    page_number: int
    baseline: float  # y-coordinate of text baseline in points


@dataclass
class LineSpacing:
    """Line spacing information for a text region."""

    ratio: float  # spacing ratio (2.0 = double, 1.5 = 1.5-spaced, 1.0 = single)
    baseline_distance: float  # in points
    font_size: float  # in points
    page_number: int
    start_line: int
    end_line: int


@dataclass
class PageNumber:
    """Detected page number on a page."""

    value: str  # The displayed value (e.g., "iii", "42")
    style: str  # "roman" or "arabic"
    position: str  # "top", "bottom"
    alignment: str  # "left", "center", "right"
    page_index: int  # 0-indexed page in PDF


@dataclass
class Violation:
    """A single compliance violation."""

    rule_id: str
    rule_type: RuleType
    severity: Severity
    message: str
    page: int | None = None
    expected: Any = None
    found: Any = None
    suggestion: str | None = None
    location: BoundingBox | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type.value,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.page is not None:
            result["page"] = self.page
        if self.expected is not None:
            result["expected"] = self.expected
        if self.found is not None:
            result["found"] = self.found
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.location:
            result["location"] = {
                "x0": self.location.x0,
                "y0": self.location.y0,
                "x1": self.location.x1,
                "y1": self.location.y1,
            }
        return result


@dataclass
class ComplianceReport:
    """Complete compliance report for a thesis."""

    pdf_path: Path
    spec_name: str
    pages_checked: int
    rules_checked: int
    violations: list[Violation] = field(default_factory=list)

    @property
    def errors(self) -> list[Violation]:
        """Get all error-level violations."""
        return [v for v in self.violations if v.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        """Get all warning-level violations."""
        return [v for v in self.violations if v.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        """Check if the document passed (no errors)."""
        return len(self.errors) == 0

    @property
    def passed_strict(self) -> bool:
        """Check if the document passed strictly (no errors or warnings)."""
        return len(self.violations) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pdf_path": str(self.pdf_path),
            "spec_name": self.spec_name,
            "pages_checked": self.pages_checked,
            "rules_checked": self.rules_checked,
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "violations": [v.to_dict() for v in self.violations],
        }
