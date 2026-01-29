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
        if self._doc:
            self._doc.close()

    @property
    def page_count(self) -> int:
        """Get the total number of pages."""
        return len(self._doc)

    def get_page_info(self, page_num: int) -> PageInfo:
        """Get information about a specific page (1-indexed).

        Args:
            page_num: 1-indexed page number.

        Returns:
            PageInfo with dimensions.
        """
        page = self._doc[page_num - 1]  # fitz uses 0-indexing
        rect = page.rect
        return PageInfo.from_points(page_num, rect.width, rect.height)

    def iter_pages(self) -> Iterator[PageInfo]:
        """Iterate over all pages."""
        for i in range(len(self._doc)):
            page = self._doc[i]
            rect = page.rect
            yield PageInfo.from_points(i + 1, rect.width, rect.height)

    def get_text_blocks(self, page_num: int) -> list[TextBlock]:
        """Extract text blocks from a page with position and font info.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of TextBlock objects.
        """
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
