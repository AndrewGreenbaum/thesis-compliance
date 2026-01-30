"""Bibliography extraction and analysis from PDFs."""

import re
from dataclasses import dataclass

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import TextBlock


@dataclass
class BibliographyEntry:
    """Information about a single bibliography entry."""

    text: str
    page_number: int
    first_line_indent: float  # Left position of first line in points
    continuation_indent: float  # Left position of continuation lines in points
    font_size: float
    line_count: int  # Number of lines in this entry


@dataclass
class BibliographyInfo:
    """Information about the bibliography section."""

    start_page: int
    end_page: int
    entries: list[BibliographyEntry]
    avg_hanging_indent: float  # Average hanging indent in inches
    avg_entry_spacing: float  # Average spacing ratio within entries
    avg_between_spacing: float  # Average spacing ratio between entries


class BibliographyExtractor:
    """Extract and analyze bibliography/references from a PDF document."""

    # Common bibliography section headers
    SECTION_PATTERNS = [
        r"^(?:REFERENCES|References)$",
        r"^(?:BIBLIOGRAPHY|Bibliography)$",
        r"^(?:WORKS CITED|Works Cited)$",
        r"^(?:LITERATURE CITED|Literature Cited)$",
        r"^(?:CITED REFERENCES|Cited References)$",
    ]

    # Patterns that indicate start of a bibliography entry
    ENTRY_START_PATTERNS = [
        r"^\[\d+\]",  # [1] Author...
        r"^\d+\.\s+",  # 1. Author...
        r"^[A-Z][a-z]+,\s+[A-Z]\.",  # Author, A. B.
        r"^[A-Z][a-z]+,\s+[A-Z][a-z]+",  # Author, Firstname
    ]

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc
        self._bib_info_cache: BibliographyInfo | None = None

    def find_bibliography_section(self) -> tuple[int, int] | None:
        """Find the bibliography section in the document.

        Returns:
            Tuple of (start_page, end_page) or None if not found.
        """
        start_page: int | None = None

        for page_num in range(1, self.doc.page_count + 1):
            blocks = self.doc.get_text_blocks(page_num)
            for block in blocks:
                text = block.text.strip()
                for pattern in self.SECTION_PATTERNS:
                    if re.match(pattern, text):
                        start_page = page_num
                        break
                if start_page is not None:
                    break
            if start_page is not None:
                break

        if start_page is None:
            return None

        # Bibliography typically continues to the end or until appendices
        end_page = self.doc.page_count

        # Check for appendix after bibliography
        for page_num in range(start_page + 1, self.doc.page_count + 1):
            blocks = self.doc.get_text_blocks(page_num)
            for block in blocks:
                text = block.text.strip().upper()
                if text.startswith("APPENDIX") or text.startswith("APPENDICES"):
                    end_page = page_num - 1
                    break
            if end_page != self.doc.page_count:
                break

        return (start_page, end_page)

    def get_bibliography_entries(
        self, start_page: int | None = None, end_page: int | None = None
    ) -> list[BibliographyEntry]:
        """Extract bibliography entries from the document.

        Args:
            start_page: First page of bibliography (auto-detected if None).
            end_page: Last page of bibliography (auto-detected if None).

        Returns:
            List of BibliographyEntry objects.
        """
        if start_page is None or end_page is None:
            section = self.find_bibliography_section()
            if section is None:
                return []
            start_page, end_page = section

        entries: list[BibliographyEntry] = []
        current_entry_blocks: list[TextBlock] = []
        in_bibliography = False

        for page_num in range(start_page, end_page + 1):
            blocks = self.doc.get_text_blocks(page_num)
            # Sort blocks by vertical position
            sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))

            for block in sorted_blocks:
                text = block.text.strip()
                if not text:
                    continue

                # Skip the section header
                if not in_bibliography:
                    for pattern in self.SECTION_PATTERNS:
                        if re.match(pattern, text):
                            in_bibliography = True
                            break
                    continue

                # Check if this starts a new entry
                is_entry_start = self._is_entry_start(text)

                if is_entry_start and current_entry_blocks:
                    # Save previous entry
                    entry = self._create_entry(current_entry_blocks)
                    if entry is not None:
                        entries.append(entry)
                    current_entry_blocks = []

                current_entry_blocks.append(block)

        # Don't forget the last entry
        if current_entry_blocks:
            entry = self._create_entry(current_entry_blocks)
            if entry is not None:
                entries.append(entry)

        return entries

    def _is_entry_start(self, text: str) -> bool:
        """Check if text looks like the start of a bibliography entry.

        Args:
            text: Text to check.

        Returns:
            True if this appears to start a new entry.
        """
        for pattern in self.ENTRY_START_PATTERNS:
            if re.match(pattern, text):
                return True
        return False

    def _create_entry(self, blocks: list[TextBlock]) -> BibliographyEntry | None:
        """Create a BibliographyEntry from a list of text blocks.

        Args:
            blocks: Text blocks that make up the entry.

        Returns:
            BibliographyEntry or None if invalid.
        """
        if not blocks:
            return None

        # Combine text
        text = " ".join(b.text.strip() for b in blocks)

        # Get first line indent (first block's x position)
        first_line_indent = blocks[0].bbox.x0

        # Get continuation indent (average x position of subsequent blocks)
        if len(blocks) > 1:
            continuation_indents = [b.bbox.x0 for b in blocks[1:]]
            continuation_indent = sum(continuation_indents) / len(continuation_indents)
        else:
            continuation_indent = first_line_indent

        # Get font size (use first block's size)
        font_size = blocks[0].font.size

        return BibliographyEntry(
            text=text,
            page_number=blocks[0].page_number,
            first_line_indent=first_line_indent,
            continuation_indent=continuation_indent,
            font_size=font_size,
            line_count=len(blocks),
        )

    def analyze_bibliography(self) -> BibliographyInfo | None:
        """Analyze the bibliography section.

        Returns:
            BibliographyInfo with analysis results, or None if no bibliography found.
        """
        if self._bib_info_cache is not None:
            return self._bib_info_cache

        section = self.find_bibliography_section()
        if section is None:
            return None

        start_page, end_page = section
        entries = self.get_bibliography_entries(start_page, end_page)

        if not entries:
            return None

        # Calculate average hanging indent
        hanging_indents: list[float] = []
        for entry in entries:
            if entry.line_count > 1:
                # Hanging indent = continuation indent - first line indent
                indent_pts = entry.continuation_indent - entry.first_line_indent
                indent_inches = indent_pts / 72.0
                if indent_inches > 0:  # Only positive (actual hanging indent)
                    hanging_indents.append(indent_inches)

        avg_hanging_indent = sum(hanging_indents) / len(hanging_indents) if hanging_indents else 0.0

        # For spacing analysis, we'd need to look at baseline distances
        # This is a simplified approximation
        avg_entry_spacing = 1.0  # Assume single-spaced within entries
        avg_between_spacing = 2.0  # Assume double-spaced between entries

        info = BibliographyInfo(
            start_page=start_page,
            end_page=end_page,
            entries=entries,
            avg_hanging_indent=avg_hanging_indent,
            avg_entry_spacing=avg_entry_spacing,
            avg_between_spacing=avg_between_spacing,
        )

        self._bib_info_cache = info
        return info

    def check_bibliography_compliance(
        self,
        hanging_indent: float = 0.5,
        indent_tolerance: float = 0.1,
        font_size: float = 12.0,
        size_tolerance: float = 0.5,
    ) -> tuple[bool, list[tuple[int, str]]]:
        """Check if bibliography complies with requirements.

        Args:
            hanging_indent: Required hanging indent in inches.
            indent_tolerance: Allowed indent deviation in inches.
            font_size: Required font size in points.
            size_tolerance: Allowed size deviation in points.

        Returns:
            Tuple of (compliant, list of (page, issue) tuples).
        """
        info = self.analyze_bibliography()
        if info is None:
            return True, []  # No bibliography to check

        issues: list[tuple[int, str]] = []

        # Check hanging indent
        if abs(info.avg_hanging_indent - hanging_indent) > indent_tolerance:
            issues.append(
                (
                    info.start_page,
                    f'Bibliography hanging indent {info.avg_hanging_indent:.2f}" '
                    f'should be {hanging_indent:.2f}"',
                )
            )

        # Check font sizes
        for entry in info.entries:
            if abs(entry.font_size - font_size) > size_tolerance:
                issues.append(
                    (
                        entry.page_number,
                        f"Bibliography entry font size {entry.font_size:.1f}pt "
                        f"should be {font_size:.1f}pt",
                    )
                )
                break  # Only report once

        # Check for missing bibliography
        if not info.entries:
            issues.append((0, "No bibliography entries found"))

        return len(issues) == 0, issues
