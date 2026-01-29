"""Font extraction and analysis from PDFs."""

from collections import Counter
from dataclasses import dataclass

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import FontInfo, TextBlock


@dataclass
class FontUsage:
    """Statistics about font usage in the document."""

    font_name: str
    sizes: set[float]
    occurrence_count: int
    is_body_font: bool = False  # Whether this appears to be the main body font


class FontExtractor:
    """Extract and analyze fonts used in a PDF document."""

    # Common acceptable body fonts (base names without style suffixes)
    ACCEPTABLE_BODY_FONTS = {
        "Times",
        "TimesNewRoman",
        "Times-Roman",
        "Times New Roman",
        "Arial",
        "Helvetica",
        "Georgia",
        "Cambria",
        "Calibri",
        "Garamond",
        "Palatino",
        "Book Antiqua",
        "Century",
        "CMR",  # Computer Modern Roman (LaTeX)
        "CMSS",  # Computer Modern Sans
        "LMRoman",  # Latin Modern Roman
        "TeXGyreTermes",  # TeX Gyre Times
        "TeXGyreHeros",  # TeX Gyre Helvetica
    }

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc

    def get_fonts_on_page(self, page_num: int) -> list[FontInfo]:
        """Get all unique fonts used on a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of unique FontInfo objects.
        """
        blocks = self.doc.get_text_blocks(page_num)
        seen: set[tuple[str, float]] = set()
        fonts: list[FontInfo] = []

        for block in blocks:
            key = (block.font.name, block.font.size)
            if key not in seen:
                seen.add(key)
                fonts.append(block.font)

        return fonts

    def get_font_usage(self, pages: list[int] | None = None) -> dict[str, FontUsage]:
        """Analyze font usage across pages.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Dictionary mapping font base names to FontUsage statistics.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        # Count occurrences by font name
        font_counts: Counter[str] = Counter()
        font_sizes: dict[str, set[float]] = {}

        for page_num in pages:
            blocks = self.doc.get_text_blocks(page_num)
            for block in blocks:
                base_name = block.font.base_name
                font_counts[base_name] += len(block.text)
                if base_name not in font_sizes:
                    font_sizes[base_name] = set()
                font_sizes[base_name].add(round(block.font.size, 1))

        # Determine body font (most common by character count)
        most_common = font_counts.most_common(1)
        body_font = most_common[0][0] if most_common else None

        result: dict[str, FontUsage] = {}
        for font_name, count in font_counts.items():
            result[font_name] = FontUsage(
                font_name=font_name,
                sizes=font_sizes.get(font_name, set()),
                occurrence_count=count,
                is_body_font=(font_name == body_font),
            )

        return result

    def get_body_font(self, pages: list[int] | None = None) -> FontUsage | None:
        """Identify the main body font.

        The body font is determined by character count - the font used
        for the most text is assumed to be the body font.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            FontUsage for the body font, or None if no text found.
        """
        usage = self.get_font_usage(pages)
        for font_usage in usage.values():
            if font_usage.is_body_font:
                return font_usage
        return None

    def check_body_font_compliance(
        self,
        allowed_fonts: set[str] | None = None,
        required_size: float = 12.0,
        size_tolerance: float = 0.5,
        pages: list[int] | None = None,
    ) -> tuple[bool, list[str]]:
        """Check if body font meets requirements.

        Args:
            allowed_fonts: Set of allowed font names (uses defaults if None).
            required_size: Required font size in points.
            size_tolerance: Allowed size deviation in points.
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Tuple of (compliant, list of issues).
        """
        if allowed_fonts is None:
            allowed_fonts = self.ACCEPTABLE_BODY_FONTS

        body_font = self.get_body_font(pages)
        if body_font is None:
            return False, ["No body text found in document"]

        issues: list[str] = []

        # Check font name
        font_allowed = any(
            allowed.lower() in body_font.font_name.lower() for allowed in allowed_fonts
        )
        if not font_allowed:
            issues.append(
                f"Body font '{body_font.font_name}' is not in allowed fonts: "
                f"{', '.join(sorted(allowed_fonts))}"
            )

        # Check font size - body text should primarily use required size
        primary_sizes = [s for s in body_font.sizes if abs(s - required_size) <= size_tolerance]
        if not primary_sizes:
            issues.append(
                f"Body font size {min(body_font.sizes)}pt does not match "
                f"required {required_size}pt (±{size_tolerance}pt)"
            )

        return len(issues) == 0, issues

    def find_font_size_violations(
        self,
        min_size: float,
        max_size: float | None = None,
        pages: list[int] | None = None,
    ) -> dict[int, list[tuple[str, float]]]:
        """Find text that doesn't meet size requirements.

        Args:
            min_size: Minimum allowed font size in points.
            max_size: Maximum allowed font size in points (None = no max).
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Dictionary mapping page numbers to list of (font_name, size) violations.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        violations: dict[int, list[tuple[str, float]]] = {}

        for page_num in pages:
            page_violations: list[tuple[str, float]] = []
            blocks = self.doc.get_text_blocks(page_num)

            for block in blocks:
                size = block.font.size
                if size < min_size or (max_size is not None and size > max_size):
                    page_violations.append((block.font.name, size))

            if page_violations:
                # Deduplicate
                violations[page_num] = list(set(page_violations))

        return violations
