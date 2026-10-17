# Thesis PDF Format Checker frontend

A Next.js interface for the Python thesis-formatting checker. It loads the
available university specifications from the API, uploads a PDF, and displays
errors, warnings, and suggestions returned by the checker.

Findings need human review. The bundled university specifications are snapshots;
a passing report does not guarantee acceptance by a graduate school.

## Run locally

Use Python 3.11 or newer, Node.js 22.13+ or 24, and npm. Start the API from the
repository root:

```sh
git clone https://github.com/AndrewGreenbaum/thesis-pdf-format-checker.git
cd thesis-pdf-format-checker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api]"
uvicorn thesis_compliance.api:app --host 127.0.0.1 --port 8000
```

In a second terminal, from the repository root:

```sh
cd web
npm ci
npm run dev
```

Open http://localhost:3000/check. The frontend requires the API to list
specifications and analyze PDFs; the CLI can run independently. Uploads are
limited to 20 MiB.

The API address defaults to http://localhost:8000. Set `NEXT_PUBLIC_API_URL`
before starting the frontend or building it to use a different address. The API
allows http://localhost:3000 by default; set its comma-separated `CORS_ORIGINS`
when using another frontend origin.

For a production frontend build, run `npm run build` then `npm start` in `web`.
The Python API remains a separate service. External deployments also need a
proxy request-size limit; see the [repository README](../README.md).

## Checks

From `web`:

```sh
npm ci
npm ls --all
npm run lint
npm run test:lint-config
npm audit --audit-level=high
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests use mocked API responses. The Python test suite and local CLI
instructions are in the [repository README](../README.md).

## Source layout

- `src/app/check/page.tsx`: fetches `/specs`, posts PDFs to `/check`, and manages the upload/results flow.
- `src/components/`: PDF selection, university selection, and report display.
- `src/lib/types.ts`: API response types and display conversion.
- `../src/thesis_compliance/api.py`: FastAPI endpoints; PDF parsing runs in Python.
- `../src/thesis_compliance/spec/builtin/`: bundled YAML university specifications.

Use `thesis-check list-specs` to see the current specifications. Add or update
YAML specifications in the Python package, then test them with the CLI; there is
no separate browser university database or PDF analyzer.

## Lint dependency compatibility

ESLint 10.13.0 runs through Next's published ESLint 10 compatibility layer in
`eslint-config-next` 16.4.2. Next restores the removed rule-context APIs used by
React/import rules and adapts its Babel parser. See
[Next PR #99628](https://github.com/vercel/next.js/pull/99628) and
[the upstream implementation](https://github.com/vercel/next.js/commit/907721a66e8b4174515445c27068d9835bd424d8).

The three plugins below still advertise ESLint 9 peer ranges. Version-scoped
overrides under `eslint-config-next@16.4.2` resolve those peers to our pinned
ESLint 10, using Next's tested runtime compatibility. No lint rules or audit
findings are suppressed, and `npm ci` needs neither `--force` nor
`--legacy-peer-deps`.

| Existing checks | Implementation after the upgrade | Coverage |
| --- | --- | --- |
| Next recommended and Core Web Vitals | Same `@next/eslint-plugin-next` 16.4.2 | Same rule names, levels and options; page-link and script regressions |
| React | Same `eslint-plugin-react` 7.37.5 through Next's context bridge | All 17 enabled rules retained; 15 diagnostic rules exercised in JSX and TSX, plus reference-tracking cases |
| Accessibility | Same `eslint-plugin-jsx-a11y` 6.10.2 | All 6 enabled rules exercised in JSX and TSX |
| Imports | Same `eslint-plugin-import` 2.32.0 through Next's context bridge | Anonymous-default-export warning exercised in JSX and TSX |
| Hooks and TypeScript | Same Next presets and plugins | Complete rule maps retained; hook-order and explicit-any regressions |

`npm run test:lint-config` compares the complete effective rule maps and 49
diagnostic fixtures against snapshots captured with ESLint 9.39.5 before the
upgrade. It also verifies Babel globals, JSX reference tracking, a single
installed ESLint version, and the existing directory-glob adapter. CI runs the
checks on both Node 22 and 24. When these plugin versions or Next change, review
their declared peers and remove overrides once their supported ranges allow it;
the version assertions deliberately require that review.

Newer npm versions also record approval for the pinned `unrs-resolver@1.12.2`
postinstall script, which prepares its platform-specific native binding used by
the TypeScript import resolver.
