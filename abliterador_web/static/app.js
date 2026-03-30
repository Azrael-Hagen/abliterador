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
  const res = await fetch("/api/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "No se pudo cargar perfil");
  }
  profileInfo.textContent = `Perfil: ${data.username} (${data.role}) | Espacio: ${data.workspace}`;
  adminBlock.style.display = data.role === "admin" ? "block" : "none";
}

async function loadServerInfo() {
  const res = await fetch("/api/server-info", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "No se pudo cargar info del servidor");
  }

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
    await loadModels();
  } catch (err) {
    addMsg("tool", `Login error: ${err.message}`);
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
    newRole.value = "user";
  } catch (err) {
    addMsg("tool", `Crear perfil error: ${err.message}`);
  }
});
