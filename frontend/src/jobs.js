// frontend/src/jobs.js — Run/Stop buttons, updateRunBtn, isCurrentSheetRunning

import { callApi } from "./api.js";
import { runBtn, stopBtn, fSid, fSname, sheetStatus, dupWarning, output } from "./dom.js";
import * as state from "./state.js";
import { getJobStatus, saveFormToState } from "./tabs.js";
import { checkDuplicate, scheduleDupCheck } from "./dedup.js";
import { printLog, renderJobStatus } from "./log.js";
import { startPolling } from "./polling.js";

const ACTIVE_JOB_STATUSES = ["queued", "running", "cancelling"];
const STOPPABLE_JOB_STATUSES = ["queued", "running"];

// Ngăn form tự submit (reload trang)
document.querySelector("#job-form")?.addEventListener("submit", e => e.preventDefault());

export function isCurrentSheetRunning() {
  const sid   = fSid.value.trim();
  const sname = fSname.value.trim() || "Sheet1";
  if (!sid) return false;
  const currentJobId = state.activeTab ? state.tabStates[state.activeTab]?.jobId : null;
  return Object.values(state.jobsCache).some(j =>
    j.spreadsheet_id === sid &&
    j.sheet_name     === sname &&
    ACTIVE_JOB_STATUSES.includes(j.status) &&
    j.id !== currentJobId
  );
}

export function updateRunBtn() {
  if (!state.activeTab) {
    runBtn.disabled = true;
    stopBtn.disabled = true;
    return;
  }
  const p            = state.profiles.find(x => x.id === state.activeTab);
  const st           = state.tabStates[state.activeTab] || {};
  const hasSid       = !!fSid.value.trim();
  const sheetReady   = state.sheetValidation.status !== "invalid";
  const jobStatus    = getJobStatus(st.jobId);
  const isRunning    = ACTIVE_JOB_STATUSES.includes(jobStatus);
  const isStoppable  = STOPPABLE_JOB_STATUSES.includes(jobStatus);
  const sheetConflict = !isRunning && isCurrentSheetRunning();
  runBtn.disabled  = !p?.logged_in || !hasSid || !sheetReady || isRunning || sheetConflict;
  stopBtn.disabled = !isStoppable;
  if (sheetConflict) {
    runBtn.title = "Sheet này đang được xử lý ở tab khác";
    dupWarning.style.display = "block";
  } else if (!isRunning) {
    runBtn.title = "";
  }
}

fSid.addEventListener("input",   () => { scheduleDupCheck(); updateRunBtn(); });
fSname.addEventListener("input", () => { scheduleDupCheck(); updateRunBtn(); });

let sheetCheckTimer = null;

async function validateSheet() {
  const spreadsheetId = fSid.value.trim();
  const sheetName = fSname.value.trim() || "Sheet1";
  const profileId = state.activeTab;
  if (!spreadsheetId || !profileId) {
    state.setSheetValidation({ status: "idle", message: "" });
    sheetStatus.style.display = "none";
    updateRunBtn();
    return;
  }
  state.setSheetValidation({ status: "checking", message: "Dang kiem tra Sheet ID va Sheet name..." });
  sheetStatus.textContent = "Dang kiem tra Sheet ID va Sheet name...";
  sheetStatus.className = "sheet-status";
  sheetStatus.style.display = "block";
  try {
    const result = await callApi(`/utils/sheet-validate?spreadsheet_id=${encodeURIComponent(spreadsheetId)}&sheet_name=${encodeURIComponent(sheetName)}&profile_id=${encodeURIComponent(profileId)}`, { timeoutMs: 20000, retries: 1 });
    if (result.ok) {
      state.setSheetValidation({ status: "valid", message: result.message });
      sheetStatus.textContent = `✓ Sheet ID va Sheet name hop le`;
      sheetStatus.className = "sheet-status ok";
      sheetStatus.style.display = "block";
    } else {
      state.setSheetValidation({ status: "invalid", message: result.message });
      sheetStatus.textContent = `✗ ${result.message}`;
      sheetStatus.className = "sheet-status error";
      sheetStatus.style.display = "block";
    }
  } catch (e) {
    state.setSheetValidation({ status: "invalid", message: "Khong tim thay Google Sheet ID" });
    sheetStatus.textContent = "✗ Khong tim thay Google Sheet ID";
    sheetStatus.className = "sheet-status error";
    sheetStatus.style.display = "block";
  }
  updateRunBtn();
}

