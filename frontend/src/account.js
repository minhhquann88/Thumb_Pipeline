// frontend/src/account.js — Account card rendering, login/logout/delete handlers

import { acctAvatar, acctName, acctEmail, acctLoginBtn, acctLogoutBtn, acctDeleteBtn } from "./dom.js";
import * as state from "./state.js";
import { callApi } from "./api.js";
import { printLog } from "./log.js";
import { loadProfiles } from "./profiles.js";
import { switchTab } from "./tabs.js";

let _updateRunBtn = null;
export function setUpdateRunBtnRef(fn) { _updateRunBtn = fn; }

export function renderAccountCard() {
  if (!state.activeTab) return;
  const p = state.profiles.find(x => x.id === state.activeTab);
  if (!p) return;
  const letter = (p.email || p.name || "?")[0].toUpperCase();
  acctAvatar.textContent   = letter;
  acctAvatar.className     = "acct-avatar-lg" + (p.logged_in ? "" : " offline");
  acctName.textContent     = p.name;
  acctEmail.textContent    = p.logged_in ? (p.email || "Đã đăng nhập") : "Chưa đăng nhập";
  acctLoginBtn.textContent = p.logged_in ? "Đổi tài khoản" : "Đăng nhập";
  acctLogoutBtn.style.display = p.logged_in ? "" : "none";
}

// ─── Event listeners ──────────────────────────────────────────────────────

acctLoginBtn.addEventListener("click", async () => {
  if (!state.activeTab) return;
  try {
    const data = await callApi(`/profiles/${state.activeTab}/login`, { method: "POST" });
    printLog(data.message + "\nApp sẽ tự cập nhật sau khi đăng nhập xong.");
    const pid = state.activeTab;
    const timer = setInterval(async () => {
      try {
        const info = await callApi(`/profiles/${pid}`);
        if (info.logged_in) {
          clearInterval(timer);
          await loadProfiles();
          // Làm mới account card + run button
          if (state.activeTab === pid) {
            renderAccountCard();
            if (_updateRunBtn) _updateRunBtn();
          }
          printLog("✅ Đăng nhập thành công: " + (info.email || info.name || "OK"));
        }
      } catch {}
    }, 3000);
  } catch (e) { printLog("Lỗi đăng nhập: " + e.message); }
});

acctLogoutBtn.addEventListener("click", async () => {
  if (!state.activeTab || !confirm("Đăng xuất khỏi tài khoản này?")) return;
  try {
    await callApi(`/profiles/${state.activeTab}/logout`, { method: "PATCH" });
    await loadProfiles();
    renderAccountCard();   // cập nhật card ngay lập tức
    if (_updateRunBtn) _updateRunBtn();
  } catch (e) { printLog("Lỗi đăng xuất: " + e.message); }
});

acctDeleteBtn.addEventListener("click", async () => {
  if (!state.activeTab || !confirm("Xóa tài khoản này? Hành động không thể hoàn tác.")) return;
  try {
    await callApi(`/profiles/${state.activeTab}`, { method: "DELETE" });
    delete state.tabStates[state.activeTab];
    state.setActiveTab(null);
    await loadProfiles();
    if (state.profiles.length > 0) switchTab(state.profiles[0].id);
  } catch (e) { printLog("Lỗi xóa: " + e.message); }
});
