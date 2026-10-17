# Thesis Compliance

Checks thesis PDFs for possible formatting problems: margins, fonts, spacing, headings, captions, bibliography layout, and page numbers. The Python checker works on its own; the API and browser interface are optional.

This is a review aid. PDF structure is inferred, so flagged text needs a human check. The bundled university rules are snapshots, not a guarantee of current graduate-school requirements or acceptance.

## Run locally

Use Python 3.11 or newer. From this repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,api]"
thesis-check check my-thesis.pdf --spec rackham
thesis-check check my-thesis.pdf --pages 1-10,42 --format json --strict
thesis-check list-specs
thesis-check info my-thesis.pdf
```

`--spec` accepts a bundled name or a YAML file. The bundled YAML files are in `src/thesis_compliance/spec/builtin/`; start with one when writing a custom specification.

Exit codes: 0 means no errors; 1 means formatting errors; 2 means warnings in strict mode; 3 means a checker failure. Command-line usage mistakes may also return 2. JSON output goes to standard output.

## Browser interface

Start the API from the repository root with the virtual environment active:

```sh
uvicorn thesis_compliance.api:app --host 127.0.0.1 --port 8000
```

In another terminal, with Node.js 20.9 or newer:

```sh
cd web
npm ci
npm run dev
```

Open http://localhost:3000/check. The browser uses http://localhost:8000 by default; set `NEXT_PUBLIC_API_URL` before building to use another API address. Uploads are limited to 20 MiB.

For a production frontend build, run `npm run build` and `npm start` in `web`. If hosting the API externally, configure its allowed origins and put a request-size limit at the proxy. Multipart parsing happens before the application checks file size.

## GitHub Actions

The composite action in `action.yml` installs this checkout and runs the same CLI. It writes `errors`, `warnings`, and `passed` outputs, plus `thesis-results.json` in the runner temporary directory. Checker failures remain failures; missing or malformed JSON cannot produce a passing result.

The reusable workflow in `.github/workflows/thesis-check.yml` checks out the calling repository and the checker, runs the action, and uploads the report. It currently uses the checker's `main` branch; pin that checkout to a reviewed commit for a fixed version.

## Checks

```sh
pytest
ruff check src tests scripts
ruff format --check src tests scripts
mypy src
cd web
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser regressions mock API replies. API tests use temporary PDFs and mocked network responses; they do not fetch arbitrary live sites. URL downloads reject non-public destinations and check each redirect, with bounded reads and cleanup on failure.

MIT license.
