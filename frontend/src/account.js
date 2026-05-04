// frontend/src/account.js — Account card rendering, login/logout/delete handlers

import { acctAvatar, acctName, acctEmail, acctLoginBtn, acctLogoutBtn, acctDeleteBtn } from "./dom.js";
import * as state from "./state.js";
import { callApi } from "./api.js";
import { printLog } from "./log.js";
import { loadProfiles } from "./profiles.js";
import { switchTab } from "./tabs.js";

let _updateRunBtn = null;
export function setUpdateRunBtnRef(fn) { _updateRunBtn = fn; }

// Timer cho login polling — giữ ref de co the clear khi click lai
let _loginPollTimer = null;

export function renderAccountCard() {
  if (!state.activeTab) return;
  const p = state.profiles.find(x => x.id === state.activeTab);
  if (!p) return;
  const displayName = p.logged_in ? (p.google_name || p.email || "Đã đăng nhập") : "";
  const letter = (displayName || p.name || "?")[0].toUpperCase();
  acctAvatar.textContent   = letter;
  acctAvatar.className     = "acct-avatar-lg" + (p.logged_in ? "" : " offline");
  acctName.textContent     = displayName;
  acctEmail.textContent    = p.logged_in ? (p.email || "") : "Chưa đăng nhập";
  acctLoginBtn.textContent = p.logged_in ? "Đổi tài khoản" : "Đăng nhập";
  acctLogoutBtn.style.display = p.logged_in ? "" : "none";
}

// ─── Event listeners ──────────────────────────────────────────────────────

acctLoginBtn.addEventListener("click", async () => {
  if (!state.activeTab) return;
  try {
    const data = await callApi(`/profiles/${state.activeTab}/login`, { method: "POST" });
    
    if (data.auth_url) {
      const overlay = document.createElement("div");
      overlay.style.position = "fixed";
      overlay.style.top = "0"; overlay.style.left = "0";
      overlay.style.width = "100vw"; overlay.style.height = "100vh";
      overlay.style.backgroundColor = "rgba(0,0,0,0.6)";
      overlay.style.zIndex = "9999";
      overlay.style.display = "flex";
      overlay.style.alignItems = "center";
      overlay.style.justifyContent = "center";
      
      const box = document.createElement("div");
      box.style.background = "var(--bg, #fff)";
      box.style.padding = "20px";
      box.style.borderRadius = "8px";
      box.style.width = "400px";
      box.style.maxWidth = "90%";
      box.style.boxShadow = "0 4px 12px rgba(0,0,0,0.15)";
      box.style.color = "var(--text, #333)";
      
      box.innerHTML = `
        <h3 style="margin-top:0">Đăng nhập tài khoản</h3>
        <p style="font-size:13px; color:var(--muted, #666); line-height:1.4">Hãy copy đường dẫn dưới đây và dán vào trình duyệt bạn muốn để đăng nhập. Sau khi cấp quyền xong trên trình duyệt, thông tin tại đây sẽ tự động cập nhật.</p>
        <textarea readonly style="width:100%; height:90px; margin-top:12px; padding:8px; font-family:monospace; font-size:11px; border-radius:5px; border:1px solid #ccc; outline:none; resize:none; background:#f9f9f9; color:#000" onclick="this.select()">${data.auth_url}</textarea>
        <div style="margin-top:15px; text-align:right">
          <button class="btn btn-sm btn-ghost" id="close-dialog-btn" style="margin-right:8px">Đóng</button>
          <button class="btn btn-sm btn-primary" id="copy-dialog-btn">Copy & Đóng</button>
        </div>
      `;
      overlay.appendChild(box);
      document.body.appendChild(overlay);
      
      const copyBtn = box.querySelector("#copy-dialog-btn");
      const closeBtn = box.querySelector("#close-dialog-btn");
      const textarea = box.querySelector("textarea");
      
      copyBtn.onclick = () => {
        textarea.select();
        document.execCommand('copy');
        try { navigator.clipboard.writeText(data.auth_url); } catch(e){}
        document.body.removeChild(overlay);
      };
      closeBtn.onclick = () => {
        document.body.removeChild(overlay);
      };
    }

    const pid = state.activeTab;

    // Huy timer cu neu nguoi dung click Dang nhap nhieu lan
    if (_loginPollTimer) { clearTimeout(_loginPollTimer); _loginPollTimer = null; }

    let retries = 0;
    const MAX_RETRIES = 180; // ~4.5 phut
    
    async function pollLogin() {
      retries++;
      if (retries > MAX_RETRIES) {
        _loginPollTimer = null;
        printLog("⏰ Het thoi gian cho dang nhap. Vui long thu lai.");
        return;
      }
      try {
        const info = await callApi(`/profiles/${pid}`);
        if (info.logged_in) {
          _loginPollTimer = null;
          await loadProfiles();
          if (state.activeTab === pid) {
            renderAccountCard();
            if (_updateRunBtn) _updateRunBtn();
          }
          printLog("✅ Dang nhap thanh cong: " + (info.email || info.name || "OK"));
          return;
        }
      } catch { /* bo qua loi mang tam thoi */ }
      
      _loginPollTimer = setTimeout(pollLogin, 1500);
    }
    
    _loginPollTimer = setTimeout(pollLogin, 1500);
  } catch (e) { printLog("Loi dang nhap: " + e.message); }
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
