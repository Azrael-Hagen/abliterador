import { state, el, apiRequest, addMsg, appendTransferLog, parseApiError } from "./app_core.js";

export function renderFileRows(rows) {
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

export async function loadFileList() {
  if (!state.token || !el.fileListStatus) return;
  el.fileListStatus.textContent = "Cargando archivos...";
  const data = await apiRequest("/api/files/manager/list", "POST", { path: "", filter_type: null });
  state.filesCache = Array.isArray(data.files) ? data.files : [];
  renderFileRows(state.filesCache);
}

export async function previewFile(path) {
  const data = await apiRequest("/api/files/manager/preview", "POST", { path });
  if (data.content) {
    addMsg("tool", data.content.substring(0, 800), `Preview: ${path}`);
  } else {
    addMsg("tool", data.reason || "Tipo no soportado para preview", `Preview: ${path}`);
  }
}

export async function deleteFile(path) {
  if (!window.confirm(`Eliminar ${path}?`)) return;
  await apiRequest("/api/files/manager/delete", "POST", { path });
  appendTransferLog(`Eliminado: ${path}`);
  if (state.selectedFilePath === path) state.selectedFilePath = "";
  await loadFileList();
}

export async function createFolder() {
  const folderName = window.prompt("Nombre de la carpeta:");
  if (!folderName) return;
  const data = await apiRequest("/api/files/manager/mkdir", "POST", { path: folderName });
  appendTransferLog(`Carpeta creada: ${data.path}`);
  await loadFileList();
}

export async function uploadSelectedFile() {
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

export async function downloadSelectedFile() {
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

export async function searchFiles() {
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
