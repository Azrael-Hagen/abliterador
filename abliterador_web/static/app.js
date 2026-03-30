const $ = (id) => document.getElementById(id);

const state = {
  token: "",
  profile: null,
  models: [],
  activeModel: localStorage.getItem("abliterador.activeModel") || "",
  roleCatalog: {},
  selectedFilePath: "",
  filesCache: [],
  modelsCacheUntil: 0,
  perfMode: localStorage.getItem("abliterador.perfMode") || "balanced",
};

const PERF = {
  eco: { modelTtlMs: 90_000, pullPollMs: 2400 },
  balanced: { modelTtlMs: 35_000, pullPollMs: 1500 },
  fast: { modelTtlMs: 15_000, pullPollMs: 900 },
};

const el = {
  log: $("log"),
  statusStrip: $("statusStrip"),
  spinner: $("spinner"),
  progressText: $("progressText"),
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

function addMsg(role, text, meta = "") {
  if (!el.log) return;
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = meta ? `${meta}\n${text}` : text;
  el.log.appendChild(div);
  el.log.scrollTop = el.log.scrollHeight;
}

function setStatus(text) {
  if (el.statusStrip) el.statusStrip.textContent = text;
}

function setProgress(active, text = "Listo") {
  if (el.spinner) el.spinner.style.display = active ? "block" : "none";
  if (el.progressText) el.progressText.textContent = text;
}

function parseApiError(data) {
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

function setActiveTab(tabName) {
  el.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  el.panes.forEach((pane) => pane.classList.toggle("active", pane.dataset.pane === tabName));
}

function getPerfCfg() {
  return PERF[state.perfMode] || PERF.balanced;
}

function updateModelBadges() {
  const current = state.activeModel || "-";
  if (el.chatModelBadge) el.chatModelBadge.textContent = `Modelo: ${current}`;
  if (el.activeModelBadge) el.activeModelBadge.textContent = current === "-" ? "Sin modelo" : current;
}

function setActiveModel(model, persist = true) {
  state.activeModel = model || "";
  if (persist) localStorage.setItem("abliterador.activeModel", state.activeModel);
  if (el.modelSelectMain && el.modelSelectMain.value !== state.activeModel) {
    el.modelSelectMain.value = state.activeModel;
  }
  updateModelBadges();
}

async function apiRequest(path, method = "GET", body = null, isForm = false) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!isForm && body !== null) headers["Content-Type"] = "application/json";

  const res = await fetch(path, {
    method,
    headers,
    body: body === null ? null : (isForm ? body : JSON.stringify(body)),
  });

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json().catch(() => ({})) : null;
  if (!res.ok) throw new Error(parseApiError(data || {}));
  return data;
}

async function loadModels(force = false) {
  if (!state.token) return;
  const now = Date.now();
  if (!force && state.models.length > 0 && now < state.modelsCacheUntil) return;
  const data = await apiRequest("/api/models");
  state.models = Array.isArray(data.models) ? data.models : [];
  state.modelsCacheUntil = now + getPerfCfg().modelTtlMs;

  if (el.modelSelectMain) {
    el.modelSelectMain.innerHTML = "";
    state.models.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      el.modelSelectMain.appendChild(opt);
    });
  }

  if (!state.activeModel || !state.models.includes(state.activeModel)) {
    setActiveModel(state.models[0] || "", true);
  } else {
    setActiveModel(state.activeModel, false);
  }

  setStatus(`Modelos disponibles: ${state.models.length}`);
}

function appendTransferLog(text) {
  if (!el.transferQueue) return;
  const row = document.createElement("div");
  row.textContent = `${new Date().toLocaleTimeString()} - ${text}`;
  el.transferQueue.prepend(row);
}

function renderFileRows(rows) {
  if (!el.fileList || !el.fileListStatus) return;
  el.fileList.innerHTML = "";
  if (!rows.length) {
    el.fileListStatus.textContent = "Sin archivos en esta vista.";
    return;
  }
  el.fileListStatus.textContent = `${rows.length} elemento(s)`;
  rows.forEach((file) => {
    const item = document.createElement("div");
    item.className = `file-item ${file.is_dir ? "folder" : "file"}${state.selectedFilePath === file.path ? " selected" : ""}`;
    item.dataset.path = file.path;
    item.innerHTML = `
      <div class="file-icon">${file.is_dir ? "DIR" : "FILE"}</div>
      <div class="file-info">
        <span class="file-name">${file.name}</span>
        <span class="file-meta">${file.size_readable} | ${file.type}</span>
      </div>
      <div class="file-actions">
        <button data-action="preview" data-path="${file.path}">Ver</button>
        <button data-action="delete" data-path="${file.path}">Del</button>
      </div>
    `;
    el.fileList.appendChild(item);
  });
}

