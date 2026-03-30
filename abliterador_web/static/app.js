let token = "";

const log = document.getElementById("log");
const username = document.getElementById("username");
const password = document.getElementById("password");
const btnLogin = document.getElementById("btnLogin");
const btnModels = document.getElementById("btnModels");
const modelSelect = document.getElementById("modelSelect");
const btnSend = document.getElementById("btnSend");
const prompt = document.getElementById("prompt");
const useTools = document.getElementById("useTools");
const profileInfo = document.getElementById("profileInfo");
const adminBlock = document.getElementById("adminBlock");
const newUser = document.getElementById("newUser");
const newPass = document.getElementById("newPass");
const newRole = document.getElementById("newRole");
const btnCreateUser = document.getElementById("btnCreateUser");
const serverUrls = document.getElementById("serverUrls");
const ftpUrls = document.getElementById("ftpUrls");
const signupUser = document.getElementById("signupUser");
const signupPass = document.getElementById("signupPass");
const btnSignup = document.getElementById("btnSignup");
const btnRefreshUsers = document.getElementById("btnRefreshUsers");
const userCatalog = document.getElementById("userCatalog");
const editRole = document.getElementById("editRole");
const editActive = document.getElementById("editActive");
const btnApplyUserEdit = document.getElementById("btnApplyUserEdit");
const btnDeleteUser = document.getElementById("btnDeleteUser");
const pullModelName = document.getElementById("pullModelName");
const btnPullModel = document.getElementById("btnPullModel");
const pullStatus = document.getElementById("pullStatus");
const btnSelfHealCheck = document.getElementById("btnSelfHealCheck");
const btnSelfHealRun = document.getElementById("btnSelfHealRun");
const btnLaunchGui = document.getElementById("btnLaunchGui");

let roleCatalog = {};

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function api(path, payload) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Error de API");
  }
  return data;
}

async function apiGet(path) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Error de API");
  }
  return data;
}

async function loadModels() {
  if (!token) {
    addMsg("tool", "Inicia sesión primero.");
    return;
  }
  const res = await fetch("/api/models", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "No se pudieron cargar modelos");
  }

  modelSelect.innerHTML = "";
  for (const model of data.models || []) {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    modelSelect.appendChild(opt);
  }
  addMsg("tool", `Modelos cargados: ${(data.models || []).length}`);
}

async function loadProfile() {
  const data = await apiGet("/api/me");
  profileInfo.textContent = `Perfil: ${data.username} (${data.role}) | Activo: ${data.active} | Espacio: ${data.workspace}`;
  adminBlock.style.display = data.role === "admin" ? "block" : "none";
}

async function loadServerInfo() {
  const data = await apiGet("/api/server-info");

  if (!serverUrls) return;
  serverUrls.innerHTML = "";
  for (const url of data.urls || []) {
    const li = document.createElement("li");
    li.textContent = url;
    serverUrls.appendChild(li);
  }

  if (ftpUrls && data.ftp && Array.isArray(data.ftp.urls)) {
    ftpUrls.innerHTML = "";
    for (const url of data.ftp.urls) {
      const li = document.createElement("li");
      li.textContent = url;
      ftpUrls.appendChild(li);
    }
  }
}

async function loadRoles() {
  const data = await apiGet("/api/roles");
  roleCatalog = data.roles || {};
}

async function loadUsersCatalog() {
  const users = await apiGet("/api/users");
  if (!userCatalog) return;
  userCatalog.innerHTML = "";
  for (const item of users) {
    const opt = document.createElement("option");
    opt.value = item.username;
    opt.textContent = `${item.username} | ${item.role} | ${item.active ? "activo" : "inactivo"}`;
    opt.dataset.role = item.role;
    opt.dataset.active = item.active ? "1" : "0";
    userCatalog.appendChild(opt);
  }
  if (userCatalog.options.length > 0) {
    userCatalog.selectedIndex = 0;
    syncUserEditor();
  }
}

function syncUserEditor() {
  if (!userCatalog || userCatalog.selectedIndex < 0) return;
  const opt = userCatalog.options[userCatalog.selectedIndex];
  if (editRole) editRole.value = opt.dataset.role || "viewer";
  if (editActive) editActive.checked = (opt.dataset.active || "1") === "1";
}

btnLogin.addEventListener("click", async () => {
  try {
    const data = await api("/api/login", {
      username: username.value.trim(),
      password: password.value,
    });
    token = data.token;
    addMsg("tool", "Autenticado correctamente.");
    await loadProfile();
    await loadServerInfo();
    await loadRoles();
    if (adminBlock.style.display === "block") {
      await loadUsersCatalog();
    }
    await loadModels();
  } catch (err) {
    addMsg("tool", `Login error: ${err.message}`);
  }
});

btnSignup.addEventListener("click", async () => {
  try {
    const payload = {
      username: signupUser.value.trim(),
      password: signupPass.value,
    };
    const data = await api("/api/signup", payload);
    addMsg("tool", `Registro OK: ${data.username} (${data.role}). Ya puedes iniciar sesión.`);
    signupUser.value = "";
    signupPass.value = "";
  } catch (err) {
    addMsg("tool", `Registro error: ${err.message}`);
  }
});

