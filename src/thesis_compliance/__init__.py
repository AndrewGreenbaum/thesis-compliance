"""
Thesis Compliance - Detect formatting deviations in thesis PDFs.

"Never get your thesis rejected for formatting again."
"""

__version__ = "0.1.0"

from thesis_compliance.checker.engine import ThesisChecker
from thesis_compliance.models import ComplianceReport, Violation

__all__ = ["ThesisChecker", "ComplianceReport", "Violation", "__version__"]
