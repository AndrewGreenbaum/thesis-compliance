"""Thesis compliance CLI using Typer."""

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from thesis_compliance import __version__
from thesis_compliance.checker.engine import ThesisChecker
from thesis_compliance.reporter.console import ConsoleReporter
from thesis_compliance.reporter.json import JSONReporter
from thesis_compliance.spec import SpecLoader

app = typer.Typer(
    name="thesis-check",
    help="Check thesis PDF formatting compliance against university style requirements.",
    add_completion=False,
)

console = Console()


class OutputFormat(str, Enum):
    """Output format options."""

    CONSOLE = "console"
    JSON = "json"
    BRIEF = "brief"


# Exit codes
EXIT_SUCCESS = 0
EXIT_ERRORS = 1
EXIT_WARNINGS = 2  # Only in strict mode
EXIT_TOOL_ERROR = 3


@app.command()
def check(
    pdf_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the thesis PDF file to check",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    spec: Annotated[
        str | None,
        typer.Option(
            "--spec",
            "-s",
            help="Style specification (built-in name or path to YAML file)",
        ),
    ] = None,
    pages: Annotated[
        str | None,
        typer.Option(
            "--pages",
            "-p",
            help="Page range to check (e.g., '1-10', '1,5,10', '1-10,20')",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
        ),
    ] = OutputFormat.CONSOLE,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Strict mode: exit with error code on warnings too",
        ),
    ] = False,
    json_pretty: Annotated[
        bool,
        typer.Option(
            "--pretty",
            help="Pretty-print JSON output",
        ),
    ] = False,
) -> None:
    """Check a thesis PDF for formatting compliance.

    Analyzes the rendered PDF output to detect:
    - Margin violations (1.5" left for binding, 1" others)
    - Font issues (12pt Times New Roman or similar)
    - Line spacing problems (double-spacing required)
    - Page number format and position

    Examples:
        thesis-check my-thesis.pdf
        thesis-check my-thesis.pdf --spec stanford.yaml
        thesis-check my-thesis.pdf --format json --strict
        thesis-check my-thesis.pdf --pages 1-10,42
    """
    try:
        with ThesisChecker(pdf_path, spec) as checker:
            report = checker.check(pages)

        # Output report
        if output_format == OutputFormat.JSON:
            json_reporter = JSONReporter(pretty=json_pretty)
            json_reporter.print_report(report)
        elif output_format == OutputFormat.BRIEF:
            console_reporter = ConsoleReporter(console)
            console_reporter.print_brief(report)
        else:
            console_reporter = ConsoleReporter(console)
            console_reporter.print_report(report)

        # Determine exit code
        if not report.passed:
            raise typer.Exit(EXIT_ERRORS)
        elif strict and report.warnings:
            raise typer.Exit(EXIT_WARNINGS)
        else:
            raise typer.Exit(EXIT_SUCCESS)

    except typer.Exit:
        raise  # Re-raise typer.Exit without catching
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_TOOL_ERROR)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_TOOL_ERROR)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(EXIT_TOOL_ERROR)


@app.command()
def list_specs() -> None:
    """List available built-in style specifications."""
    specs = SpecLoader.list_builtin_specs()

    if not specs:
        console.print("[yellow]No built-in specs found[/yellow]")
        return

    console.print("[bold]Available specifications:[/bold]")
    console.print()

    for spec_name in sorted(specs):
        try:
            spec = SpecLoader.load(spec_name)
            console.print(f"  [green]{spec_name}[/green]")
            console.print(f"    {spec.university}")
            if spec.description:
                console.print(f"    [dim]{spec.description}[/dim]")
            console.print()
        except Exception:
            console.print(f"  [yellow]{spec_name}[/yellow] (failed to load)")


@app.command()
def info(
    pdf_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the thesis PDF file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
) -> None:
    """Show information about a thesis PDF without checking compliance."""
    try:
        from thesis_compliance.extractor import (
            FontExtractor,
            PDFDocument,
            SpacingExtractor,
        )

        with PDFDocument(pdf_path) as doc:
            console.print(f"[bold]File:[/bold] {pdf_path.name}")
            console.print(f"[bold]Pages:[/bold] {doc.page_count}")
            console.print()

            # Page dimensions
            page_info = doc.get_page_info(1)
            console.print(
                f"[bold]Page size:[/bold] "
                f'{page_info.width_inches:.2f}" × {page_info.height_inches:.2f}"'
            )
            console.print()

            # Fonts
            font_extractor = FontExtractor(doc)
            fonts = font_extractor.get_font_usage()
            console.print("[bold]Fonts used:[/bold]")
            for font_name, usage in sorted(fonts.items(), key=lambda x: -x[1].occurrence_count):
                sizes = ", ".join(f"{s}pt" for s in sorted(usage.sizes))
                marker = " [green](body)[/green]" if usage.is_body_font else ""
                console.print(f"  {font_name}: {sizes}{marker}")
            console.print()

            # Spacing
            spacing_extractor = SpacingExtractor(doc)
            spacing_type = spacing_extractor.detect_spacing_type()
            console.print(f"[bold]Line spacing:[/bold] {spacing_type}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_TOOL_ERROR)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"thesis-check version {__version__}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
