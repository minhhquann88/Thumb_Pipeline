import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/jobs.js", import.meta.url), "utf8");

test("starting a job keeps the profile that clicked run", () => {
  assert.match(source, /const runProfileId\s*=\s*state\.activeTab/);
  assert.match(source, /saveFormToState\(runProfileId\)/);
  assert.match(source, /const st\s*=\s*state\.tabStates\[runProfileId\]/);
  assert.match(source, /checkDuplicate\(runProfileId\)/);
  assert.match(source, /profile_ids:\s*\[runProfileId\]/);
  assert.match(source, /max_workers:\s*3/);
  assert.match(source, /state\.tabStates\[runProfileId\]\.jobId\s*=\s*snap\.id/);
  assert.match(source, /timeoutMs:\s*60000/);
  assert.match(source, /retries:\s*2/);
});

test("stopping a job marks the clicked profile as cancelling immediately", () => {
  assert.match(source, /const stopProfileId\s*=\s*state\.activeTab/);
  assert.match(source, /status:\s*"cancelling"/);
  assert.match(source, /Dang gui yeu cau dung/);
  assert.match(source, /state\.activeTab === stopProfileId/);
});
