// frontend/src/jobs.js — Run/Stop buttons, updateRunBtn, isCurrentSheetRunning
import { callApi } from "./api.js";

import { runBtn, stopBtn, fSid, fSname,
         sidStatus, snameStatus, output,
         checkSidBtn, checkSnameBtn, sidLinkWrap, sidLinkInput } from "./dom.js";
import * as state from "./state.js";
import { getJobStatus, saveFormToState } from "./tabs.js";
import { printLog, renderJobStatus } from "./log.js";
import { startPolling } from "./polling.js";

const ACTIVE_JOB_STATUSES   = ["queued", "running", "cancelling"];
const STOPPABLE_JOB_STATUSES = ["queued", "running"];

// Ngăn form tự submit (reload trang)
document.querySelector("#job-form")?.addEventListener("submit", e => e.preventDefault());

// Trang thai kiem tra rieng cho tung field
// "idle" | "checking" | "ok" | "error"
let sidCheckState   = { status: "idle", sheetNames: [] };
let snameCheckState = { status: "idle" };

function resetSidStatus() {
  sidCheckState = { status: "idle", sheetNames: [] };
  snameCheckState = { status: "idle" };
  _setStatus(sidStatus, "idle", "");
  _setStatus(snameStatus, "idle", "");
  const clearThumbStatus = document.querySelector("#clear-thumb-status");
  if (clearThumbStatus) clearThumbStatus.style.display = "none";
  if (sidLinkWrap) sidLinkWrap.style.display = "none";
  updateRunBtn();
}

function resetSnameStatus() {
  snameCheckState = { status: "idle" };
  _setStatus(snameStatus, "idle", "");
  const clearThumbStatus = document.querySelector("#clear-thumb-status");
  if (clearThumbStatus) clearThumbStatus.style.display = "none";
  updateRunBtn();
}

function _setStatus(el, type, msg) {
  if (!el) return;
  if (!msg) { el.style.display = "none"; return; }
  el.style.display = "block";
  el.className = "field-status" + (type === "ok" ? " ok" : type === "error" ? " error" : type === "checking" ? " checking" : "");
  el.textContent = msg;
}

// ─── Check Spreadsheet ID ─────────────────────────────────────────────────

async function checkSpreadsheetId() {
  const sid = fSid.value.trim();
  const pid = state.activeTab;
  if (!sid) { _setStatus(sidStatus, "error", "Vui lòng nhập Spreadsheet ID"); return; }
  if (!pid)  { _setStatus(sidStatus, "error", "Chưa chọn tài khoản"); return; }

  sidCheckState = { status: "checking", sheetNames: [] };
  _setStatus(sidStatus, "checking", "Đang kiểm tra Spreadsheet ID...");
  checkSidBtn.disabled = true;
  updateRunBtn();

  try {
    const r = await callApi(
      `/utils/check-spreadsheet?spreadsheet_id=${encodeURIComponent(sid)}&profile_id=${encodeURIComponent(pid)}`,
      { timeoutMs: 20000, retries: 1 },
    );
    if (r.ok) {
      sidCheckState = { status: "ok", sheetNames: r.sheet_names || [] };
      _setStatus(sidStatus, "ok", `✓ ${r.message}`);
      
      const fullUrl = `https://docs.google.com/spreadsheets/d/${sid}/edit`;
      if (sidLinkWrap && sidLinkInput) {
        sidLinkInput.value = fullUrl;
        sidLinkWrap.style.display = "block";
      }
      
    } else {
      sidCheckState = { status: "error", sheetNames: [] };
      _setStatus(sidStatus, "error", `✗ ${r.message}`);
    }
  } catch (e) {
    sidCheckState = { status: "error", sheetNames: [] };
    _setStatus(sidStatus, "error", "✗ Không kết nối được hoặc Spreadsheet ID sai");
  } finally {
    checkSidBtn.disabled = false;
  }
  updateRunBtn();
}

// ─── Check Sheet Name ──────────────────────────────────────────────────────

async function checkSheetName() {
  const sid   = fSid.value.trim();
  const sname = fSname.value.trim() || "Sheet1";
  const pid   = state.activeTab;
  if (sidCheckState.status !== "ok") { _setStatus(snameStatus, "error", "Kiểm tra Spreadsheet ID trước"); return; }
  if (!pid)  { _setStatus(snameStatus, "error", "Chưa chọn tài khoản"); return; }

  snameCheckState = { status: "checking" };
  _setStatus(snameStatus, "checking", "Đang kiểm tra Sheet name...");
  checkSnameBtn.disabled = true;
  const clearThumbStatus = document.querySelector("#clear-thumb-status");
  if (clearThumbStatus) clearThumbStatus.style.display = "none";
  updateRunBtn();

  try {
    const r = await callApi(
      `/utils/check-sheet?spreadsheet_id=${encodeURIComponent(sid)}&sheet_name=${encodeURIComponent(sname)}&profile_id=${encodeURIComponent(pid)}`,
      { timeoutMs: 20000, retries: 1 },
    );
    if (r.ok) {
      snameCheckState = { status: "ok" };
      _setStatus(snameStatus, "ok", `✓ ${r.message}`);
    } else if (r.running) {
      snameCheckState = { status: "error" };
      _setStatus(snameStatus, "error", `⚠ ${r.message}`);
    } else {
      snameCheckState = { status: "error" };
      _setStatus(snameStatus, "error", `✗ ${r.message}`);
    }
  } catch (e) {
    snameCheckState = { status: "error" };
    _setStatus(snameStatus, "error", "✗ Không kết nối được hoặc Sheet không tồn tại");
  } finally {
    checkSnameBtn.disabled = false;
  }
  updateRunBtn();
}

