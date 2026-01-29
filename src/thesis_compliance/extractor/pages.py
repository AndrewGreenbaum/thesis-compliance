"""Page number detection and analysis."""

import re
from dataclasses import dataclass

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import PageNumber, TextBlock


@dataclass
class PageNumberAnalysis:
    """Analysis of page numbering in a document."""

    front_matter_pages: list[int]  # Pages with Roman numerals
    body_pages: list[int]  # Pages with Arabic numbers
    unnumbered_pages: list[int]  # Pages without visible numbers
    numbering_style: str  # "standard" (roman then arabic), "arabic_only", "mixed", "none"
    issues: list[str]


class PageNumberExtractor:
    """Extract and analyze page numbers from PDF documents."""

    # Roman numeral patterns
    ROMAN_PATTERN = re.compile(
        r"^(i{1,3}|iv|vi{0,3}|ix|xi{0,3}|xiv|xvi{0,3}|xix|xxi{0,3})$",
        re.IGNORECASE,
    )

    # Arabic number pattern
    ARABIC_PATTERN = re.compile(r"^\d+$")

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc

    def _is_page_number_candidate(self, block: TextBlock, page_info_height: float) -> bool:
        """Check if a text block might be a page number.

        Page numbers are typically:
        - Short text (1-4 characters)
        - Near top or bottom of page
        - Centered or near margins

        Args:
            block: TextBlock to check.
            page_info_height: Page height in points.

        Returns:
            True if block is a candidate page number.
        """
        text = block.text.strip()

        # Must be short
        if len(text) > 6:
            return False

        # Must match a number pattern
        if not (self.ROMAN_PATTERN.match(text) or self.ARABIC_PATTERN.match(text)):
            return False

        # Must be near top or bottom (within 1.5 inches)
        margin = 1.5 * 72  # 1.5 inches in points
        y_center = (block.bbox.y0 + block.bbox.y1) / 2

        is_near_top = y_center < margin
        is_near_bottom = y_center > (page_info_height - margin)

        return is_near_top or is_near_bottom

    def _determine_position(self, block: TextBlock, page_width: float) -> str:
        """Determine horizontal position of a block.

        Args:
            block: TextBlock to analyze.
            page_width: Page width in points.

        Returns:
            One of: "left", "center", "right"
        """
        x_center = (block.bbox.x0 + block.bbox.x1) / 2
        relative_pos = x_center / page_width

        if relative_pos < 0.35:
            return "left"
        elif relative_pos > 0.65:
            return "right"
        else:
            return "center"

    def _determine_vertical_position(self, block: TextBlock, page_height: float) -> str:
        """Determine vertical position of a block.

        Args:
            block: TextBlock to analyze.
            page_height: Page height in points.

        Returns:
            One of: "top", "bottom"
        """
        y_center = (block.bbox.y0 + block.bbox.y1) / 2
        return "top" if y_center < page_height / 2 else "bottom"

    def get_page_number(self, page_num: int) -> PageNumber | None:
        """Extract page number from a specific page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            PageNumber if found, None otherwise.
        """
        page_info = self.doc.get_page_info(page_num)
        blocks = self.doc.get_text_blocks(page_num)

        candidates: list[tuple[TextBlock, float]] = []

        for block in blocks:
            if self._is_page_number_candidate(block, page_info.height_pt):
                # Score by distance from page edges
                y_center = (block.bbox.y0 + block.bbox.y1) / 2
                dist_from_edge = min(y_center, page_info.height_pt - y_center)
                candidates.append((block, dist_from_edge))

        if not candidates:
            return None

        # Pick the candidate closest to edge
        best_block = min(candidates, key=lambda x: x[1])[0]
        text = best_block.text.strip()

        # Determine style
        if self.ROMAN_PATTERN.match(text):
            style = "roman"
        else:
            style = "arabic"

        return PageNumber(
            value=text,
            style=style,
            position=self._determine_vertical_position(best_block, page_info.height_pt),
            alignment=self._determine_position(best_block, page_info.width_pt),
            page_index=page_num - 1,
        )

    def analyze_page_numbers(self) -> PageNumberAnalysis:
        """Analyze page numbering throughout the document.

        Returns:
            PageNumberAnalysis with categorized pages and issues.
        """
        front_matter: list[int] = []
        body: list[int] = []
        unnumbered: list[int] = []
        issues: list[str] = []

        last_style: str | None = None
        seen_arabic = False

        for page_num in range(1, self.doc.page_count + 1):
            page_number = self.get_page_number(page_num)

            if page_number is None:
                unnumbered.append(page_num)
                continue

            if page_number.style == "roman":
                front_matter.append(page_num)
                if seen_arabic:
                    issues.append(
                        f"Page {page_num}: Roman numeral '{page_number.value}' "
                        f"appears after Arabic numbers"
                    )
            else:
                body.append(page_num)
                seen_arabic = True

            last_style = page_number.style

        # Determine numbering style
        if not front_matter and not body:
            numbering_style = "none"
        elif front_matter and body:
            # Check if front matter comes before body
            if front_matter and body and max(front_matter) < min(body):
                numbering_style = "standard"
            else:
                numbering_style = "mixed"
        elif body:
            numbering_style = "arabic_only"
        else:
            numbering_style = "roman_only"

        return PageNumberAnalysis(
            front_matter_pages=front_matter,
            body_pages=body,
            unnumbered_pages=unnumbered,
            numbering_style=numbering_style,
            issues=issues,
        )

    def check_page_number_compliance(
        self,
        require_roman_front_matter: bool = True,
        require_centered: bool = True,
    ) -> tuple[bool, list[str]]:
        """Check if page numbering meets typical thesis requirements.

        Args:
            require_roman_front_matter: Require Roman numerals for front matter.
            require_centered: Require centered page numbers.

        Returns:
            Tuple of (compliant, list of issues).
        """
        issues: list[str] = []
        analysis = self.analyze_page_numbers()

        issues.extend(analysis.issues)

        if require_roman_front_matter and analysis.numbering_style not in ["standard", "none"]:
            if not analysis.front_matter_pages and analysis.body_pages:
                issues.append(
                    "Front matter should use Roman numerals before body page numbers"
                )

        if require_centered:
            for page_num in range(1, self.doc.page_count + 1):
                page_number = self.get_page_number(page_num)
                if page_number and page_number.alignment != "center":
                    issues.append(
                        f"Page {page_num}: Page number '{page_number.value}' "
                        f"is {page_number.alignment}-aligned, should be centered"
                    )

        return len(issues) == 0, issues
