export const $ = (id) => document.getElementById(id);

// ── Lightweight markdown renderer (no external deps) ─────────
export function renderMarkdown(raw) {
  if (!raw) return "";
  // Escape HTML first to prevent XSS
  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  let text = raw;

  // Fenced code blocks (``` lang\n...\n```)
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m, lang, code) => {
    const langAttr = lang ? ` data-lang="${esc(lang)}"` : "";
    return `<pre${langAttr}><code>${esc(code.trim())}</code></pre>`;
  });

  // Process lines (for non-code content)
  const lines = text.split("\n");
  const out = [];
  let inPre = false;
  let listBuf = [];

  const flushList = () => {
    if (listBuf.length) {
      out.push(`<ul>${listBuf.map((l) => `<li>${l}</li>`).join("")}</ul>`);
      listBuf = [];
    }
  };

  for (const line of lines) {
    if (line.startsWith("<pre")) { inPre = true; }
    if (inPre) { out.push(line); if (line.includes("</pre>")) inPre = false; continue; }

    // Bullet list
    const bulletMatch = line.match(/^[ \t]*[-*•]\s+(.*)/);
    if (bulletMatch) {
      listBuf.push(inlineMarkdown(esc(bulletMatch[1])));
      continue;
    }
    flushList();

    // Headings
    const h3 = line.match(/^### (.*)/);
    if (h3) { out.push(`<strong>${inlineMarkdown(esc(h3[1]))}</strong>`); continue; }
    const h2 = line.match(/^## (.*)/);
    if (h2) { out.push(`<strong>${inlineMarkdown(esc(h2[1]))}</strong>`); continue; }
    const h1 = line.match(/^# (.*)/);
    if (h1) { out.push(`<strong>${inlineMarkdown(esc(h1[1]))}</strong>`); continue; }

    // Blank line → separator
    if (!line.trim()) { out.push("<br/>"); continue; }

    out.push(`<span>${inlineMarkdown(esc(line))}</span>`);
  }
  flushList();
  return out.join("\n");
}

function inlineMarkdown(s) {
  // Bold **text**
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic *text*
  s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Inline code `code`
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Links [text](url)
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );
  return s;
}

// ── Add a streaming cursor to a message element ───────────────
export function addCursor(msgEl) {
  if (!msgEl) return;
  const cursor = document.createElement("span");
  cursor.className = "cursor-blink";
  msgEl.appendChild(cursor);
  return cursor;
}

export function removeCursor(msgEl) {
  if (!msgEl) return;
  const c = msgEl.querySelector(".cursor-blink");
  if (c) c.remove();
}

// ── Finalize AI message: render markdown + add copy button ────
export function finalizeMsg(wrapEl, rawText, qualityScore = null) {
  if (!wrapEl) return;
  const msgEl = wrapEl.querySelector(".msg.ai");
  if (!msgEl) return;

  removeCursor(msgEl);
  msgEl.innerHTML = renderMarkdown(rawText);

  // Quality tint
  if (qualityScore !== null) {
    msgEl.classList.remove("quality-high", "quality-mid", "quality-low");
    if (qualityScore >= 0.75) msgEl.classList.add("quality-high");
    else if (qualityScore >= 0.45) msgEl.classList.add("quality-mid");
    else msgEl.classList.add("quality-low");
  }

  // Actions row
  let actionsEl = wrapEl.querySelector(".msg-actions");
  if (!actionsEl) {
    actionsEl = document.createElement("div");
    actionsEl.className = "msg-actions";
    wrapEl.appendChild(actionsEl);
  }
  actionsEl.innerHTML = "";

  const copyBtn = document.createElement("button");
  copyBtn.className = "btn-copy";
  copyBtn.textContent = "Copiar";
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(rawText).then(() => {
      copyBtn.textContent = "✓ Copiado";
      setTimeout(() => { copyBtn.textContent = "Copiar"; }, 1800);
    });
  });
  actionsEl.appendChild(copyBtn);
}

export const state = {
  token: "",
  profile: null,
  models: [],
  activeModel: localStorage.getItem("abliterador.activeModel") || "",
  roleCatalog: {},
  selectedFilePath: "",
  filesCache: [],
  modelsCacheUntil: 0,
  perfMode: localStorage.getItem("abliterador.perfMode") || "balanced",
  isGenerating: false,
  chatAbortController: null,
  chatTimeoutByPerf: {
    eco: 120,
    balanced: 90,
    fast: 60,
  },
};

export const PERF = {
  eco: { modelTtlMs: 90_000, pullPollMs: 2400 },
  balanced: { modelTtlMs: 35_000, pullPollMs: 1500 },
  fast: { modelTtlMs: 15_000, pullPollMs: 900 },
};