async function loadFileList() {
  if (!state.token || !el.fileListStatus) return;
  el.fileListStatus.textContent = "Cargando archivos...";
  const data = await apiRequest("/api/files/manager/list", "POST", { path: "", filter_type: null });
  state.filesCache = Array.isArray(data.files) ? data.files : [];
  renderFileRows(state.filesCache);
}

async function previewFile(path) {
  const data = await apiRequest("/api/files/manager/preview", "POST", { path });
  if (data.content) {
    addMsg("tool", data.content.substring(0, 800), `Preview: ${path}`);
  } else {
    addMsg("tool", data.reason || "Tipo no soportado para preview", `Preview: ${path}`);
  }
}

async function deleteFile(path) {
  if (!window.confirm(`Eliminar ${path}?`)) return;
  await apiRequest("/api/files/manager/delete", "POST", { path });
  appendTransferLog(`Eliminado: ${path}`);
  if (state.selectedFilePath === path) state.selectedFilePath = "";
  await loadFileList();
}

async function createFolder() {
  const folderName = window.prompt("Nombre de la carpeta:");
  if (!folderName) return;
  const data = await apiRequest("/api/files/manager/mkdir", "POST", { path: folderName });
  appendTransferLog(`Carpeta creada: ${data.path}`);
  await loadFileList();
}

async function uploadSelectedFile() {
  const file = el.uploadFileInput?.files?.[0];
  if (!file) {
    addMsg("tool", "Selecciona un archivo para subir.");
    return;
  }
  const form = new FormData();
  form.append("file", file);
  form.append("path", (el.uploadTargetPath?.value || "").trim());
  const data = await apiRequest("/api/files/manager/upload", "POST", form, true);
  appendTransferLog(`Subido: ${data.path} (${data.size_bytes} bytes)`);
  await loadFileList();
}

