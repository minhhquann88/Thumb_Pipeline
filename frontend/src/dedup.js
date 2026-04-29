// frontend/src/dedup.js — Duplicate sheet check

import { callApi } from "./api.js";
import { fSid, fSname, dupWarning } from "./dom.js";
import { activeTab, tabStates } from "./state.js";

let dupTimer = null;

export async function checkDuplicate(currentProfileId = activeTab) {
  const sid   = fSid.value.trim();
  const sname = fSname.value.trim() || "Sheet1";
  if (!sid) { dupWarning.style.display = "none"; return; }

  try {
    const jobs = await callApi("/jobs");
    const currentJobId = currentProfileId ? tabStates[currentProfileId]?.jobId : null;
    const dup = jobs.find(j =>
      j.spreadsheet_id === sid &&
      j.sheet_name     === sname &&
      ["queued", "running", "cancelling"].includes(j.status) &&
      j.id !== currentJobId   // không đếm job của chính tab này
    );
    dupWarning.style.display = dup ? "block" : "none";
  } catch {
    dupWarning.style.display = "none";
  }
}

export function scheduleDupCheck() {
  clearTimeout(dupTimer);
  dupTimer = setTimeout(checkDuplicate, 600);
}
