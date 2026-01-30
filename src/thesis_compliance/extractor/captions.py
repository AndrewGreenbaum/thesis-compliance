"""Caption extraction and analysis from PDFs."""

import re
from dataclasses import dataclass
from typing import Literal

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import TextBlock


@dataclass
class CaptionInfo:
    """Information about a detected figure or table caption."""

    text: str
    caption_type: Literal["figure", "table"]
    number: str  # The figure/table number (e.g., "1", "2.1", "A.1")
    page_number: int
    font_size: float
    y_position: float  # Position from top of page in points
    label_format: str  # Detected label format (e.g., "Figure", "Fig.", "Table")


@dataclass
class CaptionSequence:
    """Analysis of caption numbering sequence."""

    caption_type: Literal["figure", "table"]
    captions: list[CaptionInfo]
    is_continuous: bool  # True if numbered 1, 2, 3...; False if by chapter (1.1, 2.1...)
    sequence_issues: list[str]  # Any numbering issues found


class CaptionExtractor:
    """Extract and analyze figure/table captions from a PDF document."""

    # Common caption patterns
    FIGURE_PATTERNS = [
        r"^(Figure|Fig\.?)\s+(\d+(?:\.\d+)?(?:[a-zA-Z])?)\s*[:\.]?\s*",
        r"^(FIGURE)\s+(\d+(?:\.\d+)?(?:[a-zA-Z])?)\s*[:\.]?\s*",
    ]

    TABLE_PATTERNS = [
        r"^(Table)\s+(\d+(?:\.\d+)?(?:[a-zA-Z])?)\s*[:\.]?\s*",
        r"^(TABLE)\s+(\d+(?:\.\d+)?(?:[a-zA-Z])?)\s*[:\.]?\s*",
    ]

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc

    def get_captions_on_page(self, page_num: int) -> list[CaptionInfo]:
        """Get all captions detected on a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of CaptionInfo objects.
        """
        blocks = self.doc.get_text_blocks(page_num)
        if not blocks:
            return []

        captions: list[CaptionInfo] = []

        for block in blocks:
            caption = self._detect_caption(block)
            if caption is not None:
                captions.append(caption)

        return captions

    def get_all_captions(self, pages: list[int] | None = None) -> dict[int, list[CaptionInfo]]:
        """Get all captions in the document.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            Dictionary mapping page numbers to lists of CaptionInfo.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        result: dict[int, list[CaptionInfo]] = {}
        for page_num in pages:
            page_captions = self.get_captions_on_page(page_num)
            if page_captions:
                result[page_num] = page_captions

        return result

    def _detect_caption(self, block: TextBlock) -> CaptionInfo | None:
        """Detect if a text block is a caption.

        Args:
            block: TextBlock to analyze.

        Returns:
            CaptionInfo if block is a caption, None otherwise.
        """
        text = block.text.strip()
        if not text or len(text) < 5:
            return None

        # Check figure patterns
        for pattern in self.FIGURE_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return CaptionInfo(
                    text=text,
                    caption_type="figure",
                    number=match.group(2),
                    page_number=block.page_number,
                    font_size=block.font.size,
                    y_position=block.bbox.y0,
                    label_format=match.group(1),
                )

        # Check table patterns
        for pattern in self.TABLE_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return CaptionInfo(
                    text=text,
                    caption_type="table",
                    number=match.group(2),
                    page_number=block.page_number,
                    font_size=block.font.size,
                    y_position=block.bbox.y0,
                    label_format=match.group(1),
                )

        return None

    def analyze_caption_sequence(
        self, pages: list[int] | None = None
    ) -> tuple[CaptionSequence, CaptionSequence]:
        """Analyze the numbering sequence of figures and tables.

        Args:
            pages: Pages to analyze (None for all).

        Returns:
            Tuple of (figure_sequence, table_sequence).
        """
        all_captions = self.get_all_captions(pages)

        # Collect all figure and table captions
        figures: list[CaptionInfo] = []
        tables: list[CaptionInfo] = []

        for page_captions in all_captions.values():
            for caption in page_captions:
                if caption.caption_type == "figure":
                    figures.append(caption)
                else:
                    tables.append(caption)

        # Analyze sequences
        figure_seq = self._analyze_sequence(figures, "figure")
        table_seq = self._analyze_sequence(tables, "table")

        return figure_seq, table_seq

    def _analyze_sequence(
        self,
        captions: list[CaptionInfo],
        caption_type: Literal["figure", "table"],
    ) -> CaptionSequence:
        """Analyze a sequence of captions for numbering issues.

        Args:
            captions: List of captions to analyze.
            caption_type: Type of caption.

        Returns:
            CaptionSequence with analysis results.
        """
        if not captions:
            return CaptionSequence(
                caption_type=caption_type,
                captions=[],
                is_continuous=True,
                sequence_issues=[],
            )

        issues: list[str] = []

        # Determine if continuous or by-chapter numbering
        has_dot = any("." in c.number for c in captions)
        is_continuous = not has_dot

        # Check sequence
        if is_continuous:
            # Expect 1, 2, 3, ...
            expected = 1
            for caption in captions:
                try:
                    # Handle numbers like "1a", "1b"
                    num_match = re.match(r"(\d+)", caption.number)
                    if num_match:
                        actual = int(num_match.group(1))
                        if actual != expected:
                            issues.append(
                                f"{caption_type.title()} {caption.number} on page "
                                f"{caption.page_number}: expected {expected}"
                            )
                        expected = actual + 1
                except ValueError:
                    issues.append(
                        f"Invalid {caption_type} number '{caption.number}' "
                        f"on page {caption.page_number}"
                    )
        else:
            # By-chapter numbering (1.1, 1.2, 2.1, ...)
            # Track expected next number per chapter
            chapter_counts: dict[str, int] = {}
            for caption in captions:
                parts = caption.number.split(".")
                if len(parts) >= 2:
                    chapter = parts[0]
                    try:
                        fig_num = int(parts[1].rstrip("abcdefghijklmnopqrstuvwxyz"))
                        expected = chapter_counts.get(chapter, 1)
                        if fig_num != expected:
                            issues.append(
                                f"{caption_type.title()} {caption.number} on page "
                                f"{caption.page_number}: expected {chapter}.{expected}"
                            )
                        chapter_counts[chapter] = fig_num + 1
                    except ValueError:
                        issues.append(
                            f"Invalid {caption_type} number '{caption.number}' "
                            f"on page {caption.page_number}"
                        )

        return CaptionSequence(
            caption_type=caption_type,
            captions=captions,
            is_continuous=is_continuous,
            sequence_issues=issues,
        )

    def check_caption_compliance(
        self,
        font_size: float = 10.0,
        size_tolerance: float = 0.5,
        figure_label: str = "Figure",
        table_label: str = "Table",
        numbering: Literal["continuous", "by_chapter"] = "continuous",
        pages: list[int] | None = None,
    ) -> tuple[bool, list[tuple[int, CaptionInfo, str]]]:
        """Check if captions comply with requirements.

        Args:
            font_size: Required caption font size in points.
            size_tolerance: Allowed size deviation in points.
            figure_label: Expected figure label (e.g., "Figure" or "Fig.").
            table_label: Expected table label.
            numbering: Expected numbering style.
            pages: Pages to check (None for all).

        Returns:
            Tuple of (compliant, list of (page, caption, issue) tuples).
        """
        all_captions = self.get_all_captions(pages)
        issues: list[tuple[int, CaptionInfo, str]] = []

        for page_num, page_captions in all_captions.items():
            for caption in page_captions:
                # Check font size
                if abs(caption.font_size - font_size) > size_tolerance:
                    issues.append(
                        (
                            page_num,
                            caption,
                            f"Caption font size {caption.font_size:.1f}pt "
                            f"should be {font_size:.1f}pt",
                        )
                    )

                # Check label format
                if caption.caption_type == "figure":
                    # Allow common variations
                    if not (caption.label_format.lower().startswith(figure_label.lower()[:3])):
                        issues.append(
                            (
                                page_num,
                                caption,
                                f"Figure label '{caption.label_format}' should be '{figure_label}'",
                            )
                        )
                else:
                    if not caption.label_format.lower().startswith(table_label.lower()[:3]):
                        issues.append(
                            (
                                page_num,
                                caption,
                                f"Table label '{caption.label_format}' should be '{table_label}'",
                            )
                        )

        # Check numbering sequence
        figure_seq, table_seq = self.analyze_caption_sequence(pages)

        expected_continuous = numbering == "continuous"
        if figure_seq.captions and figure_seq.is_continuous != expected_continuous:
            style = "continuous" if expected_continuous else "by-chapter"
            issues.append(
                (
                    0,  # Document-wide issue
                    figure_seq.captions[0],
                    f"Figure numbering should be {style}",
                )
            )

        if table_seq.captions and table_seq.is_continuous != expected_continuous:
            style = "continuous" if expected_continuous else "by-chapter"
            issues.append(
                (
                    0,
                    table_seq.captions[0],
                    f"Table numbering should be {style}",
                )
            )

        # Add any sequence issues
        for issue_text in figure_seq.sequence_issues + table_seq.sequence_issues:
            # Create a placeholder caption for the issue
            issues.append(
                (
                    0,
                    figure_seq.captions[0] if figure_seq.captions else table_seq.captions[0],
                    issue_text,
                )
            )

        return len(issues) == 0, issues