export const el = {
  log: $("log"),
  statusStrip: $("statusStrip"),
  spinner: $("spinner"),
  progressText: $("progressText"),
  connBadge: $("connBadge"),
  chatPerfBadge: $("chatPerfBadge"),
  chatEmptyState: $("chatEmptyState"),
  chatModelBadge: $("chatModelBadge"),
  activeModelBadge: $("activeModelBadge"),
  modelSelectMain: $("modelSelectMain"),
  btnModels: $("btnModels"),
  btnRefreshModelsChat: $("btnRefreshModelsChat"),

  username: $("username"),
  password: $("password"),
  btnLogin: $("btnLogin"),
  profileInfo: $("profileInfo"),
  signupUser: $("signupUser"),
  signupPass: $("signupPass"),
  btnSignup: $("btnSignup"),
  perfMode: $("perfMode"),

  prompt: $("prompt"),
  btnSend: $("btnSend"),
  btnCancel: $("btnCancel"),
  useQualityCheck: $("useQualityCheck"),
  useToolsChat: $("useToolsChat"),
  useWebSearchChat: $("useWebSearchChat"),
  useWebKnowledgeChat: $("useWebKnowledgeChat"),
  webQueryChat: $("webQueryChat"),
  webResultsLimitChat: $("webResultsLimitChat"),

  fileListStatus: $("fileListStatus"),
  fileList: $("fileList"),
  searchFiles: $("searchFiles"),
  btnSearchFiles: $("btnSearchFiles"),
  btnNewFolder: $("btnNewFolder"),
  uploadTargetPath: $("uploadTargetPath"),
  uploadFileInput: $("uploadFileInput"),
  btnUploadFile: $("btnUploadFile"),
  btnDownloadSelected: $("btnDownloadSelected"),
  transferQueue: $("transferQueue"),

  adminBlock: $("adminBlock"),
  adminHint: $("adminHint"),
  newUser: $("newUser"),
  newPass: $("newPass"),
  newRole: $("newRole"),
  btnCreateUser: $("btnCreateUser"),
  btnRefreshUsers: $("btnRefreshUsers"),
  userCatalog: $("userCatalog"),
  editRole: $("editRole"),
  editActive: $("editActive"),
  btnApplyUserEdit: $("btnApplyUserEdit"),
  btnDeleteUser: $("btnDeleteUser"),
  pullModelName: $("pullModelName"),
  btnPullModel: $("btnPullModel"),
  pullStatus: $("pullStatus"),
  downloadCatalog: $("downloadCatalog"),
  btnRefreshDownloadCatalog: $("btnRefreshDownloadCatalog"),
  btnLaunchGui: $("btnLaunchGui"),

  btnSelfHealCheck: $("btnSelfHealCheck"),
  btnSelfHealRun: $("btnSelfHealRun"),
  btnAiDiagCheck: $("btnAiDiagCheck"),
  btnAiDiagRun: $("btnAiDiagRun"),
  aiDiagStatus: $("aiDiagStatus"),
  webSearchQuery: $("webSearchQuery"),
  webSearchLimit: $("webSearchLimit"),
  btnWebSearch: $("btnWebSearch"),
  webSearchStatus: $("webSearchStatus"),

  tabs: Array.from(document.querySelectorAll(".tab")),
  panes: Array.from(document.querySelectorAll(".tab-pane")),
};

export function createMsg(role, text = "", meta = "") {
  if (!el.log) return;
  if (el.chatEmptyState) {
    el.chatEmptyState.style.display = "none";
  }

  const time = new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
  const wrap = document.createElement("div");
  wrap.className = `msg-wrap ${role}-wrap`;

  const metaEl = document.createElement("div");
  metaEl.className = "msg-meta";
  metaEl.textContent = time;
  wrap.appendChild(metaEl);

  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = meta ? `${meta}\n${text}` : text;
  wrap.appendChild(div);

  el.log.appendChild(wrap);
  el.log.scrollTop = el.log.scrollHeight;
  return div;
}

export function addMsg(role, text, meta = "") {
  createMsg(role, text, meta);
}

export function setStatus(text) {
  if (el.statusStrip) el.statusStrip.textContent = text;
}

export function setProgress(active, text = "Listo") {
  if (el.spinner) el.spinner.style.display = active ? "block" : "none";
  if (el.progressText) el.progressText.textContent = text;
}

export function parseApiError(data) {
  if (!data) return "Error de API";
  if (typeof data.detail === "string") return data.detail;
  if (data.detail && typeof data.detail === "object") {
    if (typeof data.detail.message === "string") {
      return data.detail.hint ? `${data.detail.message} | ${data.detail.hint}` : data.detail.message;
    }
    return JSON.stringify(data.detail);
  }
  return data.message || "Error de API";
}

export function setActiveTab(tabName) {
  el.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  el.panes.forEach((pane) => pane.classList.toggle("active", pane.dataset.pane === tabName));
}

export function getPerfCfg() {
  return PERF[state.perfMode] || PERF.balanced;
}

export function updateModelBadges() {
  const current = state.activeModel || "-";
  if (el.chatModelBadge) el.chatModelBadge.textContent = `Modelo: ${current}`;
  if (el.activeModelBadge) el.activeModelBadge.textContent = current === "-" ? "Sin modelo" : current;
}

export function setActiveModel(model, persist = true) {
  state.activeModel = model || "";
  if (persist) localStorage.setItem("abliterador.activeModel", state.activeModel);
  if (el.modelSelectMain && el.modelSelectMain.value !== state.activeModel) {
    el.modelSelectMain.value = state.activeModel;
  }
  updateModelBadges();
}

export async function apiRequest(path, method = "GET", body = null, isForm = false, requestOptions = {}) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!isForm && body !== null) headers["Content-Type"] = "application/json";

  const res = await fetch(path, {
    method,
    headers,
    body: body === null ? null : (isForm ? body : JSON.stringify(body)),
    signal: requestOptions.signal,
  });

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json().catch(() => ({})) : null;
  if (!res.ok) throw new Error(parseApiError(data || {}));
  return data;
}

export function appendTransferLog(text) {
  if (!el.transferQueue) return;
  const row = document.createElement("div");
  row.textContent = `${new Date().toLocaleTimeString()} - ${text}`;
  el.transferQueue.prepend(row);
}
