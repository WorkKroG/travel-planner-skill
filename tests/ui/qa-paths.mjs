import path from "node:path";
import { fileURLToPath } from "node:url";

export function repositoryRootFromModuleUrl(moduleUrl) {
  return path.resolve(path.dirname(fileURLToPath(moduleUrl)), "../..");
}
