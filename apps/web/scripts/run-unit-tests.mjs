import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROJECT_ROOT = fileURLToPath(new URL("..", import.meta.url));
const FEATURES_ROOT = path.join(PROJECT_ROOT, "src", "features");
const TEST_FILE_SUFFIX = ".test.ts";

const testFiles = listTestFiles(FEATURES_ROOT)
  .sort()
  .map((filePath) => path.relative(PROJECT_ROOT, filePath));

if (testFiles.length === 0) {
  throw new Error("No unit tests found under src/features.");
}

const result = spawnSync(
  process.execPath,
  ["--loader", "./scripts/ts-path-alias-loader.mjs", "--test", "--experimental-strip-types", ...testFiles],
  { cwd: PROJECT_ROOT, stdio: "inherit" },
);

if (result.error) {
  throw result.error;
}

process.exit(result.status ?? 1);

function listTestFiles(directoryPath) {
  return readdirSync(directoryPath, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      return listTestFiles(entryPath);
    }
    return entry.isFile() && entry.name.endsWith(TEST_FILE_SUFFIX) ? [entryPath] : [];
  });
}
