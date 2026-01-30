"""Heading extraction and analysis from PDFs."""

import re
from dataclasses import dataclass

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import TextBlock


@dataclass
class HeadingInfo:
    """Information about a detected heading."""

    text: str
    level: int  # 1 = chapter, 2 = section, 3 = subsection
    page_number: int
    font_size: float
    is_bold: bool
    is_italic: bool
    is_all_caps: bool
    y_position: float  # Position from top of page in points
    space_before: float  # Space before heading in points (from top or previous content)


class HeadingExtractor:
    """Extract and analyze chapter/section headings from a PDF document."""

    # Common heading patterns
    CHAPTER_PATTERNS = [
        r"^CHAPTER\s+[IVXLCDM\d]+",  # CHAPTER 1, CHAPTER I
        r"^Chapter\s+[IVXLCDM\d]+",  # Chapter 1, Chapter I
        r"^\d+\.\s+[A-Z]",  # 1. Introduction (numbered section)
    ]

    SECTION_PATTERNS = [
        r"^\d+\.\d+\s+",  # 1.1 Section title
        r"^[IVXLCDM]+\.\s+",  # I. Section title
    ]

    SUBSECTION_PATTERNS = [
        r"^\d+\.\d+\.\d+\s+",  # 1.1.1 Subsection title
        r"^[a-z]\)\s+",  # a) Subsection
    ]

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc
        self._headings_cache: dict[int, list[HeadingInfo]] | None = None

    def get_headings_on_page(self, page_num: int) -> list[HeadingInfo]:
        """Get all headings detected on a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of HeadingInfo objects.
        """
        blocks = self.doc.get_text_blocks(page_num)
        if not blocks:
            return []

        headings: list[HeadingInfo] = []
        page_info = self.doc.get_page_info(page_num)

        # Sort blocks by vertical position
        sorted_blocks = sorted(blocks, key=lambda b: b.bbox.y0)

        prev_bottom = 0.0
        for block in sorted_blocks:
            heading = self._classify_heading(block, page_info.height_pt, prev_bottom)
            if heading is not None:
                headings.append(heading)
            prev_bottom = block.bbox.y1

        return headings

    def get_all_headings(self, pages: list[int] | None = None) -> dict[int, list[HeadingInfo]]:
        """Get all headings in the document.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Dictionary mapping page numbers to lists of HeadingInfo.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        result: dict[int, list[HeadingInfo]] = {}
        for page_num in pages:
            page_headings = self.get_headings_on_page(page_num)
            if page_headings:
                result[page_num] = page_headings

        return result

    def _classify_heading(
        self, block: TextBlock, page_height: float, prev_bottom: float
    ) -> HeadingInfo | None:
        """Classify a text block as a heading if it matches heading criteria.

        Args:
            block: TextBlock to analyze.
            page_height: Height of the page in points.
            prev_bottom: Bottom position of previous content in points.

        Returns:
            HeadingInfo if block is a heading, None otherwise.
        """
        text = block.text.strip()
        if not text or len(text) < 2:
            return None

        # Check if all caps
        is_all_caps = text.isupper() and any(c.isalpha() for c in text)

        # Calculate space before
        space_before = block.bbox.y0 - prev_bottom if prev_bottom > 0 else block.bbox.y0

        # Determine heading level
        level = self._determine_heading_level(
            text=text,
            font_size=block.font.size,
            is_bold=block.font.is_bold,
            is_italic=block.font.is_italic,
            is_all_caps=is_all_caps,
            y_position=block.bbox.y0,
            page_height=page_height,
        )

        if level is None:
            return None

        return HeadingInfo(
            text=text,
            level=level,
            page_number=block.page_number,
            font_size=block.font.size,
            is_bold=block.font.is_bold,
            is_italic=block.font.is_italic,
            is_all_caps=is_all_caps,
            y_position=block.bbox.y0,
            space_before=space_before,
        )

    def _determine_heading_level(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        is_italic: bool,
        is_all_caps: bool,
        y_position: float,
        page_height: float,
    ) -> int | None:
        """Determine the heading level based on formatting and patterns.

        Args:
            text: The heading text.
            font_size: Font size in points.
            is_bold: Whether text is bold.
            is_italic: Whether text is italic.
            is_all_caps: Whether text is all caps.
            y_position: Y position from top of page in points.
            page_height: Total page height in points.

        Returns:
            Heading level (1, 2, or 3) or None if not a heading.
        """
        # Check for chapter heading patterns
        for pattern in self.CHAPTER_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return 1

        # Check for section heading patterns
        for pattern in self.SECTION_PATTERNS:
            if re.match(pattern, text):
                return 2

        # Check for subsection heading patterns
        for pattern in self.SUBSECTION_PATTERNS:
            if re.match(pattern, text):
                return 3

        # Heuristic: Large, bold, all caps near top of page = chapter
        if font_size >= 14.0 and is_bold and is_all_caps:
            # Near top quarter of page
            if y_position < page_height * 0.30:
                return 1

        # Heuristic: Bold text larger than 12pt could be section heading
        if is_bold and font_size >= 12.0 and not is_italic:
            # Single line, short text
            if len(text) < 100 and "\n" not in text:
                return 2

        # Heuristic: Bold or italic text at 12pt = subsection
        if (is_bold or is_italic) and 11.5 <= font_size <= 12.5:
            if len(text) < 80 and "\n" not in text:
                return 3

        return None

    def check_heading_compliance(
        self,
        chapter_font_size: float = 14.0,
        chapter_bold: bool = True,
        chapter_all_caps: bool = True,
        section_font_size: float = 12.0,
        section_bold: bool = True,
        subsection_font_size: float = 12.0,
        subsection_italic: bool = True,
        size_tolerance: float = 0.5,
        pages: list[int] | None = None,
    ) -> tuple[bool, list[tuple[int, HeadingInfo, str]]]:
        """Check if headings comply with requirements.

        Args:
            chapter_font_size: Required chapter heading size.
            chapter_bold: Whether chapters must be bold.
            chapter_all_caps: Whether chapters must be all caps.
            section_font_size: Required section heading size.
            section_bold: Whether sections must be bold.
            subsection_font_size: Required subsection heading size.
            subsection_italic: Whether subsections must be italic.
            size_tolerance: Allowed size deviation in points.
            pages: Pages to check (None for all).

        Returns:
            Tuple of (compliant, list of (page, heading, issue) tuples).
        """
        all_headings = self.get_all_headings(pages)
        issues: list[tuple[int, HeadingInfo, str]] = []

        for page_num, headings in all_headings.items():
            for heading in headings:
                if heading.level == 1:  # Chapter
                    if abs(heading.font_size - chapter_font_size) > size_tolerance:
                        issues.append(
                            (
                                page_num,
                                heading,
                                f"Chapter heading font size {heading.font_size:.1f}pt "
                                f"should be {chapter_font_size:.1f}pt",
                            )
                        )
                    if chapter_bold and not heading.is_bold:
                        issues.append(
                            (
                                page_num,
                                heading,
                                "Chapter heading should be bold",
                            )
                        )
                    if chapter_all_caps and not heading.is_all_caps:
                        issues.append(
                            (
                                page_num,
                                heading,
                                "Chapter heading should be ALL CAPS",
                            )
                        )

                elif heading.level == 2:  # Section
                    if abs(heading.font_size - section_font_size) > size_tolerance:
                        issues.append(
                            (
                                page_num,
                                heading,
                                f"Section heading font size {heading.font_size:.1f}pt "
                                f"should be {section_font_size:.1f}pt",
                            )
                        )
                    if section_bold and not heading.is_bold:
                        issues.append(
                            (
                                page_num,
                                heading,
                                "Section heading should be bold",
                            )
                        )

                elif heading.level == 3:  # Subsection
                    if abs(heading.font_size - subsection_font_size) > size_tolerance:
                        issues.append(
                            (
                                page_num,
                                heading,
                                f"Subsection heading font size {heading.font_size:.1f}pt "
                                f"should be {subsection_font_size:.1f}pt",
                            )
                        )
                    if subsection_italic and not heading.is_italic:
                        issues.append(
                            (
                                page_num,
                                heading,
                                "Subsection heading should be italic",
                            )
                        )

        return len(issues) == 0, issues
