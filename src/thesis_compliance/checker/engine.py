"""Main thesis compliance checking engine."""

from pathlib import Path

from thesis_compliance.extractor import PDFDocument
from thesis_compliance.models import ComplianceReport
from thesis_compliance.spec import SpecLoader, StyleSpec

from .evaluators import RuleEvaluator


def parse_page_range(page_spec: str, max_pages: int) -> list[int]:
    """Parse a page range specification.

    Supports formats like:
    - "1-10" - pages 1 through 10
    - "1,5,10" - specific pages
    - "1-10,20,30-35" - mixed ranges and singles

    Args:
        page_spec: Page specification string.
        max_pages: Maximum valid page number.

    Returns:
        List of page numbers (1-indexed).

    Raises:
        ValueError: If page spec is invalid.
    """
    pages: set[int] = set()

    for part in page_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start_num = int(start.strip())
            end_num = int(end.strip())
            if start_num > end_num:
                raise ValueError(f"Invalid page range: {start_num}-{end_num} (start > end)")
            if start_num < 1 or end_num > max_pages:
                raise ValueError(f"Page range {start_num}-{end_num} out of bounds (1-{max_pages})")
            pages.update(range(start_num, end_num + 1))
        else:
            page_num = int(part)
            if page_num < 1 or page_num > max_pages:
                raise ValueError(f"Page {page_num} out of bounds (1-{max_pages})")
            pages.add(page_num)

    return sorted(pages)


class ThesisChecker:
    """Main engine for checking thesis compliance.

    Usage:
        checker = ThesisChecker("my-thesis.pdf")
        report = checker.check()
        print(report.passed)
    """

    def __init__(
        self,
        pdf_path: str | Path,
        spec: str | StyleSpec | None = None,
    ):
        """Initialize the thesis checker.

        Args:
            pdf_path: Path to the PDF file to check.
            spec: Style specification - can be:
                  - None: Use default (Rackham)
                  - str: Name of built-in spec or path to YAML file
                  - StyleSpec: Pre-loaded specification

        Raises:
            FileNotFoundError: If PDF or spec file doesn't exist.
            ValueError: If PDF or spec is invalid.
        """
        self.pdf_path = Path(pdf_path)

        # Load the PDF
        self.doc = PDFDocument(self.pdf_path)

        # Load the spec
        if spec is None:
            self.spec = SpecLoader.get_default_spec()
        elif isinstance(spec, str):
            self.spec = SpecLoader.load(spec)
        else:
            self.spec = spec

        # Initialize evaluator
        self.evaluator = RuleEvaluator(self.doc, self.spec)

    def __enter__(self) -> "ThesisChecker":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the PDF document."""
        self.doc.close()

    def _normalize_pages(self, pages: str | list[int] | None) -> list[int] | None:
        """Normalize page specification to a list of page numbers.

        Args:
            pages: Pages to normalize - can be:
                   - None: Returns None (check all pages)
                   - str: Page range like "1-10,20,30-35"
                   - list[int]: Explicit list of page numbers

        Returns:
            List of page numbers or None for all pages.
        """
        if pages is None:
            return None
        if isinstance(pages, str):
            return parse_page_range(pages, self.doc.page_count)
        return pages

    def check(
        self,
        pages: str | list[int] | None = None,
    ) -> ComplianceReport:
        """Run compliance check on the PDF.

        Args:
            pages: Pages to check - can be:
                   - None: Check all pages
                   - str: Page range like "1-10,20,30-35"
                   - list[int]: Explicit list of page numbers

        Returns:
            ComplianceReport with all violations found.
        """
        # Parse pages
        page_list = self._normalize_pages(pages)

        # Pre-load pages to warm cache for all extractors
        self.doc.preload_pages(page_list)

        # Run all evaluations
        violations = self.evaluator.evaluate_all(page_list)

        # Sort violations by page, then by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        violations.sort(
            key=lambda v: (
                v.page or 0,
                severity_order.get(v.severity.value, 3),
            )
        )

        return ComplianceReport(
            pdf_path=self.pdf_path,
            spec_name=self.spec.name,
            pages_checked=len(page_list) if page_list else self.doc.page_count,
            rules_checked=self.spec.rule_count,
            violations=violations,
        )

    def check_margins_only(
        self,
        pages: str | list[int] | None = None,
    ) -> ComplianceReport:
        """Check only margin compliance.

        Args:
            pages: Pages to check.

        Returns:
            ComplianceReport with margin violations only.
        """
        page_list = self._normalize_pages(pages)
        self.doc.preload_pages(page_list)

        violations = self.evaluator.evaluate_title_page()
        violations.extend(self.evaluator.evaluate_margins(page_list))

        return ComplianceReport(
            pdf_path=self.pdf_path,
            spec_name=self.spec.name,
            pages_checked=len(page_list) if page_list else self.doc.page_count,
            rules_checked=5,  # 4 margins + title page
            violations=violations,
        )

    def check_fonts_only(
        self,
        pages: str | list[int] | None = None,
    ) -> ComplianceReport:
        """Check only font compliance.

        Args:
            pages: Pages to check.

        Returns:
            ComplianceReport with font violations only.
        """
        page_list = self._normalize_pages(pages)
        self.doc.preload_pages(page_list)

        violations = self.evaluator.evaluate_fonts(page_list)

        return ComplianceReport(
            pdf_path=self.pdf_path,
            spec_name=self.spec.name,
            pages_checked=len(page_list) if page_list else self.doc.page_count,
            rules_checked=2,  # font family, size
            violations=violations,
        )

    def check_spacing_only(
        self,
        pages: str | list[int] | None = None,
    ) -> ComplianceReport:
        """Check only line spacing compliance.

        Args:
            pages: Pages to check.

        Returns:
            ComplianceReport with spacing violations only.
        """
        page_list = self._normalize_pages(pages)
        self.doc.preload_pages(page_list)

        violations = self.evaluator.evaluate_spacing(page_list)

        return ComplianceReport(
            pdf_path=self.pdf_path,
            spec_name=self.spec.name,
            pages_checked=len(page_list) if page_list else self.doc.page_count,
            rules_checked=1,
            violations=violations,
        )

    @property
    def page_count(self) -> int:
        """Get the number of pages in the PDF."""
        return self.doc.page_count
