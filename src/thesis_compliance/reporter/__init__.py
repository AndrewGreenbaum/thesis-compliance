"""Report generation for compliance results."""

from thesis_compliance.reporter.console import ConsoleReporter
from thesis_compliance.reporter.json import JSONReporter

__all__ = ["ConsoleReporter", "JSONReporter"]
