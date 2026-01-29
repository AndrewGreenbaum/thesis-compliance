"""Generate test PDF fixtures for thesis compliance testing.

This script creates various PDF files with specific formatting
characteristics for testing the compliance checker.
"""

from pathlib import Path

import fitz  # PyMuPDF


# Output directory for test PDFs
FIXTURES_DIR = Path(__file__).parent


def create_valid_thesis() -> Path:
    """Create a properly formatted thesis PDF.

    Characteristics:
    - 1.5" left margin, 1" other margins
    - 2" top margin on title page
    - 12pt Times New Roman
    - Double spacing
    - Page numbers at bottom center

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    # Page dimensions (US Letter)
    page_width = 612  # 8.5"
    page_height = 792  # 11"

    # Margins in points
    left_margin = 108  # 1.5"
    right_margin = 72  # 1"
    top_margin = 72  # 1" (2" for title page)
    bottom_margin = 72  # 1"
    title_top_margin = 144  # 2"

    # Font settings
    font_name = "Times-Roman"
    font_size = 12

    # Line spacing (double = font_size * 2)
    line_height = font_size * 2

    # Page 1: Title page (2" top margin, no page number)
    page = doc.new_page(width=page_width, height=page_height)
    page.insert_text(
        (left_margin, title_top_margin + font_size),
        "A THESIS ON COMPLIANCE CHECKING",
        fontname=font_name,
        fontsize=14,
    )
    page.insert_text(
        (left_margin, title_top_margin + 50),
        "by",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 70),
        "Test Author",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 120),
        "A thesis submitted in partial fulfillment",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 140),
        "of the requirements for the degree of",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 160),
        "Doctor of Philosophy",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 220),
        "Test University",
        fontname=font_name,
        fontsize=font_size,
    )
    page.insert_text(
        (left_margin, title_top_margin + 240),
        "2024",
        fontname=font_name,
        fontsize=font_size,
    )

    # Pages 2-5: Body text with proper formatting
    for page_num in range(2, 6):
        page = doc.new_page(width=page_width, height=page_height)

        # Body text with double spacing
        y_pos = top_margin + font_size
        text_lines = [
            f"This is page {page_num} of the thesis document.",
            "The text is formatted with proper margins and double spacing.",
            "The left margin is 1.5 inches as required by the style guide.",
            "Right, top, and bottom margins are all 1 inch.",
            "This line tests the double spacing between lines.",
            "Each line should have proper font size of 12 points.",
            "The font used is Times New Roman as specified.",
            "Page numbers should appear at the bottom center.",
        ]

        for line in text_lines:
            if y_pos < page_height - bottom_margin:
                page.insert_text(
                    (left_margin, y_pos),
                    line,
                    fontname=font_name,
                    fontsize=font_size,
                )
                y_pos += line_height

        # Page number at bottom center
        page_number_text = str(page_num)
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=font_size)
        page.insert_text(
            ((page_width - text_width) / 2, page_height - 36),
            page_number_text,
            fontname=font_name,
            fontsize=font_size,
        )

    output_path = FIXTURES_DIR / "valid_thesis.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_bad_margins() -> Path:
    """Create PDF with 0.5" margins (too small).

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    page_width = 612
    page_height = 792
    small_margin = 36  # 0.5"

    font_name = "Times-Roman"
    font_size = 12
    line_height = font_size * 2

    for page_num in range(1, 4):
        page = doc.new_page(width=page_width, height=page_height)

        y_pos = small_margin + font_size
        text_lines = [
            "This text has margins that are too small.",
            "The margins are only 0.5 inches on all sides.",
            "This should trigger margin violation errors.",
            f"Current page: {page_num}",
        ]

        for line in text_lines:
            if y_pos < page_height - small_margin:
                page.insert_text(
                    (small_margin, y_pos),
                    line,
                    fontname=font_name,
                    fontsize=font_size,
                )
                y_pos += line_height

    output_path = FIXTURES_DIR / "bad_margins.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_wrong_font() -> Path:
    """Create PDF with wrong font (Helvetica) and size (10pt).

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    page_width = 612
    page_height = 792
    left_margin = 108
    top_margin = 72

    # Wrong font and size
    font_name = "Helvetica"
    font_size = 10
    line_height = font_size * 2

    for page_num in range(1, 4):
        page = doc.new_page(width=page_width, height=page_height)

        y_pos = top_margin + font_size
        text_lines = [
            "This text uses the wrong font and size.",
            "The font is Helvetica instead of Times.",
            "The font size is 10pt instead of 12pt.",
            "This should trigger font-related violations.",
            f"Page {page_num} of the test document.",
        ]

        for line in text_lines:
            if y_pos < page_height - 72:
                page.insert_text(
                    (left_margin, y_pos),
                    line,
                    fontname=font_name,
                    fontsize=font_size,
                )
                y_pos += line_height

    output_path = FIXTURES_DIR / "wrong_font.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_single_spaced() -> Path:
    """Create PDF with single line spacing.

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    page_width = 612
    page_height = 792
    left_margin = 108
    top_margin = 72

    font_name = "Times-Roman"
    font_size = 12
    # Single spacing
    line_height = font_size * 1.0

    for page_num in range(1, 4):
        page = doc.new_page(width=page_width, height=page_height)

        y_pos = top_margin + font_size
        text_lines = [
            "This text is single spaced.",
            "The line spacing ratio is approximately 1.0.",
            "Double spacing requires a ratio of 2.0.",
            "This should trigger spacing violations.",
            "The checker expects double-spaced body text.",
            "Single spacing is not acceptable for theses.",
            f"This is page {page_num}.",
        ]

        for line in text_lines:
            if y_pos < page_height - 72:
                page.insert_text(
                    (left_margin, y_pos),
                    line,
                    fontname=font_name,
                    fontsize=font_size,
                )
                y_pos += line_height

    output_path = FIXTURES_DIR / "single_spaced.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_no_page_numbers() -> Path:
    """Create PDF without page numbers.

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    page_width = 612
    page_height = 792
    left_margin = 108
    top_margin = 72

    font_name = "Times-Roman"
    font_size = 12
    line_height = font_size * 2

    for page_num in range(1, 4):
        page = doc.new_page(width=page_width, height=page_height)

        y_pos = top_margin + font_size
        text_lines = [
            "This page has no page number.",
            "Page numbers are required for thesis documents.",
            "This should trigger page number violations.",
            "The missing page numbers need to be detected.",
        ]

        for line in text_lines:
            if y_pos < page_height - 72:
                page.insert_text(
                    (left_margin, y_pos),
                    line,
                    fontname=font_name,
                    fontsize=font_size,
                )
                y_pos += line_height

        # No page number inserted

    output_path = FIXTURES_DIR / "no_page_nums.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_minimal_pdf() -> Path:
    """Create a minimal single-page PDF for basic testing.

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 144), "Minimal test PDF", fontname="Times-Roman", fontsize=12)

    output_path = FIXTURES_DIR / "minimal.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def create_empty_pdf() -> Path:
    """Create a PDF with blank pages (no text content).

    Returns:
        Path to the created PDF.
    """
    doc = fitz.open()

    # Create 3 blank pages
    for _ in range(3):
        doc.new_page(width=612, height=792)

    output_path = FIXTURES_DIR / "empty.pdf"
    doc.save(output_path)
    doc.close()
    return output_path


def generate_all() -> list[Path]:
    """Generate all test PDF fixtures.

    Returns:
        List of paths to created PDFs.
    """
    generators = [
        create_valid_thesis,
        create_bad_margins,
        create_wrong_font,
        create_single_spaced,
        create_no_page_numbers,
        create_minimal_pdf,
        create_empty_pdf,
    ]

    paths = []
    for generator in generators:
        path = generator()
        print(f"Created: {path}")
        paths.append(path)

    return paths


if __name__ == "__main__":
    print("Generating test PDF fixtures...")
    generate_all()
    print("Done!")
