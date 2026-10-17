const assert = require("node:assert/strict");
const path = require("node:path");
const { test } = require("node:test");
const { ESLint } = require("eslint");
const baseline = require("./eslint9-rule-baseline.json");
const diagnostics = require("./eslint9-diagnostics.json");
const lock = require("../package-lock.json");

const web = path.resolve(__dirname, "..");
const eslint = new ESLint({ cwd: web, overrideConfigFile: path.join(web, "eslint.config.mjs") });

test("one supported ESLint version serves the version-scoped Next compatibility layer", () => {
  assert.equal(ESLint.version, "10.13.0");
  const expected = { "eslint-plugin-react": "7.37.5", "eslint-plugin-import": "2.32.0",
    "eslint-plugin-jsx-a11y": "6.10.2" };
  const nextDirectory = path.dirname(require.resolve("eslint-config-next"));
  assert.equal(require(path.join(nextDirectory, "../package.json")).version, "16.4.2");
  for (const [plugin, version] of Object.entries(expected)) {
    const pluginManifest = require.resolve(`${plugin}/package.json`, { paths: [nextDirectory] });
    assert.equal(require(pluginManifest).version, version);
    assert.equal(require.resolve("eslint", { paths: [path.dirname(pluginManifest)] }),
      require.resolve("eslint"));
  }
  const installed = Object.entries(lock.packages).filter(([name]) => /(^|\/)node_modules\/eslint$/.test(name));
  assert.equal(installed.length, 1, "a nested ESLint 9 would reintroduce the deprecated dependency");
  assert.equal(installed[0][1].version, ESLint.version);
});

for (const extension of ["jsx", "tsx", "mjs"]) {
  test(`the complete effective ${extension} rule map is unchanged from ESLint 9`, async () => {
    const config = await eslint.calculateConfigForFile(path.join(web, `src/app/lint-fixture.${extension}`));
    const expected = extension === "tsx"
      ? { ...baseline.jsx, ...baseline.typescriptOverrides } : baseline.jsx;
    // ESLint 10 exposes extra default options for disabled core rules. Their
    // severity must remain zero; options have no effect until a rule is enabled.
    const effectiveRules = rules => Object.fromEntries(Object.entries(rules)
      .map(([name, setting]) => [name, setting[0] === 0 ? [0] : setting]));
    assert.deepEqual(effectiveRules(config.rules), effectiveRules(expected));
  });
}

for (const { name, code, language, rule, messages } of diagnostics) {
  test(`the actual Next config preserves ESLint 9 diagnostics: ${name}`, async () => {
    assert.ok(messages.some(message => message.ruleId === rule), `${rule} must be covered by the baseline`);
    const [result] = await eslint.lintText(code, { filePath: path.join(web, `src/app/lint-fixture.${language}`) });
    const actual = result.messages.map(({ ruleId, severity, message, line, column, endLine, endColumn }) =>
      ({ ruleId, severity, message, line, column, endLine, endColumn }));
    assert.deepEqual(JSON.parse(JSON.stringify(actual)), messages);
  });
}

for (const language of ["jsx", "tsx"]) {
  test(`valid ${language} retains React/JSX reference tracking without false positives`, async () => {
    const checking = new ESLint({ cwd: web, overrideConfigFile: path.join(web, "eslint.config.mjs"),
      overrideConfig: [{ rules: { "no-unused-vars": "error", "no-undef": "error" } }] });
    const [result] = await checking.lintText(
      'import React from "react"; const Label = () => <span>Safe</span>; export default function Page() { return <Label />; }',
      { filePath: path.join(web, `src/app/lint-fixture.${language}`) },
    );
    assert.deepEqual(result.messages, []);
  });
}

test("Next's Babel compatibility layer resolves browser, Node and inline globals", async () => {
  const checking = new ESLint({ cwd: web, overrideConfigFile: path.join(web, "eslint.config.mjs"),
    overrideConfig: [{ rules: { "no-undef": "error" } }] });
  const [result] = await checking.lintText(
    '/* global injectedValue */ export function read() { return [window.location, process.env.NODE_ENV, injectedValue]; }',
    { filePath: path.join(web, "src/app/lint-fixture.js") },
  );
  assert.deepEqual(result.messages, []);
});
