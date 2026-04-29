import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/profiles.js", import.meta.url), "utf8");

test("adding an account does not steal the current active tab", () => {
  assert.match(source, /const shouldSelectNewProfile\s*=\s*!state\.activeTab/);
  assert.match(source, /if \(shouldSelectNewProfile\) switchTab\(profile\.id\)/);
  assert.doesNotMatch(source, /await loadProfiles\(\);\s*switchTab\(profile\.id\)/);
});
