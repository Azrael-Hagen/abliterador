import { $, state, el, apiRequest, setStatus, addMsg } from "./app_core.js";

export async function loadProfile() {
  const data = await apiRequest("/api/me");
  state.profile = data;
  if (el.profileInfo) {
    el.profileInfo.textContent = `Perfil: ${data.username} (${data.role}) | Activo: ${data.active} | Espacio: ${data.workspace}`;
  }
  if (el.adminBlock) el.adminBlock.style.display = data.role === "admin" ? "block" : "none";
  if (el.adminHint) el.adminHint.style.display = data.role === "admin" ? "none" : "block";
  setStatus(`Sesion activa: ${data.username} (${data.role})`);
}

export async function loadUsersCatalog() {
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

export function syncUserEditor() {
  if (!el.userCatalog || el.userCatalog.selectedIndex < 0) return;
  const current = el.userCatalog.options[el.userCatalog.selectedIndex];
  if (el.editRole) el.editRole.value = current.dataset.role || "viewer";
  if (el.editActive) el.editActive.checked = (current.dataset.active || "1") === "1";
}

export async function loadServerInfo() {
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

export function renderDownloadCatalog(rows, onPull) {
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

  el.downloadCatalog.onclick = async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const action = target.dataset.action;
    const model = target.dataset.model;
    if (action === "pull-catalog" && model && typeof onPull === "function") {
      try {
        await onPull(model);
      } catch (err) {
        addMsg("tool", `Descarga de catalogo error: ${err.message}`);
      }
    }
  };
}