function scheduleSheetValidation() {
  clearTimeout(sheetCheckTimer);
  sheetCheckTimer = setTimeout(validateSheet, 600);
}

fSid.addEventListener("input", scheduleSheetValidation);
fSname.addEventListener("input", scheduleSheetValidation);

runBtn.addEventListener("click", async () => {
  const runProfileId = state.activeTab;
  if (!runProfileId) return;
  saveFormToState(runProfileId);
  const st = state.tabStates[runProfileId];
  const previousJobId = st.jobId;
  const previousJob = previousJobId ? state.jobsCache[previousJobId] : null;
  if (previousJob && ["succeeded", "failed", "cancelled"].includes(previousJob.status)) {
    delete state.jobsCache[previousJobId];
    state.tabStates[runProfileId].jobId = null;
    if (state.activeTab === runProfileId) printLog("Dang khoi dong job moi...");
  }
  await checkDuplicate(runProfileId);
  if (dupWarning.style.display === "block") {
    if (!confirm("Trang tính này đang được xử lý ở nơi khác. Vẫn tiếp tục?")) return;
  }
  runBtn.disabled = true;
  runBtn.textContent = "Đang khởi động...";
  try {
    const timestamps = st.timestamps.split(",").map(v => parseInt(v.trim(), 10)).filter(Number.isFinite);
    const snap = await callApi("/jobs", {
      method: "POST",
      timeoutMs: 60000,
      retries: 2,
      body: JSON.stringify({
        spreadsheet_id: st.spreadsheetId, sheet_name: st.sheetName,
        drive_folder: st.driveFolder, video_url_col: st.videoUrlCol,
        thumb_col: st.thumbCol, target_timestamps: timestamps,
        max_workers: 3, upload_workers: 3,
        thumb_quality: 2, thumb_width: 1280, profile_ids: [runProfileId],
      }),
    });
    state.tabStates[runProfileId].jobId = snap.id;
    state.jobsCache[snap.id] = snap;
    if (state.activeTab === runProfileId) {
      updateRunBtn();
      renderJobStatus();      // Hiện log ngay lập tức, không chờ poll
      stopBtn.disabled = false;
    }
    startPolling();
  } catch (e) {
    if (state.tabStates[runProfileId]) {
      state.tabStates[runProfileId].jobId = null;
    }
    if (state.activeTab === runProfileId) {
      stopBtn.disabled = true;
      printLog("Lỗi tạo job:\n" + e.message);
    }
  }
  finally { runBtn.textContent = "▶ Chạy"; updateRunBtn(); }
});

stopBtn.addEventListener("click", async () => {
  const stopProfileId = state.activeTab;
  const jobId = stopProfileId ? state.tabStates[stopProfileId]?.jobId : null;
  if (!jobId) return;
  stopBtn.disabled = true;
  const currentSnap = state.jobsCache[jobId];
  if (currentSnap && ["queued", "running"].includes(currentSnap.status)) {
    state.jobsCache[jobId] = {
      ...currentSnap,
      status: "cancelling",
      logs: [...(currentSnap.logs || []), "Dang gui yeu cau dung..."],
    };
    if (state.activeTab === stopProfileId) {
      updateRunBtn();
      renderJobStatus();
    }
  }
  try {
    // DELETE trả về snapshot với log mới nhất — cập nhật ngay, không chờ poll
    const snap = await callApi(`/jobs/${jobId}`, { method: "DELETE", timeoutMs: 60000, retries: 2 });
    state.jobsCache[snap.id] = snap;
    if (state.activeTab === stopProfileId) {
      updateRunBtn();
      renderJobStatus();   // hiện log “⏹ Đã gửi lệnh dừng” ngay lập tức
    }
  } catch (e) {
    // Không dùng printLog (đè log) — thêm 1 dòng vào output
    if (state.activeTab === stopProfileId) {
      output.textContent += "\nLỗi dừng: " + e.message;
      stopBtn.disabled = false;
    }
  }
});
