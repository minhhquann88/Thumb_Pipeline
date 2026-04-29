// frontend/src/tabs.js — Tab management, form↔state sync, layout

import { acctTabbar, emptyState, workspace, fSid, fSname, fFolder, fVcol, fTcol, fTs, dupWarning, output } from "./dom.js";
import * as state from "./state.js";
import { esc } from "./utils.js";
import { renderJobStatus } from "./log.js";

// ─── Tab rendering ────────────────────────────────────────────────────────

export function getJobStatus(jobId) {
  return state.jobsCache[jobId]?.status ?? null;
}

export function statusDotClass(status) {
  return { queued:"dot-waiting", running:"dot-running", cancelling:"dot-waiting", succeeded:"dot-done", failed:"dot-error", cancelled:"dot-offline" }[status] ?? "dot-idle";
}

export function renderTabs() {
  acctTabbar.innerHTML = "";
  for (const p of state.profiles) {
    const tab = document.createElement("button");
    tab.className = "acct-tab" + (p.id === state.activeTab ? " active" : "");
    tab.dataset.pid = p.id;

    const st = state.tabStates[p.id] || {};
    const jobId = st.jobId;
    const jobStatus = jobId ? getJobStatus(jobId) : null;
    const dotClass  = jobStatus ? statusDotClass(jobStatus) : (p.logged_in ? "dot-idle" : "dot-offline");

    const letter = (p.email || p.name || "?")[0].toUpperCase();
    tab.innerHTML = `
      <span class="tab-avatar">${letter}</span>
      <span class="tab-name">${esc(p.name)}</span>
      <span class="tab-dot ${dotClass}"></span>`;
    tab.title = p.email || p.name;
    tab.addEventListener("click", () => switchTab(p.id));
    acctTabbar.appendChild(tab);
  }
}

export function refreshTabStatuses() {
  for (const p of state.profiles) {
    const tab = acctTabbar.querySelector(`[data-pid="${CSS.escape(p.id)}"]`);
    if (!tab) continue;
    tab.classList.toggle("active", p.id === state.activeTab);

    const st = state.tabStates[p.id] || {};
    const jobStatus = st.jobId ? getJobStatus(st.jobId) : null;
    const dotClass = jobStatus ? statusDotClass(jobStatus) : (p.logged_in ? "dot-idle" : "dot-offline");
    const dot = tab.querySelector(".tab-dot");
    if (dot) dot.className = `tab-dot ${dotClass}`;
  }
}

// ─── Form ↔ State ──────────────────────────────────────────────────────────

export function saveFormToState(pid) {
  if (!state.tabStates[pid]) state.tabStates[pid] = { ...state.DEFAULT_SETTINGS };
  state.tabStates[pid].spreadsheetId = fSid.value.trim();
  state.tabStates[pid].sheetName     = fSname.value.trim() || "Sheet1";
  state.tabStates[pid].driveFolder   = fFolder.value.trim() || "thumbnails";
  state.tabStates[pid].videoUrlCol   = parseInt(fVcol.value, 10) || 3;
  state.tabStates[pid].thumbCol      = parseInt(fTcol.value, 10) || 14;
  state.tabStates[pid].timestamps    = fTs.value.trim() || "3,8,13,18,23";
}

export function loadStateToForm(pid) {
  const st = state.tabStates[pid] || state.DEFAULT_SETTINGS;
  fSid.value     = st.spreadsheetId;
  fSname.value   = st.sheetName;
  fFolder.value  = st.driveFolder;
  fVcol.value    = st.videoUrlCol;
  fTcol.value    = st.thumbCol;
  fTs.value      = st.timestamps;
  dupWarning.style.display = "none";
  output.textContent = st.jobId ? "Đang tải log..." : "Chưa có dữ liệu.";
  fSid.dispatchEvent(new Event("input"));
}

// ─── Layout ───────────────────────────────────────────────────────────────

export function updateLayout() {
  const hasProfiles = state.profiles.length > 0;
  emptyState.style.display  = hasProfiles ? "none" : "flex";
  workspace.style.display   = (hasProfiles && state.activeTab) ? "flex" : "none";
}

// ─── Switch tab (called externally and by tab click) ──────────────────────
// We import updateRunBtn lazily to break circular dependency

let _updateRunBtn = null;
export function setUpdateRunBtnFn(fn) { _updateRunBtn = fn; }

let _renderAccountCard = null;
export function setRenderAccountCardFn(fn) { _renderAccountCard = fn; }

export function switchTab(pid) {
  // Save current form values
  if (state.activeTab && state.tabStates[state.activeTab]) {
    saveFormToState(state.activeTab);
  }
  state.setActiveTab(pid);
  renderTabs();
  loadStateToForm(pid);
  if (_renderAccountCard) _renderAccountCard();
  renderJobStatus();
  if (_updateRunBtn) _updateRunBtn();
  updateLayout();
}
