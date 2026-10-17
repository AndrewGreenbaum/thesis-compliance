const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { before, after, test } = require("node:test");
const { ESLint, Linter } = require("eslint");
const plugin = require("@next/eslint-plugin-next");
const pluginDirectory = path.dirname(require.resolve("@next/eslint-plugin-next"));
const { getRootDirs } = require(path.join(pluginDirectory, "utils/get-root-dirs.js"));
const adapterPath = require.resolve("fast-glob", { paths: [pluginDirectory] });
const adapter = require(adapterPath);
const baseline = require("./fast-glob-baseline.json");

const web = path.resolve(__dirname, "..");
const originalCwd = process.cwd();
let fixture;
before(() => {
  fixture = fs.mkdtempSync(path.join(os.tmpdir(), "next-lint-roots-"));
  for (const directory of ["apps/one/pages", "apps/one/app/blog", "apps/two/src/app",
    "apps/.hidden/pages", "empty", "apps/01/pages", "apps/02/pages", "apps/03/pages",
    "packages/web/pages", "space dir/pages"]) {
    fs.mkdirSync(path.join(fixture, directory), { recursive: true });
  }
  fs.writeFileSync(path.join(fixture, "apps/regular-file"), "not a directory");
  fs.writeFileSync(path.join(fixture, "apps/one/pages/about.js"), "export default function Page() {}");
  process.chdir(fixture);
});
after(() => {
  process.chdir(originalCwd);
  fs.rmSync(fixture, { recursive: true, force: true });
});
const resolveFixture = value => value.replaceAll("<ROOT>", fixture.replaceAll("\\", "/"));

test("the pinned Next plugin resolves the committed local adapter", () => {
  assert.equal(require("@next/eslint-plugin-next/package.json").version, "16.4.2");
  assert.equal(fs.readFileSync(adapterPath, "utf8"),
    fs.readFileSync(path.join(web, "vendor/next-root-glob/index.cjs"), "utf8"));
  assert.deepEqual(Object.keys(adapter), ["globSync"]);
  assert.throws(() => adapter.globSync("apps/*", {}), TypeError);
  assert.throws(() => adapter.globSync(["apps/*"], { onlyDirectories: true }), TypeError);
});

for (const { pattern, expected } of baseline.cases) {
  test(`Next root resolution matches fast-glob 3.3.1: ${pattern}`, () => {
    const roots = getRootDirs({ cwd: fixture, settings: { next: {
      rootDir: resolveFixture(pattern),
    } } });
    assert.deepEqual(roots.sort(), expected.map(resolveFixture).sort());
  });
}

test("Next preserves default cwd, root arrays and Windows-style separators", () => {
  assert.deepEqual(getRootDirs({ cwd: fixture, settings: {} }), [fixture]);
  assert.deepEqual(getRootDirs({ cwd: fixture, settings: { next: {
    rootDir: ["apps\\one", "packages\\*", 42],
  } } }).sort(), ["apps/one", "packages/web"]);
});

test("Next's real page-link rule still finds pages through the overridden resolver", () => {
  const linter = new Linter({ cwd: fixture });
  for (const rootDir of ["apps/one", "apps/{one,two}", ["apps\\one", "missing"]]) {
    const messages = linter.verify(
      'export default function Page() { return <a href="/about">About</a>; }',
      [{ languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
        plugins: { "@next/next": plugin },
        settings: { next: { rootDir } },
        rules: { "@next/next/no-html-link-for-pages": "error" } }],
      { filename: "example.js" },
    );
    assert.ok(messages.some(message =>
      message.ruleId === "@next/next/no-html-link-for-pages" && message.severity === 2),
    JSON.stringify(messages));
  }
});

test("the actual Next/TypeScript config retains framework and hook checks", async () => {
  const eslint = new ESLint({ cwd: web, overrideConfigFile: path.join(web, "eslint.config.mjs") });
  const config = await eslint.calculateConfigForFile(path.join(web, "src/app/check/page.tsx"));
  for (const rule of ["@next/next/no-html-link-for-pages", "react-hooks/rules-of-hooks",
    "@typescript-eslint/no-explicit-any"]) {
    assert.ok(config.rules[rule]?.[0] > 0, `${rule} must remain enabled`);
  }
});
