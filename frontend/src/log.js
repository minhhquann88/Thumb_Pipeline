// frontend/src/log.js — Log display, auto-scroll, printLog

import { outputWrap, output, scrollBottomBtn, logTitle, statusPill } from "./dom.js";
import { activeTab, tabStates, jobsCache } from "./state.js";

let userScrolledUp = false;
let lastRenderedJobKey = "";

export function printLog(text) {
  lastRenderedJobKey = "";
  output.textContent = text;
  outputWrap.scrollTop = outputWrap.scrollHeight;
}

export function isAtBottom() {
  return outputWrap.scrollHeight - outputWrap.scrollTop - outputWrap.clientHeight <= 80;
}

export function renderJobStatus() {
  if (!activeTab) return;
  const jobId = tabStates[activeTab]?.jobId;
  if (!jobId || !jobsCache[jobId]) {
    lastRenderedJobKey = "";
    logTitle.textContent   = "Kết quả";
    statusPill.textContent = "";
    statusPill.className   = "status-pill";
    return;
  }

  const snap  = jobsCache[jobId];
  const renderKey = `${snap.id}:${snap.status}:${snap.updated_at}:${snap.logs?.length ?? 0}`;
  if (renderKey === lastRenderedJobKey) return;
  lastRenderedJobKey = renderKey;
  const statusMap = {
    cancelling: "Đang dừng",
    queued:    "Đang chờ",
    running:   "Đang chạy",
    succeeded: "Hoàn tất ✓",
    failed:    "Thất bại ✗",
    cancelled: "Đã dừng",
  };
  const clsMap = {
    cancelling: "pill-waiting",
    queued:    "pill-waiting",
    running:   "pill-running",
    succeeded: "pill-done",
    failed:    "pill-error",
    cancelled: "pill-offline",
  };

  // Null-safe: spreadsheet_id có thể undefined (backend cũ)
  const sheetLabel = snap.sheet_name
    || (snap.spreadsheet_id ? snap.spreadsheet_id.slice(0, 12) : "Sheet");

  logTitle.textContent   = sheetLabel;
  statusPill.textContent = statusMap[snap.status] ?? snap.status;
  statusPill.className   = `status-pill ${clsMap[snap.status] ?? ""}`;

  // Cập nhật log
  const atBottom = isAtBottom();
  const logText  = (snap.logs && snap.logs.length)
    ? snap.logs.join("\n")
    : (snap.status === "queued" ? "Đang chờ khởi động..." : "Đang load log...");
  const footer = snap.error
    ? `\n\n❌ Lỗi: ${snap.error}`
    : (snap.result ? `\n\n📊 Kết quả:\n${JSON.stringify(snap.result, null, 2)}` : "");

  output.textContent = logText + footer;
  if (atBottom) requestAnimationFrame(() => { outputWrap.scrollTop = outputWrap.scrollHeight; });
}

// ─── Event listeners ──────────────────────────────────────────────────────
outputWrap.addEventListener("scroll", () => {
  userScrolledUp = !isAtBottom();
  scrollBottomBtn.style.display = userScrolledUp ? "block" : "none";
});
scrollBottomBtn.addEventListener("click", () => {
  userScrolledUp = false;
  outputWrap.scrollTop = outputWrap.scrollHeight;
  scrollBottomBtn.style.display = "none";
});
