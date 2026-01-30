"""Line spacing analysis for PDF documents."""

from dataclasses import dataclass
from statistics import mean, median

from thesis_compliance.extractor.pdf import PDFDocument
from thesis_compliance.models import LineSpacing, TextBlock


@dataclass
class SpacingAnalysis:
    """Results of spacing analysis for a page or region."""

    average_ratio: float
    median_ratio: float
    min_ratio: float
    max_ratio: float
    sample_count: int
    is_consistent: bool  # True if spacing is consistent throughout


class SpacingExtractor:
    """Extract and analyze line spacing from PDF documents.

    Line spacing ratio is calculated as:
        ratio = baseline_distance / font_size

    Where:
        - 1.0 = single spacing
        - 1.5 = 1.5 line spacing
        - 2.0 = double spacing
    """

    # Tolerance for considering spacing "consistent"
    CONSISTENCY_TOLERANCE = 0.15

    def __init__(self, doc: PDFDocument):
        """Initialize with a PDF document.

        Args:
            doc: Open PDFDocument instance.
        """
        self.doc = doc

    def _group_lines(self, blocks: list[TextBlock]) -> list[list[TextBlock]]:
        """Group text blocks into logical lines based on baseline position.

        Args:
            blocks: List of TextBlock objects.

        Returns:
            List of line groups, each containing blocks on the same line.
        """
        if not blocks:
            return []

        # Sort by baseline (y position)
        sorted_blocks = sorted(blocks, key=lambda b: b.baseline)

        lines: list[list[TextBlock]] = []
        current_line: list[TextBlock] = [sorted_blocks[0]]
        current_baseline = sorted_blocks[0].baseline

        for block in sorted_blocks[1:]:
            # If baseline is close enough, same line
            if abs(block.baseline - current_baseline) < 3.0:  # 3pt tolerance
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
                current_baseline = block.baseline

        if current_line:
            lines.append(current_line)

        return lines

    def get_line_spacings(self, page_num: int) -> list[LineSpacing]:
        """Extract line spacing measurements from a page.

        Args:
            page_num: 1-indexed page number.

        Returns:
            List of LineSpacing measurements between consecutive lines.
        """
        blocks = self.doc.get_text_blocks(page_num)
        lines = self._group_lines(blocks)

        if len(lines) < 2:
            return []

        spacings: list[LineSpacing] = []

        for i in range(len(lines) - 1):
            current_line = lines[i]
            next_line = lines[i + 1]

            # Get baselines
            current_baseline = mean(b.baseline for b in current_line)
            next_baseline = mean(b.baseline for b in next_line)

            # Get font sizes (use average of line)
            current_sizes = [b.font.size for b in current_line]
            if not current_sizes:
                continue
            font_size = mean(current_sizes)

            # Calculate baseline distance
            baseline_distance = abs(next_baseline - current_baseline)

            # Skip if this looks like a paragraph break (very large gap)
            if baseline_distance > font_size * 3.0:
                continue

            # Calculate ratio
            ratio = baseline_distance / font_size if font_size > 0 else 0

            spacings.append(
                LineSpacing(
                    ratio=ratio,
                    baseline_distance=baseline_distance,
                    font_size=font_size,
                    page_number=page_num,
                    start_line=i + 1,
                    end_line=i + 2,
                )
            )

        return spacings

    def analyze_spacing(self, pages: list[int] | None = None) -> SpacingAnalysis | None:
        """Analyze line spacing across pages.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            SpacingAnalysis with statistics, or None if insufficient data.
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        all_ratios: list[float] = []

        for page_num in pages:
            spacings = self.get_line_spacings(page_num)
            all_ratios.extend(s.ratio for s in spacings)

        if len(all_ratios) < 3:  # Need at least 3 samples
            return None

        avg_ratio = mean(all_ratios)
        med_ratio = median(all_ratios)
        min_ratio = min(all_ratios)
        max_ratio = max(all_ratios)

        # Check consistency
        is_consistent = (max_ratio - min_ratio) <= self.CONSISTENCY_TOLERANCE

        return SpacingAnalysis(
            average_ratio=avg_ratio,
            median_ratio=med_ratio,
            min_ratio=min_ratio,
            max_ratio=max_ratio,
            sample_count=len(all_ratios),
            is_consistent=is_consistent,
        )

    def check_double_spacing(
        self,
        pages: list[int] | None = None,
        tolerance: float = 0.2,
    ) -> tuple[bool, list[tuple[int, float]]]:
        """Check if document uses double spacing.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.
            tolerance: Allowed deviation from 2.0 ratio.

        Returns:
            Tuple of (compliant, list of (page, ratio) violations).
        """
        if pages is None:
            pages = list(range(1, self.doc.page_count + 1))

        violations: list[tuple[int, float]] = []

        for page_num in pages:
            spacings = self.get_line_spacings(page_num)
            if not spacings:
                continue

            # Get median ratio for page (more robust than average)
            ratios = [s.ratio for s in spacings]
            page_ratio = median(ratios)

            # Check if it's close to double spacing
            if abs(page_ratio - 2.0) > tolerance:
                violations.append((page_num, page_ratio))

        return len(violations) == 0, violations

    def detect_spacing_type(self, pages: list[int] | None = None) -> str:
        """Detect the predominant spacing type.

        Args:
            pages: List of 1-indexed page numbers, or None for all pages.

        Returns:
            One of: "single", "1.5", "double", "mixed", or "unknown"
        """
        analysis = self.analyze_spacing(pages)
        if analysis is None:
            return "unknown"

        ratio = analysis.median_ratio

        if 0.9 <= ratio <= 1.2:
            return "single"
        elif 1.4 <= ratio <= 1.7:
            return "1.5"
        elif 1.8 <= ratio <= 2.3:
            return "double"
        elif analysis.is_consistent:
            return f"custom ({ratio:.1f})"
        else:
            return "mixed"
