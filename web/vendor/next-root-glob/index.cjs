const fs = require("node:fs");
const path = require("node:path");
const { globSync: findDirectories, isDynamicPattern } = require("tinyglobby");
const { expand } = require("brace-expansion");

// This is the only fast-glob API used by @next/eslint-plugin-next@16.4.2.
// Reject new callers/options so an upstream change cannot silently alter linting.
exports.globSync = function globSync(pattern, options) {
  if (typeof pattern !== "string" || pattern.length === 0) {
    throw new TypeError("Next root directory pattern must be a non-empty string");
  }
  if (!options || options.onlyDirectories !== true ||
      Object.keys(options).some(key => key !== "onlyDirectories")) {
    throw new TypeError("This adapter supports only Next's directory-only globSync call");
  }

  if (!isDynamicPattern(pattern)) {
    try {
      return fs.statSync(pattern).isDirectory() ? [pattern] : [];
    } catch (error) {
      if (error.code === "ENOENT" || error.code === "ENOTDIR") return [];
      throw error;
    }
  }

  // fast-glob's final globstar matches descendants, excluding its base directory.
  const searches = expand(pattern).map(part =>
    part.replace(/\/+$/, "").replace(/(^|\/)\*\*$/, "$1**/*")
  );
  const absolute = path.isAbsolute(pattern);
  return findDirectories(searches, {
    onlyDirectories: true,
    expandDirectories: false,
    absolute,
  }).map(directory => {
    const clean = directory.replace(/\/$/, "") || "/";
    return !absolute && pattern.startsWith("./") && !clean.startsWith("./")
      ? `./${clean}` : clean;
  });
};
