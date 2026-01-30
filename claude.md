# Thesis Compliance Checker

Automated thesis/dissertation compliance checker that analyzes PDF documents against university formatting requirements (margins, fonts, spacing, page numbers). Uses a "Software 2.0" approach - analyzing rendered PDF output rather than LaTeX source to catch font substitution, figure spacing, and other rendering issues.

## Tech Stack

- **Language:** Python 3.11+
- **PDF Processing:** PyMuPDF (fitz) >=1.23.0, pdfplumber >=0.10.0
- **CLI:** Typer >=0.9.0 with Rich >=13.0.0 for terminal output
- **Data Validation:** Pydantic >=2.0.0
- **Configuration:** PyYAML >=6.0
- **API (optional):** FastAPI >=0.109.0, Uvicorn >=0.27.0
- **Testing:** pytest >=7.0.0, pytest-cov >=4.0.0
- **Linting:** Ruff (line-length: 100), MyPy (strict mode)
- **Build:** Hatchling

## Architecture & Data Flow

```
PDF File → ThesisChecker → PDFDocument (cached extraction)
                ↓
    ┌──────────┼──────────┬──────────┐
    ↓          ↓          ↓          ↓
MarginExt  FontExt   SpacingExt  PageNumExt
    └──────────┴──────────┴──────────┘
                ↓
         RuleEvaluator (applies StyleSpec)
                ↓
         ComplianceReport → Reporter (console/json)
```

**Key Modules:**
- `src/thesis_compliance/extractor/` - PDF data extraction (pdf.py, margins.py, fonts.py, spacing.py, pages.py)
- `src/thesis_compliance/checker/` - Compliance logic (engine.py, evaluators.py, violations.py)
- `src/thesis_compliance/spec/` - YAML spec loading and rule models (loader.py, rules.py, builtin/*.yaml)
- `src/thesis_compliance/reporter/` - Output formatting (console.py, json.py)

## Coding Standards

**Type Hints:** ALL functions must have complete type annotations
```python
# Good:
def get_margins(self, page_num: int) -> Margins:

# Bad:
def get_margins(self, page_num):
```

**Modern Python:** Use 3.10+ syntax
```python
# Good:
pages: str | list[int] | None = None

# Bad:
pages: Optional[Union[str, List[int]]] = None
```

**Docstrings:** Google-style for all public functions
```python
def check(self, pages: str | list[int] | None = None) -> ComplianceReport:
    """Run compliance check on the PDF.

    Args:
        pages: Pages to check - can be None (all), str ("1-10,20"), or list[int].

    Returns:
        ComplianceReport with all violations found.

    Raises:
        ValueError: If page specification is invalid.
    """
```

**Naming:**
- `snake_case` for functions, variables, methods
- `CamelCase` for classes
- `UPPER_CASE` for constants
- Leading underscore for private (`_cache`, `_normalize_pages`)

**Imports:** Three groups separated by blank lines (stdlib, third-party, local)

**Data Models:**
- Dataclasses for domain models (PageInfo, Violation, ComplianceReport)
- Pydantic BaseModel for API request/response only
- Enums for constrained values (Severity, RuleType)

**Error Handling:**
- Raise specific exceptions (ValueError, FileNotFoundError)
- Document exceptions in docstrings with `Raises:`
- Use context managers for resource cleanup
- Chain exceptions with `from e`

## Critical Rules

1. **NEVER** return mutable cached data directly - always return defensive copies:
   ```python
   return list(self._cache[key])  # Good
   return self._cache[key]        # Bad
   ```

2. **NEVER** use generic `except Exception:` without logging or re-raising

3. **NEVER** hardcode file paths - use Path objects and resolve relative to project

4. **NEVER** skip type hints on function signatures

5. **NEVER** use wildcard imports (`from x import *`)

6. **NEVER** commit secrets or API keys - use environment variables

7. **NEVER** write to `/tmp` in GitHub Actions - use `$RUNNER_TEMP`

8. **NEVER** use unquoted shell variables in GitHub Actions:
   ```bash
   # Good:
   ARGS=("${{ inputs.pdf-path }}" --spec "${{ inputs.spec }}")
   thesis-check "${ARGS[@]}"

   # Bad:
   thesis-check ${{ inputs.pdf-path }} --spec ${{ inputs.spec }}
   ```

## Project Patterns

**Caching (PDFDocument):**
- Cache text blocks and page info per page number
- Call `preload_pages()` before multi-pass analysis
- Clear cache on document close

**Violation Creation:**
- Use `ViolationBuilder` factory methods, not direct Violation construction
- Always include: rule_id, rule_type, severity, message
- Include when available: page, expected, found, suggestion

**Spec System:**
- Built-in specs in `spec/builtin/*.yaml`
- Custom specs via file path
- Default spec: "rackham" (University of Michigan)

**Testing:**
- Test fixtures in `tests/fixtures/` (valid_thesis.pdf, bad_margins.pdf, etc.)
- Use pytest with coverage
- Test both success and error paths
