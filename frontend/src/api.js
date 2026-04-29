// frontend/src/api.js — API client
export const API_BASE = "http://127.0.0.1:8765";

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function callApi(path, options = {}) {
  const headers = options.body ? { "Content-Type": "application/json" } : {};
  const timeoutMs = options.timeoutMs ?? 30000;
  const retries = options.retries ?? 0;
  const fetchOptions = { ...options };
  delete fetchOptions.timeoutMs;
  delete fetchOptions.retries;
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${API_BASE}${path}`, { headers, ...fetchOptions, signal: controller.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      return res.json();
    } catch (error) {
      lastError = error;
      if (attempt === retries) break;
      await sleep(600 * (attempt + 1));
    } finally {
      clearTimeout(timeout);
    }
  }
  if (lastError?.name === "AbortError") throw new Error("Backend khong phan hoi kip thoi");
  if (lastError?.message?.startsWith("HTTP ")) throw lastError;
  throw new Error("Khong ket noi duoc backend");
}
