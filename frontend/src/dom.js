// frontend/src/dom.js — All DOM element references (single source of truth)

// ─── Topbar / layout ──────────────────────────────────────────────────────
export const backendBadge    = document.querySelector("#backend-badge");
export const backendLabel    = document.querySelector("#backend-label");
export const acctTabbar      = document.querySelector("#acct-tabbar");
export const emptyState      = document.querySelector("#empty-state");
export const workspace       = document.querySelector("#workspace");

// ─── Account card ─────────────────────────────────────────────────────────
export const acctAvatar      = document.querySelector("#acct-avatar");
export const acctName        = document.querySelector("#acct-name");
export const acctEmail       = document.querySelector("#acct-email");
export const acctLoginBtn    = document.querySelector("#acct-login-btn");
export const acctLogoutBtn   = document.querySelector("#acct-logout-btn");
export const acctDeleteBtn   = document.querySelector("#acct-delete-btn");

// ─── Pipeline form ────────────────────────────────────────────────────────
export const fSid            = document.querySelector("#f-sid");
export const fSname          = document.querySelector("#f-sname");
export const fFolder         = document.querySelector("#f-folder");
export const fVcol           = document.querySelector("#f-vcol");
export const fTcol           = document.querySelector("#f-tcol");
export const fTs             = document.querySelector("#f-ts");
export const sheetStatus     = document.querySelector("#sheet-status");   // legacy, giữ để không vỡ code cũ
export const sidStatus       = document.querySelector("#sid-status");     // inline dưới Spreadsheet ID
export const sidLinkWrap     = document.querySelector("#sid-link-wrap");
export const sidLinkInput    = document.querySelector("#sid-link-input");
export const snameStatus     = document.querySelector("#sname-status");
export const checkSidBtn     = document.querySelector("#check-sid-btn");
export const checkSnameBtn   = document.querySelector("#check-sname-btn");

// ─── Run / Stop / Log ─────────────────────────────────────────────────────
export const runBtn          = document.querySelector("#run-btn");
export const stopBtn         = document.querySelector("#stop-btn");
export const logTitle        = document.querySelector("#log-title");
export const statusPill      = document.querySelector("#status-pill");
export const outputWrap      = document.querySelector("#output-wrap");
export const output          = document.querySelector("#output");
export const scrollBottomBtn = document.querySelector("#scroll-bottom-btn");
