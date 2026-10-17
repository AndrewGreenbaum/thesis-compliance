# Development notes

The Python package is in `src/thesis_compliance`; the optional Next.js client is in `web`. Run commands and checks from README.md.

`ThesisChecker` orchestrates PDF extraction, rule evaluation, and reporting. Built-in specs are YAML files under `spec/builtin`. Keep cached extraction results private and return defensive copies. Close PDF resources with context managers.

Use typed Python and the existing rule/violation models. Add a focused regression for behavior changes, including failure paths. Keep API file handling bounded, clean temporary files, and mock outbound requests in tests.

The CLI entry point is `thesis-check check FILE`, not `thesis-check FILE`. GitHub Action inputs must be passed through environment variables and argument lists, never interpolated into shell source.

University specs and PDF layout inference need manual validation. Do not describe a passing report as guaranteed thesis acceptance.
