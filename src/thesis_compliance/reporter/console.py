"""Rich console output for compliance reports."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from thesis_compliance.models import ComplianceReport, Severity, Violation


class ConsoleReporter:
    """Generate rich console output for compliance reports."""

    def __init__(self, console: Console | None = None):
        """Initialize the reporter.

        Args:
            console: Rich Console instance (creates new one if None).
        """
        self.console = console or Console()

    def print_report(self, report: ComplianceReport) -> None:
        """Print a full compliance report.

        Args:
            report: ComplianceReport to display.
        """
        # Header
        self._print_header(report)

        # Violations
        if report.violations:
            self._print_violations(report)
        else:
            self._print_success()

        # Summary
        self._print_summary(report)

    def _print_header(self, report: ComplianceReport) -> None:
        """Print report header."""
        title = Text("Thesis Compliance Report", style="bold blue")
        self.console.print()
        self.console.print(Panel(title, expand=False))
        self.console.print()

        # Document info
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Label", style="dim")
        info_table.add_column("Value")

        info_table.add_row("Document:", str(report.pdf_path.name))
        info_table.add_row("Spec:", report.spec_name)
        info_table.add_row("Pages checked:", str(report.pages_checked))
        info_table.add_row("Rules checked:", str(report.rules_checked))

        self.console.print(info_table)
        self.console.print()

    def _print_violations(self, report: ComplianceReport) -> None:
        """Print violation details."""
        errors = report.errors
        warnings = report.warnings

        if errors:
            self.console.print(Text(f"Errors: {len(errors)}", style="bold red"))
            self.console.print()

            for violation in errors:
                self._print_violation(violation)

        if warnings:
            self.console.print(Text(f"Warnings: {len(warnings)}", style="bold yellow"))
            self.console.print()

            for violation in warnings:
                self._print_violation(violation)

    def _print_violation(self, violation: Violation) -> None:
        """Print a single violation."""
        # Location
        if violation.page is not None:
            location = f"Page {violation.page}"
        else:
            location = "Document-wide"

        # Icon based on severity
        if violation.severity == Severity.ERROR:
            icon = "✗"
            style = "red"
        elif violation.severity == Severity.WARNING:
            icon = "!"
            style = "yellow"
        else:
            icon = "i"
            style = "blue"

        # Main message
        self.console.print(f"  [{style}]{icon}[/{style}] {location}: {violation.message}")

        # Expected vs found
        if violation.expected is not None:
            self.console.print(f"    [dim]Expected:[/dim] {violation.expected}")
        if violation.found is not None:
            self.console.print(f"    [dim]Found:[/dim] {violation.found}")

        # Suggestion
        if violation.suggestion:
            self.console.print(
                f"    [dim]Suggestion:[/dim] [italic]{violation.suggestion}[/italic]"
            )

        self.console.print()

    def _print_success(self) -> None:
        """Print success message when no violations."""
        self.console.print(
            Panel(
                Text("✓ All checks passed!", style="bold green"),
                expand=False,
                border_style="green",
            )
        )
        self.console.print()

    def _print_summary(self, report: ComplianceReport) -> None:
        """Print summary section."""
        if report.passed:
            if report.warnings:
                status = Text(f"Passed with {len(report.warnings)} warning(s)", style="yellow")
            else:
                status = Text("Passed", style="bold green")
        else:
            status = Text(f"Failed - {len(report.errors)} error(s)", style="bold red")

        self.console.print("─" * 50)
        self.console.print(f"Status: {status}")
        self.console.print()

    def print_brief(self, report: ComplianceReport) -> None:
        """Print a brief one-line summary.

        Args:
            report: ComplianceReport to summarize.
        """
        if report.passed:
            if report.warnings:
                self.console.print(
                    f"[yellow]⚠[/yellow] {report.pdf_path.name}: "
                    f"Passed with {len(report.warnings)} warning(s)"
                )
            else:
                self.console.print(f"[green]✓[/green] {report.pdf_path.name}: Passed")
        else:
            self.console.print(
                f"[red]✗[/red] {report.pdf_path.name}: Failed ({len(report.errors)} error(s))"
            )
