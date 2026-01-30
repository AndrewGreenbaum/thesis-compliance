"""Margin extraction from PDF content bounding boxes."""

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import Margins


class MarginExtractor:
    """Extract actual margins from PDF pages based on content position."""

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc

    def get_margins(self, page_num: int) -> Margins | None:
        """Calculate margins for a specific page.

        Margins are calculated as the distance from page edges to the
        outermost content bounding box.

        Args:
            page_num: 1-indexed page number.

        Returns:
            Margins in inches, or None if page has no content.
        """
        page_info = self.doc.get_page_info(page_num)
        content_bbox = self.doc.get_content_bbox(page_num)

        if content_bbox is None:
            return None

        # Convert content bbox to inches
        content_inches = content_bbox.to_inches()

        # Calculate margins as distance from page edge to content
        # Clamp to zero minimum to avoid negative margins
        return Margins(
            left=max(0, content_inches.x0),
            right=max(0, page_info.width_inches - content_inches.x1),
            top=max(0, content_inches.y0),
            bottom=max(0, page_info.height_inches - content_inches.y1),
        )

    def get_all_margins(self, pages: list[int] | None = None) -> dict[int, Margins]:
        """Get margins for multiple pages.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Dictionary mapping page numbers to Margins.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        result: dict[int, Margins] = {}
        for page_num in pages:
            margins = self.get_margins(page_num)
            if margins is not None:
                result[page_num] = margins

        return result

    def get_minimum_margins(self, pages: list[int] | None = None) -> Margins | None:
        """Get the minimum margins across all specified pages.

        This is useful for checking if any page violates margin requirements.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Margins with minimum values found, or None if no pages have content.
        """
        all_margins = self.get_all_margins(pages)
        if not all_margins:
            return None

        return Margins(
            left=min(m.left for m in all_margins.values()),
            right=min(m.right for m in all_margins.values()),
            top=min(m.top for m in all_margins.values()),
            bottom=min(m.bottom for m in all_margins.values()),
        )

    def find_margin_violations(
        self,
        required: Margins,
        pages: list[int] | None = None,
        tolerance: float = 0.05,
    ) -> dict[int, dict[str, tuple[float, float]]]:
        """Find pages where margins are less than required.

        Args:
            required: Required minimum margins in inches.
            pages: List of 1-indexed page numbers, or None for all pages.
            tolerance: Allowed tolerance in inches (default 0.05").

        Returns:
            Dictionary mapping page numbers to violations.
            Each violation is a dict with margin name -> (required, actual).
        """
        all_margins = self.get_all_margins(pages)
        violations: dict[int, dict[str, tuple[float, float]]] = {}

        for page_num, margins in all_margins.items():
            page_violations: dict[str, tuple[float, float]] = {}

            if margins.left < required.left - tolerance:
                page_violations["left"] = (required.left, margins.left)
            if margins.right < required.right - tolerance:
                page_violations["right"] = (required.right, margins.right)
            if margins.top < required.top - tolerance:
                page_violations["top"] = (required.top, margins.top)
            if margins.bottom < required.bottom - tolerance:
                page_violations["bottom"] = (required.bottom, margins.bottom)

            if page_violations:
                violations[page_num] = page_violations

        return violations
