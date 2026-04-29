// frontend/src/state.js — Shared application state

export let profiles   = [];          // ProfileInfo[] from backend
export let tabStates  = {};          // pid → { spreadsheetId, sheetName, driveFolder, videoUrlCol, thumbCol, timestamps, jobId }
export let activeTab  = null;        // currently selected profile id
export let pollTimer  = null;
export let jobsCache  = {};          // jobId → JobSnapshot
export let sheetValidation = { status: "idle", message: "" };

export const DEFAULT_SETTINGS = {
  spreadsheetId: "",
  sheetName:     "Sheet1",
  driveFolder:   "thumbnails",
  videoUrlCol:   3,
  thumbCol:      14,
  timestamps:    "3,8,13,18,23",
  jobId:         null,
};

// Setter helpers (needed because ES modules export bindings are read-only from importers)
export function setProfiles(v)  { profiles  = v; }
export function setActiveTab(v) { activeTab = v; }
export function setPollTimer(v) { pollTimer = v; }
export function setSheetValidation(v) { sheetValidation = v; }
