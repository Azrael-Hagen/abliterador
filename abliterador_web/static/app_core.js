export const $ = (id) => document.getElementById(id);

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
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = meta ? `${meta}\n${text}` : text;
  el.log.appendChild(div);
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
