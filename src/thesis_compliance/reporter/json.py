"""JSON output for CI-friendly compliance reports."""

import json
import sys
from pathlib import Path
from typing import IO

from thesis_compliance.models import ComplianceReport


class JSONReporter:
    """Generate JSON output for compliance reports."""

    def __init__(self, pretty: bool = False):
        """Initialize the reporter.

        Args:
            pretty: Whether to format JSON with indentation.
        """
        self.pretty = pretty

    def to_json(self, report: ComplianceReport) -> str:
        """Convert report to JSON string.

        Args:
            report: ComplianceReport to convert.

        Returns:
            JSON string.
        """
        data = report.to_dict()

        if self.pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

    def print_report(
        self,
        report: ComplianceReport,
        file: IO[str] | None = None,
    ) -> None:
        """Print report as JSON.

        Args:
            report: ComplianceReport to print.
            file: Output file (defaults to stdout).
        """
        output = file or sys.stdout
        print(self.to_json(report), file=output)

    def write_report(
        self,
        report: ComplianceReport,
        path: Path | str,
    ) -> None:
        """Write report to a JSON file.

        Args:
            report: ComplianceReport to write.
            path: Output file path.
        """
        path = Path(path)
        path.write_text(self.to_json(report))
