import { rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const nextDevTypesDirectory = path.resolve(scriptDirectory, "../.next/dev/types");

await rm(nextDevTypesDirectory, { force: true, recursive: true });
