# Next.js lint directory adapter

The override applies only to `@next/eslint-plugin-next@16.4.2`. That version uses
one `fast-glob` call: `globSync(pattern, { onlyDirectories: true })` in
`get-root-dirs`. This adapter preserves that call using `tinyglobby@0.2.17`.
It is not a general replacement for fast-glob.

The original dependency chain ends in `braces@3.0.3`, which has no patched
release for [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
A direct tinyglobby alias changes literal-directory expansion and absolute-path
results. The adapter disables expansion, retains absolute output and literal
paths, normalizes dynamic directory suffixes, and excludes the base directory
for a trailing globstar. `brace-expansion@5.0.12` preserves numeric and nested
brace ranges; it is a separate maintained package from the vulnerable `braces`.
The [upstream migration guide](https://superchupu.dev/tinyglobby/migration)
documents the expansion difference.

The local file override is relative to the scoped Next plugin's directory.
The committed `.npmrc` sets `install-links=true` so npm packages the adapter
instead of creating a broken dependency-relative symlink. Keep that setting for
`npm ci`; the lockfile contains the adapter and its exact dependencies.

`npm run test:lint-config` exercises the actual Next resolver and ESLint rules.
When updating the Next config/plugin, review their glob usage and remove this
override once upstream no longer includes the vulnerable chain. Unexpected
adapter calls fail explicitly instead of silently weakening lint checks.
