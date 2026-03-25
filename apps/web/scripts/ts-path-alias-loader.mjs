import { accessSync, constants } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const PROJECT_ROOT = fileURLToPath(new URL("..", import.meta.url));
const SRC_ROOT = path.join(PROJECT_ROOT, "src");
const FILE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

export async function resolve(specifier, context, nextResolve) {
  const candidatePath = resolveCandidatePath(specifier, context.parentURL);
  if (candidatePath) {
    const resolvedFile = findExistingModule(candidatePath);
    if (resolvedFile) {
      return nextResolve(pathToFileURL(resolvedFile).href, context);
    }
  }
  return nextResolve(specifier, context);
}

function resolveCandidatePath(specifier, parentURL) {
  if (specifier.startsWith("@/")) {
    return path.join(SRC_ROOT, specifier.slice(2));
  }
  if (!specifier.startsWith("./") && !specifier.startsWith("../")) {
    return null;
  }
  if (!parentURL?.startsWith("file:")) {
    return null;
  }
  const parentPath = path.dirname(fileURLToPath(parentURL));
  return path.resolve(parentPath, specifier);
}

function findExistingModule(basePath) {
  if (fileExists(basePath)) {
    return basePath;
  }
  for (const extension of FILE_EXTENSIONS) {
    if (fileExists(`${basePath}${extension}`)) {
      return `${basePath}${extension}`;
    }
  }
  for (const extension of FILE_EXTENSIONS) {
    const indexFile = path.join(basePath, `index${extension}`);
    if (fileExists(indexFile)) {
      return indexFile;
    }
  }
  return null;
}

function fileExists(filePath) {
  try {
    accessSync(filePath, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}
