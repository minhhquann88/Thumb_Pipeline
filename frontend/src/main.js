/**
 * frontend/src/main.js — App entry point.
 *
 * Chỉ làm 3 việc:
 *   1. Import tất cả side-effect modules (event listeners tự đăng ký).
 *   2. Wire các hàm cross-module (tránh circular import).
 *   3. Khởi tạo app: load profiles + bắt đầu polling + check backend.
 */

// ── Side-effect modules (tự đăng ký event listeners khi import) ──────────────
import "./resizer.js";
import "./profiles.js";
import "./account.js";
import "./jobs.js";
import "./log.js";

// ── Logic modules ─────────────────────────────────────────────────────────────
import { callApi }             from "./api.js";
import { backendBadge, backendLabel } from "./dom.js";
import { loadProfiles }        from "./profiles.js";
import { startPolling }        from "./polling.js";
import { switchTab }           from "./tabs.js";
import { updateRunBtn }        from "./jobs.js";
import { renderAccountCard }   from "./account.js";

// ── Wire cross-module callbacks (phá vòng tròn import) ────────────────────────
import { setUpdateRunBtnFn, setRenderAccountCardFn } from "./tabs.js";
import { setUpdateRunBtnRef }                        from "./account.js";
import { setPollingUpdateRunBtn }                    from "./polling.js";
import * as state from "./state.js";

setUpdateRunBtnFn(updateRunBtn);
setRenderAccountCardFn(renderAccountCard);
setUpdateRunBtnRef(updateRunBtn);
setPollingUpdateRunBtn(updateRunBtn);

const reloadBeBtn = document.querySelector("#reload-be-btn");

async function checkBackend() {
  try {
    const data = await callApi("/health");
    const ok = data.status === "ok";
    backendBadge.className   = "badge " + (ok ? "online" : "error");
    backendLabel.textContent = ok ? "Backend ✓" : "Backend ✗";
    if (reloadBeBtn) reloadBeBtn.style.display = ok ? "none" : "";
  } catch {
    backendBadge.className   = "badge error";
    backendLabel.textContent = "Backend ✗";
    if (reloadBeBtn) reloadBeBtn.style.display = "";
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  await checkBackend();
  await loadProfiles();
  // Chọn tab đầu tiên nếu có
  if (state.profiles.length > 0) {
    switchTab(state.profiles[0].id);
  }
  startPolling();
})();

// ── Reload Backend button ────────────────────────────────────────────────────
if (reloadBeBtn) {
  reloadBeBtn.style.display = "none"; // ẩn mặc định, chỉ hiện khi BE lỗi
  reloadBeBtn.addEventListener("click", async () => {
    reloadBeBtn.disabled = true;
    reloadBeBtn.textContent = "Đang kết nối...";
    backendBadge.className   = "badge";
    backendLabel.textContent = "Đang kết nối...";
    try {
      if (window.__TAURI__) {
        await window.__TAURI__.core.invoke("restart_backend");
      }
    } catch (e) {
      console.warn("restart_backend invoke error:", e);
    }
    // Poll health tối đa 10s
    let retries = 0;
    const poll = async () => {
      retries++;
      await checkBackend();
      const isOk = backendBadge.className.includes("online");
      if (!isOk && retries < 20) {
        setTimeout(poll, 500);
      } else {
        reloadBeBtn.disabled = false;
        reloadBeBtn.textContent = "ReLoad";
        if (isOk) await loadProfiles();
      }
    };
    setTimeout(poll, 1000);
  });
}
