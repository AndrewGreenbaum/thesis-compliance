"""PDF content extraction utilities."""

from thesis_compliance.extractor.fonts import FontExtractor
from thesis_compliance.extractor.margins import MarginExtractor
from thesis_compliance.extractor.pages import PageNumberExtractor
from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.extractor.spacing import SpacingExtractor

__all__ = [
    "PDFDocument",
    "MarginExtractor",
    "FontExtractor",
    "SpacingExtractor",
    "PageNumberExtractor",
]
