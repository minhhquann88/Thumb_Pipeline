// frontend/src/profiles.js — Profile loading & adding

import { callApi } from "./api.js";
import * as state from "./state.js";
import { renderTabs, updateLayout, switchTab } from "./tabs.js";

export async function loadProfiles() {
  try {
    const data = await callApi("/profiles");
    state.setProfiles(data.profiles || []);
    // Init tab states for new profiles
    for (const p of state.profiles) {
      if (!state.tabStates[p.id]) state.tabStates[p.id] = { ...state.DEFAULT_SETTINGS };
    }
    renderTabs();
    updateLayout();
  } catch (e) {
    console.error("loadProfiles:", e);
  }
}

export async function addAccount() {
  const name = prompt("Tên tài khoản (ví dụ: TK Công ty):") || "";
  if (!name.trim()) return;
  const shouldSelectNewProfile = !state.activeTab;
  try {
    const profile = await callApi("/profiles", {
      method: "POST",
      body: JSON.stringify({ name: name.trim() }),
    });
    state.tabStates[profile.id] = { ...state.DEFAULT_SETTINGS };
    await loadProfiles();
    switchTab(profile.id);
  } catch (e) { alert("Lỗi: " + e.message); }
}

// ─── Event listeners ──────────────────────────────────────────────────────
document.querySelector("#add-account-btn").addEventListener("click", addAccount);
document.querySelector("#add-account-empty-btn").addEventListener("click", addAccount);
