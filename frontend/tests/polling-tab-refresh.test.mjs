import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/polling.js", import.meta.url), "utf8");

test("polling updates tab status without rebuilding the tab list", () => {
  assert.match(source, /import \{ refreshTabStatuses \} from "\.\/tabs\.js"/);
  assert.match(source, /refreshTabStatuses\(\)/);
  assert.doesNotMatch(source, /renderTabs\(\)/);
});
