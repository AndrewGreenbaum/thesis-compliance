"""PyMuPDF wrapper for PDF document access."""

from pathlib import Path
from typing import Iterator

import fitz  # PyMuPDF

from thesis_compliance.models import BoundingBox, FontInfo, PageInfo, TextBlock


class PDFDocument:
    """Wrapper around PyMuPDF for thesis PDF analysis."""

    def __init__(self, path: Path | str):
        """Open a PDF document.

        Args:
            path: Path to the PDF file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file is not a valid PDF.
        """
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"PDF not found: {self.path}")

        try:
            self._doc = fitz.open(self.path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}") from e

        # Cache for text blocks to avoid repeated extraction
        self._text_blocks_cache: dict[int, list[TextBlock]] = {}
        # Cache for page info
        self._page_info_cache: dict[int, PageInfo] = {}

    def __enter__(self) -> "PDFDocument":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __del__(self) -> None:
        """Ensure PDF document is closed on garbage collection."""
        if hasattr(self, "_doc") and self._doc is not None:
            try:
                # Check if document is still open before closing
                if not self._doc.is_closed:
                    self._doc.close()
            except Exception:
                pass

    def close(self) -> None:
        """Close the PDF document."""
        self.clear_cache()
        if self._doc:
            self._doc.close()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._text_blocks_cache.clear()
        self._page_info_cache.clear()

    def preload_pages(self, pages: list[int] | None = None) -> None:
        """Pre-load and cache text blocks for specified pages.

        This can improve performance when multiple extractors will
        process the same pages.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.
        """
        if pages is None:
            pages = list(range(1, self.page_count + 1))

        for page_num in pages:
            # This will cache the results
            self.get_text_blocks(page_num)
            self.get_page_info(page_num)

    @property
    def page_count(self) -> int:
        """Get the total number of pages."""
        return len(self._doc)

    def get_page_info(self, page_num: int) -> PageInfo:
        """Get information about a specific page (1-indexed).

        Results are cached for performance.

        Args:
            page_num: 1-indexed page number.

        Returns:
            PageInfo with dimensions.
        """
        # Check cache first
        if page_num in self._page_info_cache:
            return self._page_info_cache[page_num]

        page = self._doc[page_num - 1]  # fitz uses 0-indexing
        rect = page.rect
        info = PageInfo.from_points(page_num, rect.width, rect.height)

        # Cache and return
        self._page_info_cache[page_num] = info
        return info

    def iter_pages(self) -> Iterator[PageInfo]:
        """Iterate over all pages."""
        for i in range(len(self._doc)):
            page = self._doc[i]
            rect = page.rect
            yield PageInfo.from_points(i + 1, rect.width, rect.height)

    def get_text_blocks(self, page_num: int) -> list[TextBlock]:
        """Extract text blocks from a page with position and font info.

        Results are cached for performance - subsequent calls for the same
        page return cached data.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of TextBlock objects.
        """
        # Check cache first
        if page_num in self._text_blocks_cache:
            return self._text_blocks_cache[page_num]

        page = self._doc[page_num - 1]
        blocks: list[TextBlock] = []

        # Get detailed text with font information
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Skip non-text blocks (images, etc.)
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    bbox_coords = span.get("bbox", (0, 0, 0, 0))
                    font_name = span.get("font", "Unknown")
                    font_size = span.get("size", 12.0)
                    font_flags = span.get("flags", 0)
                    color_int = span.get("color", 0)

                    # Parse font flags
                    is_bold = bool(font_flags & 2**4)  # bit 4 = bold
                    is_italic = bool(font_flags & 2**1)  # bit 1 = italic

                    # Convert color integer to hex
                    color = f"#{color_int:06x}"

                    # Calculate baseline (origin y is baseline in PyMuPDF)
                    origin = span.get("origin") or (0, bbox_coords[3])
                    baseline = origin[1] if len(origin) > 1 else bbox_coords[3]

                    blocks.append(
                        TextBlock(
                            text=text,
                            bbox=BoundingBox(
                                x0=bbox_coords[0],
                                y0=bbox_coords[1],
                                x1=bbox_coords[2],
                                y1=bbox_coords[3],
                            ),
                            font=FontInfo(
                                name=font_name,
                                size=font_size,
                                is_bold=is_bold,
                                is_italic=is_italic,
                                color=color,
                            ),
                            page_number=page_num,
                            baseline=baseline,
                        )
                    )

        # Cache and return
        self._text_blocks_cache[page_num] = blocks
        return blocks

    def get_content_bbox(self, page_num: int) -> BoundingBox | None:
        """Get the bounding box of all content on a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            BoundingBox containing all content, or None if page is empty.
        """
        blocks = self.get_text_blocks(page_num)
        if not blocks:
            return None

        x0 = min(b.bbox.x0 for b in blocks)
        y0 = min(b.bbox.y0 for b in blocks)
        x1 = max(b.bbox.x1 for b in blocks)
        y1 = max(b.bbox.y1 for b in blocks)

        return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)

    def get_all_fonts(self) -> dict[str, set[float]]:
        """Get all fonts used in the document with their sizes.

        Returns:
            Dictionary mapping font names to sets of sizes used.
        """
        fonts: dict[str, set[float]] = {}

        for page_num in range(1, self.page_count + 1):
            for block in self.get_text_blocks(page_num):
                font_name = block.font.base_name
                if font_name not in fonts:
                    fonts[font_name] = set()
                fonts[font_name].add(round(block.font.size, 1))

        return fonts

    def get_page_text(self, page_num: int) -> str:
        """Get plain text content of a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            Plain text content.
        """
        page = self._doc[page_num - 1]
        return page.get_text()