async function downloadSelectedFile() {
  if (!state.selectedFilePath) {
    addMsg("tool", "Selecciona un archivo primero.");
    return;
  }
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const url = `/api/files/manager/download?path=${encodeURIComponent(state.selectedFilePath)}`;
  const res = await fetch(url, { method: "GET", headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(parseApiError(data));
  }
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = state.selectedFilePath.split("/").pop() || "archivo";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
  appendTransferLog(`Descargado: ${state.selectedFilePath}`);
}

async function searchFiles() {
  const query = (el.searchFiles?.value || "").trim().toLowerCase();
  if (!query) {
    renderFileRows(state.filesCache);
    return;
  }
  const localMatches = state.filesCache.filter((f) => f.name.toLowerCase().includes(query));
  if (localMatches.length > 0) {
    renderFileRows(localMatches);
    return;
  }
  const data = await apiRequest("/api/files/manager/search", "POST", { query, limit: 50 });
  renderFileRows(data.results || []);
}

async function loadProfile() {
  const data = await apiRequest("/api/me");
  state.profile = data;
  if (el.profileInfo) {
    el.profileInfo.textContent = `Perfil: ${data.username} (${data.role}) | Activo: ${data.active} | Espacio: ${data.workspace}`;
  }
  if (el.adminBlock) el.adminBlock.style.display = data.role === "admin" ? "block" : "none";
  if (el.adminHint) el.adminHint.style.display = data.role === "admin" ? "none" : "block";
  setStatus(`Sesion activa: ${data.username} (${data.role})`);
}

async function loadUsersCatalog() {
  if (!el.userCatalog) return;
  const users = await apiRequest("/api/users");
  el.userCatalog.innerHTML = "";
  users.forEach((u) => {
    const opt = document.createElement("option");
    opt.value = u.username;
    opt.dataset.role = u.role;
    opt.dataset.active = u.active ? "1" : "0";
    opt.textContent = `${u.username} | ${u.role} | ${u.active ? "activo" : "inactivo"}`;
    el.userCatalog.appendChild(opt);
  });
  syncUserEditor();
}

function syncUserEditor() {
  if (!el.userCatalog || el.userCatalog.selectedIndex < 0) return;
  const current = el.userCatalog.options[el.userCatalog.selectedIndex];
  if (el.editRole) el.editRole.value = current.dataset.role || "viewer";
  if (el.editActive) el.editActive.checked = (current.dataset.active || "1") === "1";
}

async function pullModel(model) {
  const job = await apiRequest("/api/admin/models/pull", "POST", { model });
  if (el.pullStatus) el.pullStatus.textContent = `Job ${job.job_id}: ${job.status}`;
  appendTransferLog(`Descarga de modelo iniciada: ${model}`);
  const pollMs = getPerfCfg().pullPollMs;
  while (true) {
    await new Promise((resolve) => setTimeout(resolve, pollMs));
    const st = await apiRequest(`/api/admin/models/pull/${job.job_id}`);
    if (el.pullStatus) el.pullStatus.textContent = `Job ${st.job_id}: ${st.status}`;
    if (st.status === "done" || st.status === "failed") {
      addMsg("tool", `Modelo ${st.model}: ${st.status}`);
      if (st.output_tail) addMsg("tool", st.output_tail);
      await loadModels(true);
      await loadDownloadCatalog();
      break;
    }
  }
}

function renderDownloadCatalog(rows) {
  if (!el.downloadCatalog) return;
  el.downloadCatalog.innerHTML = "";
  rows.forEach((item) => {
    const card = document.createElement("div");
    card.className = "download-item";
    card.innerHTML = `
      <div class="download-head">
        <strong>${item.name}</strong>
        <button ${item.installed ? "disabled" : ""} data-action="pull-catalog" data-model="${item.name}">${item.installed ? "Instalado" : "Descargar"}</button>
      </div>
      <div class="download-meta">${item.description || ""} | ${item.category || "general"} | ${item.size_hint || "-"}</div>
    `;
    el.downloadCatalog.appendChild(card);
  });
}

async function loadDownloadCatalog() {
  if (!state.token || !el.downloadCatalog || !state.profile || state.profile.role !== "admin") return;
  const data = await apiRequest("/api/models/download-catalog");
  renderDownloadCatalog(data.models || []);
}

async function sendChat() {
  const message = (el.prompt?.value || "").trim();
  if (!message) return;
  if (!state.activeModel) {
    addMsg("tool", "Selecciona un modelo global primero.");
    return;
  }

  addMsg("user", message);
  if (el.prompt) el.prompt.value = "";

  setProgress(true, "Preparando solicitud...");
  setStatus("Chat: preparando");

  const endpoint = el.useQualityCheck?.checked ? "/api/chat/quality" : "/api/chat";
  const payload = {
    model: state.activeModel,
    message,
    use_file_tools: Boolean(el.useToolsChat?.checked),
    use_web_search: Boolean(el.useWebSearchChat?.checked),
    web_query: (el.webQueryChat?.value || "").trim(),
    web_results_limit: Number(el.webResultsLimitChat?.value || 3),
    use_recent_web_knowledge: Boolean(el.useWebKnowledgeChat?.checked),
  };

  try {
    if (payload.use_web_search) {
      setProgress(true, "Enriqueciendo contexto web...");
    }
    setProgress(true, "Generando respuesta...");
    const data = await apiRequest(endpoint, "POST", payload);
    setProgress(true, "Validando coherencia...");

    if (Array.isArray(data.tool_events)) {
      data.tool_events.forEach((event) => {
        if (event.includes("quality")) addMsg("tool", event, "[QA]");
        else if (event.includes("web")) addMsg("tool", event, "[WEB]");
        else addMsg("tool", event);
      });
    }

    const modelUsed = data.model_used || state.activeModel;
    addMsg("ai", data.reply || "(sin respuesta)", `Modelo usado: ${modelUsed}`);
    setActiveModel(modelUsed, true);
    setStatus("Chat listo");
  } catch (err) {
    addMsg("tool", `Chat error: ${err.message}`);
    setStatus("Error en chat");
  } finally {
    setProgress(false, "Listo");
  }
}

async function loadServerInfo() {
  const data = await apiRequest("/api/server-info");
  const serverUrls = $("serverUrls");
  const ftpUrls = $("ftpUrls");

  if (serverUrls) {
    serverUrls.innerHTML = "";
    (data.urls || []).forEach((url) => {
      const li = document.createElement("li");
      li.textContent = url;
      serverUrls.appendChild(li);
    });
  }
  if (ftpUrls) {
    ftpUrls.innerHTML = "";
    ((data.ftp || {}).urls || []).forEach((url) => {
      const li = document.createElement("li");
      li.textContent = url;
      ftpUrls.appendChild(li);
    });
  }
}

function bindEvents() {
  el.tabs.forEach((tab) => {
    tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
  });

  el.perfMode?.addEventListener("change", () => {
    state.perfMode = el.perfMode.value;
    localStorage.setItem("abliterador.perfMode", state.perfMode);
    addMsg("tool", `Modo de rendimiento: ${state.perfMode}`);
  });

  el.modelSelectMain?.addEventListener("change", () => setActiveModel(el.modelSelectMain.value, true));
  el.btnModels?.addEventListener("click", async () => {
    try {
      await loadModels(true);
      addMsg("tool", `Modelos cargados: ${state.models.length}`);
    } catch (err) {
      addMsg("tool", `Modelos error: ${err.message}`);
    }
  });

  el.btnRefreshModelsChat?.addEventListener("click", async () => {
    try {
      await loadModels(true);
      await loadFileList();
      addMsg("tool", "UI sincronizada (modelos + archivos)");
    } catch (err) {
      addMsg("tool", `Sync error: ${err.message}`);
    }
  });

  el.btnLogin?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/login", "POST", {
        username: (el.username?.value || "").trim(),
        password: el.password?.value || "",
      });
      state.token = data.token;
      addMsg("tool", "Autenticado correctamente.");
      await loadProfile();
      await loadServerInfo();
      await loadModels(true);
      await loadFileList();
      if (state.profile?.role === "admin") {
        await loadUsersCatalog();
        await loadDownloadCatalog();
      }
    } catch (err) {
      addMsg("tool", `Login error: ${err.message}`);
      setStatus("Error de autenticacion");
    }
  });

  el.btnSignup?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/signup", "POST", {
        username: (el.signupUser?.value || "").trim(),
        password: el.signupPass?.value || "",
      });
      addMsg("tool", `Registro OK: ${data.username} (${data.role})`);
      if (el.signupUser) el.signupUser.value = "";
      if (el.signupPass) el.signupPass.value = "";
    } catch (err) {
      addMsg("tool", `Registro error: ${err.message}`);
    }
  });

  el.btnSend?.addEventListener("click", sendChat);

  el.btnCreateUser?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/users", "POST", {
        username: (el.newUser?.value || "").trim(),
        password: el.newPass?.value || "",
        role: el.newRole?.value || "viewer",
      });
      addMsg("tool", `Usuario creado: ${data.username} (${data.role})`);
      await loadUsersCatalog();
    } catch (err) {
      addMsg("tool", `Crear perfil error: ${err.message}`);
    }
  });

  el.userCatalog?.addEventListener("change", syncUserEditor);

  el.btnRefreshUsers?.addEventListener("click", async () => {
    try {
      await loadUsersCatalog();
      addMsg("tool", "Catalogo de usuarios actualizado.");
    } catch (err) {
      addMsg("tool", `Usuarios error: ${err.message}`);
    }
  });

  el.btnApplyUserEdit?.addEventListener("click", async () => {
    try {
      const username = el.userCatalog?.value || "";
      if (!username) return addMsg("tool", "Selecciona un usuario primero.");
      const roleResp = await apiRequest("/api/users/role", "POST", { username, role: el.editRole?.value || "viewer" });
      const activeResp = await apiRequest("/api/users/active", "POST", { username, active: Boolean(el.editActive?.checked) });
      addMsg("tool", `Usuario actualizado: ${roleResp.username} rol=${roleResp.role} activo=${activeResp.active}`);
      await loadUsersCatalog();
    } catch (err) {
      addMsg("tool", `Edicion usuario error: ${err.message}`);
    }
  });

  el.btnDeleteUser?.addEventListener("click", async () => {
    try {
      const username = el.userCatalog?.value || "";
      if (!username) return addMsg("tool", "Selecciona un usuario primero.");
      const data = await apiRequest("/api/users/delete", "POST", { username });
      addMsg("tool", `Usuario eliminado: ${data.deleted}`);
      await loadUsersCatalog();
    } catch (err) {
      addMsg("tool", `Eliminar usuario error: ${err.message}`);
    }
  });

  el.btnPullModel?.addEventListener("click", async () => {
    try {
      const model = (el.pullModelName?.value || "").trim();
      if (!model) return addMsg("tool", "Ingresa un modelo para descargar.");
      await pullModel(model);
    } catch (err) {
      addMsg("tool", `Descarga modelo error: ${err.message}`);
    }
  });

  el.btnRefreshDownloadCatalog?.addEventListener("click", async () => {
    try {
      await loadDownloadCatalog();
      addMsg("tool", "Catalogo de descarga actualizado.");
    } catch (err) {
      addMsg("tool", `Catalogo error: ${err.message}`);
    }
  });

  el.downloadCatalog?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const action = target.dataset.action;
    const model = target.dataset.model;
    if (action === "pull-catalog" && model) {
      try {
        await pullModel(model);
      } catch (err) {
        addMsg("tool", `Descarga de catalogo error: ${err.message}`);
      }
    }
  });

  el.btnLaunchGui?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/admin/gui/launch", "POST", {});
      addMsg("tool", `GUI lanzada: ${data.launched}`);
    } catch (err) {
      addMsg("tool", `Lanzar GUI error: ${err.message}`);
    }
  });

  el.btnSelfHealCheck?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/admin/self-heal/check");
      addMsg("tool", `Self-heal check: ok=${data.ok} issues=${(data.issues || []).join(",") || "ninguna"}`);
    } catch (err) {
      addMsg("tool", `Self-heal check error: ${err.message}`);
    }
  });

  el.btnSelfHealRun?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/admin/self-heal/run", "POST", {});
      addMsg("tool", `Self-heal run: ${(data.actions || []).join(", ") || "ninguna"}`);
    } catch (err) {
      addMsg("tool", `Self-heal run error: ${err.message}`);
    }
  });

  el.btnAiDiagCheck?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/admin/diagnostics/ai/check");
      const findings = data.findings || [];
      if (el.aiDiagStatus) {
        el.aiDiagStatus.textContent = findings.length
          ? findings.map((f) => `- [${f.severity}] ${f.code}: ${f.message}`).join("\n")
          : "Sin incidencias detectadas.";
      }
      addMsg("tool", `Mini IA diagnostica: ${findings.length} incidencia(s).`);
    } catch (err) {
      addMsg("tool", `Mini IA check error: ${err.message}`);
    }
  });

  el.btnAiDiagRun?.addEventListener("click", async () => {
    try {
      const data = await apiRequest("/api/admin/diagnostics/ai/repair", "POST", { actions: [] });
      const executed = data.executed || [];
      if (el.aiDiagStatus) {
        el.aiDiagStatus.textContent = executed.length
          ? executed.map((x) => `- ${x.action}: ${x.ok ? "ok" : "error"}`).join("\n")
          : "Sin acciones necesarias.";
      }
      addMsg("tool", `Mini IA reparacion ejecutada: ${executed.length} accion(es).`);
    } catch (err) {
      addMsg("tool", `Mini IA repair error: ${err.message}`);
    }
  });

  el.btnWebSearch?.addEventListener("click", async () => {
    try {
      const query = (el.webSearchQuery?.value || "").trim();
      if (!query) return addMsg("tool", "Ingresa una consulta para busqueda web.");
      const data = await apiRequest("/api/web/search", "POST", {
        query,
        max_results: Number(el.webSearchLimit?.value || 5),
      });
      const rows = data.results || [];
      if (el.webSearchStatus) {
        el.webSearchStatus.textContent = rows.length
          ? rows.map((r, i) => `${i + 1}. ${r.title} -> ${r.url}`).join("\n")
          : "Sin resultados para la consulta.";
      }
      addMsg("tool", `Busqueda web: ${rows.length} resultado(s).`);
    } catch (err) {
      addMsg("tool", `Busqueda web error: ${err.message}`);
    }
  });

  el.fileList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const action = target.dataset.action;
    const path = target.dataset.path || target.closest(".file-item")?.dataset.path;
    if (!path) return;

    if (action === "preview") {
      try {
        await previewFile(path);
      } catch (err) {
        addMsg("tool", `Preview error: ${err.message}`);
      }
      return;
    }

    if (action === "delete") {
      try {
        await deleteFile(path);
      } catch (err) {
        addMsg("tool", `Delete error: ${err.message}`);
      }
      return;
    }

    state.selectedFilePath = path;
    renderFileRows(state.filesCache);
  });

  el.btnSearchFiles?.addEventListener("click", async () => {
    try {
      await searchFiles();
    } catch (err) {
      addMsg("tool", `Error en busqueda: ${err.message}`);
    }
  });

  el.btnNewFolder?.addEventListener("click", async () => {
    try {
      await createFolder();
    } catch (err) {
      addMsg("tool", `Error al crear carpeta: ${err.message}`);
    }
  });

  el.btnUploadFile?.addEventListener("click", async () => {
    try {
      await uploadSelectedFile();
    } catch (err) {
      addMsg("tool", `Upload error: ${err.message}`);
    }
  });

  el.btnDownloadSelected?.addEventListener("click", async () => {
    try {
      await downloadSelectedFile();
    } catch (err) {
      addMsg("tool", `Download error: ${err.message}`);
    }
  });
}

function init() {
  if (el.perfMode) el.perfMode.value = state.perfMode;
  updateModelBadges();
  bindEvents();
  setStatus("Listo para iniciar sesion.");
}

init();
