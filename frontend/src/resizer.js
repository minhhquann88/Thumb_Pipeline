// frontend/src/resizer.js — Drag-to-resize left pane

const resizer  = document.querySelector("#resizer");
const paneLeft = document.querySelector("#pane-left");
const STORAGE_KEY = "pane-left-width-v2";

const savedWidth = localStorage.getItem(STORAGE_KEY);
if (savedWidth) paneLeft.style.flexBasis = savedWidth;

let isResizing = false, startX = 0, startWidth = 0;

resizer.addEventListener("mousedown", e => {
  isResizing = true; startX = e.clientX;
  startWidth = paneLeft.getBoundingClientRect().width;
  resizer.classList.add("dragging");
  document.body.style.cursor = document.body.style.userSelect = "col-resize";
  e.preventDefault();
});
document.addEventListener("mousemove", e => {
  if (!isResizing) return;
  const w = Math.min(Math.max(startWidth + e.clientX - startX, 260), window.innerWidth * 0.65);
  paneLeft.style.flexBasis = w + "px";
});
document.addEventListener("mouseup", () => {
  if (!isResizing) return;
  isResizing = false;
  resizer.classList.remove("dragging");
  document.body.style.cursor = document.body.style.userSelect = "";
  localStorage.setItem(STORAGE_KEY, paneLeft.style.flexBasis);
});
