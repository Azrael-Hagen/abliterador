import {
  state,
  el,
  apiRequest,
  addMsg,
  setStatus,
  setProgress,
  setActiveTab,
  getPerfCfg,
  setActiveModel,
  updateModelBadges,
  appendTransferLog,
} from "./app_core.js";
import {
  renderFileRows,
  loadFileList,
  previewFile,
  deleteFile,
  createFolder,
  uploadSelectedFile,
  downloadSelectedFile,
  searchFiles,
} from "./app_files.js";
import {
  loadProfile,
  loadUsersCatalog,
  syncUserEditor,
  loadServerInfo,
  renderDownloadCatalog,
} from "./app_users.js";

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

async function loadDownloadCatalog() {
  if (!state.token || !el.downloadCatalog || !state.profile || state.profile.role !== "admin") return;
  const data = await apiRequest("/api/models/download-catalog");
  renderDownloadCatalog(data.models || [], pullModel);
}

async function sendChat() {
  if (state.isGenerating) {
    addMsg("tool", "Ya hay una generacion en curso. Puedes cancelarla.");
    return;
  }

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

  state.isGenerating = true;
  state.chatAbortController = new AbortController();
  if (el.btnSend) el.btnSend.disabled = true;
  if (el.btnCancel) el.btnCancel.disabled = false;

  try {
    if (payload.use_web_search) {
      setProgress(true, "Enriqueciendo contexto web...");
    }

    setProgress(true, "Generando respuesta...");
    const data = await apiRequest(endpoint, "POST", payload, false, {
      signal: state.chatAbortController?.signal,
    });
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
    if (err?.name === "AbortError") {
      addMsg("tool", "Generacion cancelada por el usuario.");
      setStatus("Generacion cancelada");
    } else {
      addMsg("tool", `Chat error: ${err.message}`);
      setStatus("Error en chat");
    }
  } finally {
    state.isGenerating = false;
    state.chatAbortController = null;
    if (el.btnSend) el.btnSend.disabled = false;
    if (el.btnCancel) el.btnCancel.disabled = true;
    setProgress(false, "Listo");
  }
}

function cancelChatGeneration() {
  if (!state.isGenerating || !state.chatAbortController) return;
  state.chatAbortController.abort();
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
  el.btnCancel?.addEventListener("click", cancelChatGeneration);

  el.prompt?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!state.isGenerating) {
        void sendChat();
      }
    }
  });

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

async function refreshConnectionBadge() {
  if (!el.connBadge) return;
  try {
    const startedAt = performance.now();
    const response = await fetch("/api/health", { method: "GET" });
    const elapsedMs = Math.round(performance.now() - startedAt);
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    el.connBadge.textContent = `Servidor: online (${elapsedMs} ms)`;
    el.connBadge.classList.remove("badge-warn");
  } catch (_err) {
    el.connBadge.textContent = "Servidor: sin conexion";
    el.connBadge.classList.add("badge-warn");
  }
}

function init() {
  if (el.perfMode) el.perfMode.value = state.perfMode;
  updateModelBadges();
  bindEvents();
  setStatus("Listo para iniciar sesion.");
  void refreshConnectionBadge();
  window.setInterval(() => {
    void refreshConnectionBadge();
  }, 15000);
}

init();