btnModels.addEventListener("click", async () => {
  try {
    await loadModels();
  } catch (err) {
    addMsg("tool", `Modelos error: ${err.message}`);
  }
});

btnSend.addEventListener("click", async () => {
  try {
    const message = prompt.value.trim();
    if (!message) return;
    const model = modelSelect.value;
    if (!model) {
      addMsg("tool", "Selecciona un modelo primero.");
      return;
    }

    addMsg("user", message);
    prompt.value = "";

    const data = await api("/api/chat", {
      model,
      message,
      use_file_tools: useTools.checked,
    });

    if (Array.isArray(data.tool_events)) {
      for (const event of data.tool_events) {
        addMsg("tool", event);
      }
    }
    addMsg("ai", data.reply || "");
  } catch (err) {
    addMsg("tool", `Chat error: ${err.message}`);
  }
});

btnCreateUser.addEventListener("click", async () => {
  try {
    if (!token) {
      addMsg("tool", "Inicia sesión como admin primero.");
      return;
    }
    const payload = {
      username: newUser.value.trim(),
      password: newPass.value,
      role: newRole.value,
    };
    const data = await api("/api/users", payload);
    addMsg("tool", `Usuario creado: ${data.username} (${data.role}) -> ${data.workspace}`);
    newUser.value = "";
    newPass.value = "";
    newRole.value = "viewer";
    await loadUsersCatalog();
  } catch (err) {
    addMsg("tool", `Crear perfil error: ${err.message}`);
  }
});

userCatalog?.addEventListener("change", syncUserEditor);

btnRefreshUsers?.addEventListener("click", async () => {
  try {
    await loadUsersCatalog();
    addMsg("tool", "Catalogo de usuarios actualizado.");
  } catch (err) {
    addMsg("tool", `Usuarios error: ${err.message}`);
  }
});

btnApplyUserEdit?.addEventListener("click", async () => {
  try {
    const selected = userCatalog?.value || "";
    if (!selected) {
      addMsg("tool", "Selecciona un usuario primero.");
      return;
    }
    const roleResp = await api("/api/users/role", {
      username: selected,
      role: editRole.value,
    });
    const activeResp = await api("/api/users/active", {
      username: selected,
      active: Boolean(editActive.checked),
    });
    addMsg("tool", `Usuario actualizado: ${roleResp.username} rol=${roleResp.role} activo=${activeResp.active}`);
    await loadUsersCatalog();
  } catch (err) {
    addMsg("tool", `Edición usuario error: ${err.message}`);
  }
});

btnDeleteUser?.addEventListener("click", async () => {
  try {
    const selected = userCatalog?.value || "";
    if (!selected) {
      addMsg("tool", "Selecciona un usuario primero.");
      return;
    }
    const data = await api("/api/users/delete", { username: selected });
    addMsg("tool", `Usuario eliminado: ${data.deleted}`);
    await loadUsersCatalog();
  } catch (err) {
    addMsg("tool", `Eliminar usuario error: ${err.message}`);
  }
});

btnPullModel?.addEventListener("click", async () => {
  try {
    const model = (pullModelName?.value || "").trim();
    if (!model) {
      addMsg("tool", "Ingresa un modelo para descargar.");
      return;
    }
    const job = await api("/api/admin/models/pull", { model });
    pullStatus.textContent = `Job ${job.job_id}: ${job.status}`;
    addMsg("tool", `Descarga de modelo iniciada: ${model}`);

    let done = false;
    while (!done) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      const status = await apiGet(`/api/admin/models/pull/${job.job_id}`);
      pullStatus.textContent = `Job ${status.job_id}: ${status.status}`;
      if (status.status === "done" || status.status === "failed") {
        done = true;
        addMsg("tool", `Modelo ${status.model}: ${status.status}`);
        if (status.output_tail) {
          addMsg("tool", status.output_tail);
        }
      }
    }
  } catch (err) {
    addMsg("tool", `Descarga modelo error: ${err.message}`);
  }
});

btnSelfHealCheck?.addEventListener("click", async () => {
  try {
    const data = await apiGet("/api/admin/self-heal/check");
    addMsg("tool", `Self-heal check: ok=${data.ok} issues=${(data.issues || []).join(", ") || "ninguna"}`);
  } catch (err) {
    addMsg("tool", `Self-heal check error: ${err.message}`);
  }
});

btnSelfHealRun?.addEventListener("click", async () => {
  try {
    const data = await api("/api/admin/self-heal/run", {});
    addMsg("tool", `Self-heal run: acciones=${(data.actions || []).join(", ") || "ninguna"}`);
  } catch (err) {
    addMsg("tool", `Self-heal run error: ${err.message}`);
  }
});

btnLaunchGui?.addEventListener("click", async () => {
  try {
    const data = await api("/api/admin/gui/launch", {});
    addMsg("tool", `GUI lanzada: ${data.launched}`);
  } catch (err) {
    addMsg("tool", `Lanzar GUI error: ${err.message}`);
  }
});
