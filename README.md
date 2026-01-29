# Thesis Compliance

> "Never get your thesis rejected for formatting again."

A tool that detects formatting deviations in thesis PDFs by analyzing the actual rendered output, not just linting LaTeX source. Show grad students *exactly* where their document breaks from the style spec.

## Features

- **Margin checking** - Verify 1.5" left (binding) and 1" other margins
- **Font validation** - Check for 12pt Times/Arial body text
- **Line spacing** - Detect double-spacing violations
- **Page numbers** - Validate Roman numerals for front matter, Arabic for body
- **Title page** - Verify 2" top margin requirement
- **Multiple university specs** - Rackham (UMich), UNC, Rice, and more

## Installation

```bash
pip install thesis-compliance
```

Or install from source:

```bash
git clone https://github.com/thesis-compliance/thesis-compliance
cd thesis-compliance
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Basic check with default (Rackham) spec
thesis-check my-thesis.pdf

# Use a different university's requirements
thesis-check my-thesis.pdf --spec unc

# Check specific pages
thesis-check my-thesis.pdf --pages 1-10,42

# JSON output for CI
thesis-check my-thesis.pdf --format json --strict

# Get document info without checking
thesis-check info my-thesis.pdf

# List available specs
thesis-check list-specs
```

### Python API

```python
from thesis_compliance import ThesisChecker

# Check a thesis
with ThesisChecker("my-thesis.pdf") as checker:
    report = checker.check()

    if report.passed:
        print("All checks passed!")
    else:
        for violation in report.errors:
            print(f"Page {violation.page}: {violation.message}")
```

### REST API

Start the server:

```bash
pip install thesis-compliance[api]
uvicorn thesis_compliance.api:app --host 0.0.0.0 --port 8000
```

Check a thesis:

```bash
curl -X POST "http://localhost:8000/check" \
  -F "file=@my-thesis.pdf" \
  -F "spec=rackham"
```

## Example Output

```
Thesis Compliance Report

Document:     my-thesis.pdf
Spec:         rackham
Pages checked: 142
Rules checked: 23

Errors: 2

  ✗ Page 1: Title page top margin must be at least 2.0 inches
    Expected: >= 2.0 inches
    Found: 1.75 inches
    Suggestion: Add 18pt of space before the title

  ✗ Page 42: Body text must be double-spaced
    Expected: 2.0 line spacing
    Found: 1.80 (1.5 lines)
    Suggestion: Check paragraph settings use "double" not "1.5 lines"

Warnings: 0

──────────────────────────────────────────────────
Status: Failed - 2 error(s)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | Errors found |
| 2 | Warnings found (strict mode) |
| 3 | Tool error (invalid PDF, etc.) |

## Available Specs

| Spec | University | Notes |
|------|-----------|-------|
| `rackham` | University of Michigan | Default, strictest |
| `unc` | UNC Chapel Hill | |
| `rice` | Rice University | |

## Custom Specifications

Create a YAML file with your requirements:

```yaml
name: my-university
university: My University
description: Custom thesis requirements

margins:
  left: 1.5
  right: 1.0
  top: 1.0
  bottom: 1.0
  tolerance: 0.05

fonts:
  allowed_fonts:
    - Times New Roman
    - Arial
  body_size: 12.0

spacing:
  required_ratio: 2.0  # double-spaced
  tolerance: 0.2

page_numbers:
  front_matter:
    style: roman
    alignment: center
  body:
    style: arabic
    alignment: center
```

Use it:

```bash
thesis-check my-thesis.pdf --spec my-university.yaml
```

## How It Works

Thesis Compliance uses PyMuPDF to analyze the actual rendered PDF, not just source code:

1. **Margin detection** - Calculates content bounding box and measures distance from page edges
2. **Font extraction** - Reads embedded font information and sizes from each text block
3. **Line spacing** - Measures baseline-to-baseline distance divided by font size
4. **Page numbers** - Detects Roman/Arabic numerals near page edges

This "Software 2.0" approach catches issues that source linting misses, like font substitution or spacing from included figures.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src

# Linting
ruff check src tests
```

## License

MIT
