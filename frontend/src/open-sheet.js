// frontend/src/open-sheet.js — Open Google Sheet in browser

import { callApi } from "./api.js";
import { fSid, openSheetBtn } from "./dom.js";

openSheetBtn.addEventListener("click", async () => {
  const id = fSid.value.trim();
  if (!id) return;
  const url = `https://docs.google.com/spreadsheets/d/${id}`;
  try { await callApi("/utils/open-url", { method: "POST", body: JSON.stringify({ url }) }); }
  catch { window.open(url, "_blank"); }
});
