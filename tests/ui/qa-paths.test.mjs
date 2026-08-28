import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";

import { repositoryRootFromModuleUrl } from "./qa-paths.mjs";

test("module URL decodes spaces before repository path resolution", () => {
  const moduleUrl = pathToFileURL("/private/tmp/Travel Planner/tests/ui/qa.mjs").href;

  assert.equal(repositoryRootFromModuleUrl(moduleUrl), "/private/tmp/Travel Planner");
});
