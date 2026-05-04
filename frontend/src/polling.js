// frontend/src/polling.js — Job polling logic

import { callApi } from "./api.js";
import * as state from "./state.js";
import { refreshTabStatuses } from "./tabs.js";
import { renderJobStatus } from "./log.js";

const TERMINAL_JOB_STATUSES = ["succeeded", "failed", "cancelled"];

// updateRunBtn injected from main.js to avoid circular import with jobs.js
let _updateRunBtn = null;
export function setPollingUpdateRunBtn(fn) { _updateRunBtn = fn; }

export function startPolling() {
  if (state.pollTimer) clearTimeout(state.pollTimer);
  pollAll();
}

async function pollAll() {
  try {
    const allJobs = await callApi("/jobs");
    const activeJobId = state.activeTab ? state.tabStates[state.activeTab]?.jobId : null;
    const seen = new Set();
    for (const snap of allJobs) {
      seen.add(snap.id);
      state.jobsCache[snap.id] = snap;
    }
    if (activeJobId && seen.has(activeJobId)) {
      state.jobsCache[activeJobId] = await callApi(`/jobs/${activeJobId}`, { timeoutMs: 20000, retries: 1 });
    }
    for (const id of Object.keys(state.jobsCache)) {
      if (!seen.has(id)) delete state.jobsCache[id];
    }
    const referencedJobIds = new Set(Object.values(state.tabStates).map(st => st?.jobId).filter(Boolean));
    const removable = Object.values(state.jobsCache)
      .filter(job => TERMINAL_JOB_STATUSES.includes(job.status) && !referencedJobIds.has(job.id))
      .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
    for (const job of removable.slice(20)) {
      delete state.jobsCache[job.id];
    }
    refreshTabStatuses();
    renderJobStatus();
    if (_updateRunBtn) _updateRunBtn();
    const anyRunning = allJobs.some(j => ["queued","running","cancelling"].includes(j.status));
    const targetInterval = anyRunning ? 2000 : 5000;
    state.setPollTimer(setTimeout(pollAll, targetInterval));
  } catch (err) {
    console.error("[pollAll]", err);
    state.setPollTimer(setTimeout(pollAll, 5000));
  }
}