checkSidBtn?.addEventListener("click", checkSpreadsheetId);
checkSnameBtn?.addEventListener("click", checkSheetName);

// Reset status khi user thay doi gia tri
fSid.addEventListener("input", () => { resetSidStatus(); updateRunBtn(); });
fSname.addEventListener("input", () => { resetSnameStatus(); updateRunBtn(); });

// Export de tabs.js goi khi switch tab (reset status)
export function resetCheckStatuses() {
  sidCheckState   = { status: "idle", sheetNames: [] };
  snameCheckState = { status: "idle" };
  _setStatus(sidStatus,   "idle", "");
  _setStatus(snameStatus, "idle", "");
  const clearThumbStatus = document.querySelector("#clear-thumb-status");
  if (clearThumbStatus) clearThumbStatus.style.display = "none";
  if (sidLinkWrap) sidLinkWrap.style.display = "none";
}

export function updateRunBtn() {
  if (!state.activeTab) {
    runBtn.disabled = true;
    stopBtn.disabled = true;
    if (clearThumbBtn) { clearThumbBtn.disabled = true; clearThumbBtn.title = "Chưa chọn tài khoản"; }
    return;
  }
  const p             = state.profiles.find(x => x.id === state.activeTab);
  const st            = state.tabStates[state.activeTab] || {};
  const hasSid        = !!fSid.value.trim();
  
  // BẮT BUỘC phải kiểm tra và trả về "ok" thì mới được phép chạy
  const sidReady      = sidCheckState.status === "ok";
  const snameReady    = snameCheckState.status === "ok";
  
  const jobStatus     = getJobStatus(st.jobId);
  const isRunning     = ACTIVE_JOB_STATUSES.includes(jobStatus);
  const isStoppable   = STOPPABLE_JOB_STATUSES.includes(jobStatus);
  
  runBtn.disabled  = !p?.logged_in || !hasSid || !sidReady || !snameReady || isRunning;
  stopBtn.disabled = !isStoppable;
  
  if (!isRunning) {
    runBtn.title = (sidReady && snameReady) ? "" : "Vui lòng bấm 'Kiểm tra' cả Sheet ID và Sheet Name";
  }

  // Chỉ cho phép xóa thumbnail khi cả SID và Sheet Name đều đã kiểm tra OK
  if (clearThumbBtn) {
    const canClear = sidReady && snameReady && !!p?.logged_in;
    clearThumbBtn.disabled = !canClear;
    clearThumbBtn.title = canClear
      ? "Xóa toàn bộ dữ liệu cột thumbnail (trừ tiêu đề)"
      : "Cần kiểm tra Spreadsheet ID và Sheet Name trước";
  }
}

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
        thumb_quality: 2, thumb_width: 1280, profile_id: runProfileId,
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

// ─── Clear Thumbnail Column ──────────────────────────────────────────────────

const clearThumbBtn    = document.querySelector("#clear-thumb-btn");
const clearThumbStatus = document.querySelector("#clear-thumb-status");

function _setClearStatus(type, msg) {
  if (!clearThumbStatus) return;
  if (!msg) { clearThumbStatus.style.display = "none"; return; }
  clearThumbStatus.style.display = "inline";
  clearThumbStatus.className = "field-status" +
    (type === "ok" ? " ok" : type === "error" ? " error" : type === "checking" ? " checking" : "");
  clearThumbStatus.textContent = msg;
}

clearThumbBtn?.addEventListener("click", async () => {
  const pid   = state.activeTab;
  const sid   = fSid.value.trim();
  const sname = fSname.value.trim() || "Sheet1";
  const tcol  = parseInt(document.querySelector("#f-tcol")?.value ?? "14", 10);

  if (!pid)  { _setClearStatus("error", "Chưa chọn tài khoản"); return; }
  if (!sid)  { _setClearStatus("error", "Chưa nhập Spreadsheet ID"); return; }
  if (sidCheckState.status !== "ok")   { _setClearStatus("error", "Cần kiểm tra Spreadsheet ID trước"); return; }
  if (snameCheckState.status !== "ok") { _setClearStatus("error", "Cần kiểm tra Sheet Name trước"); return; }

  if (!confirm(`Xóa toàn bộ dữ liệu cột Thumbnail (cột ${tcol}) trong sheet "${sname}"?\nDòng tiêu đề sẽ được giữ lại.`)) return;

  clearThumbBtn.disabled = true;
  _setClearStatus("checking", "Đang xóa...");

  try {
    const r = await callApi("/utils/clear-thumb-col", {
      method: "POST",
      timeoutMs: 30000,
      body: JSON.stringify({
        spreadsheet_id: sid,
        sheet_name: sname,
        thumb_col: tcol,
        profile_id: pid,
      }),
    });
    if (r.ok) {
      _setClearStatus("ok", `✓ ${r.message}`);
    } else {
      _setClearStatus("error", `✗ ${r.message || "Xóa thất bại"}`);
    }
  } catch (e) {
    _setClearStatus("error", "✗ " + e.message);
  } finally {
    clearThumbBtn.disabled = false;
  }
});
