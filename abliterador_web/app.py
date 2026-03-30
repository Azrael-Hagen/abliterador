from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from typing import Any
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from abliterador_web.auth import AuthUser, TokenAuth
from abliterador_web.config import WebSettings, load_settings
from abliterador_web.models import (
    ChatRequest,
    ChatResponse,
    FileDeleteRequest,
    FileListRequest,
    FileReadRequest,
    FileWriteRequest,
    LoginRequest,
    LoginResponse,
    ModelPullJobResponse,
    ModelPullRequest,
    SignupRequest,
    SignupResponse,
    UserActiveUpdateRequest,
    UserCreateRequest,
    UserDeleteRequest,
    UserProfileResponse,
    UserRoleUpdateRequest,
)
from abliterador_web.ftp_server import ftp_urls
from abliterador_web.network import detect_server_addresses, is_local_network_ip
from abliterador_web.ollama_client import OllamaClient
from abliterador_web.sandbox import FileSandbox, SandboxError
from abliterador_web.users import ROLE_CATALOG, UserStore


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_s: int):
        self.max_requests = max_requests
        self.window_s = window_s
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        threshold = now - self.window_s

        with self._lock:
            events = self._events.get(key, [])
            events = [value for value in events if value >= threshold]
            if len(events) >= self.max_requests:
                self._events[key] = events
                return False
            events.append(now)
            self._events[key] = events
            return True


class ModelsCache:
    def __init__(self, ttl_s: int):
        self.ttl_s = max(1, ttl_s)
        self._models: list[str] = []
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_or_load(self, loader: callable) -> list[str]:
        now = time.monotonic()
        with self._lock:
            if self._models and now < self._expires_at:
                return list(self._models)

        loaded = list(loader())
        with self._lock:
            self._models = loaded
            self._expires_at = time.monotonic() + self.ttl_s
            return list(self._models)


class ModelPullManager:
    def __init__(self):
        self._jobs: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    def start(self, model: str) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "model": model,
                "status": "queued",
                "output_tail": "",
            }

        def worker() -> None:
            self._update(job_id, status="running")
            try:
                proc = subprocess.Popen(
                    ["ollama", "pull", model],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                out = []
                if proc.stdout:
                    for line in proc.stdout:
                        out.append(line.rstrip())
                        out = out[-60:]
                        self._update(job_id, output_tail="\n".join(out))
                code = proc.wait()
                self._update(job_id, status="done" if code == 0 else "failed")
            except Exception as exc:
                self._update(job_id, status="failed", output_tail=str(exc))

        threading.Thread(target=worker, daemon=True).start()
        return job_id

    def _update(self, job_id: str, **kwargs: str) -> None:
        with self._lock:
            row = self._jobs.get(job_id)
            if not row:
                return
            row.update(kwargs)

    def get(self, job_id: str) -> dict[str, str] | None:
        with self._lock:
            row = self._jobs.get(job_id)
            return dict(row) if row else None


class AutoRecoveryManager:
    def __init__(self):
        self._last_run = 0.0

    def check(self, settings: WebSettings, ollama: OllamaClient) -> dict[str, Any]:
        issues: list[str] = []
        try:
            _ = ollama.list_models()
        except Exception:
            issues.append("ollama_unreachable")

        if not settings.users_db_path.exists():
            issues.append("users_db_missing")
        elif not os.access(settings.users_db_path, os.R_OK | os.W_OK):
            issues.append("users_db_permissions")

        return {"ok": not issues, "issues": issues}

    def run(self, settings: WebSettings, ollama: OllamaClient) -> dict[str, Any]:
        now = time.time()
        if now - self._last_run < 20:
            return {"actions": ["cooldown_active"], "check": self.check(settings, ollama)}
        self._last_run = now

        check = self.check(settings, ollama)
        actions: list[str] = []
        if "users_db_missing" in check["issues"]:
            settings.users_db_path.parent.mkdir(parents=True, exist_ok=True)
            settings.users_db_path.write_text('{"users": []}', encoding="utf-8")
            actions.append("users_db_created")

        if "ollama_unreachable" in check["issues"]:
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                actions.append("ollama_serve_started")
            except Exception:
                actions.append("ollama_serve_failed")

        return {"actions": actions, "check": self.check(settings, ollama)}


def _extract_tool_call(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get("tool"):
            return obj
    except Exception:
        return None
    return None


def _tool_system_prompt() -> str:
    return (
        "You can answer normally. If the user asks to create/edit/read/delete files, "
        "respond with JSON only and no extra text using this schema: "
        "{\"tool\":\"write_file|read_file|delete_file|list_dir\",\"path\":\"relative/path\",\"content\":\"...optional\"}. "
        "Use only relative paths. Never attempt paths outside sandbox."
    )


def create_app() -> FastAPI:
    settings = load_settings()
    auth = TokenAuth(secret=settings.secret)
    user_store = UserStore(settings.users_db_path)
    user_store.ensure_admin(settings.username, settings.password)
    settings.user_workspaces_root.mkdir(parents=True, exist_ok=True)
    ollama = OllamaClient(settings.ollama_url)
    models_cache = ModelsCache(settings.models_cache_ttl_s)
    pull_manager = ModelPullManager()
    recovery_manager = AutoRecoveryManager()
    rate_limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute, 60)
    server_urls = [item.url for item in detect_server_addresses(settings.port)]
    ftp_access_urls = ftp_urls(settings.ftp_port) if settings.ftp_enabled else []

    app = FastAPI(title="Abliterador Web Server", version="0.7.0")
    module_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(module_dir / "templates"))
    app.mount("/static", StaticFiles(directory=str(module_dir / "static")), name="static")

    @app.middleware("http")
    async def local_network_guard(request: Request, call_next):
        path = request.url.path
        client_host = request.client.host if request.client else ""

        if settings.local_network_only:
            if not is_local_network_ip(client_host):
                raise HTTPException(status_code=403, detail="Solo acceso de red local")

        if path.startswith("/api/"):
            key = client_host or "unknown"
            if not rate_limiter.allow(key):
                raise HTTPException(status_code=429, detail="Demasiadas solicitudes, intenta en unos segundos")

        return await call_next(request)

    def user_workspace(username: str) -> Path:
        root = (settings.user_workspaces_root / username).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def user_sandbox(user: AuthUser) -> FileSandbox:
        return FileSandbox([user_workspace(user.username)])

    def _to_profile_response(item) -> UserProfileResponse:
        return UserProfileResponse(
            username=item.username,
            role=item.role,
            active=getattr(item, "active", True),
            permissions=list(getattr(item, "permissions", []) or []),
            workspace=str(user_workspace(item.username)),
        )

    def _has_permission(user: AuthUser, permission: str) -> bool:
        perms = ROLE_CATALOG.get(user.role, [])
        return permission in perms

    def require_user(authorization: str | None = Header(default=None)) -> AuthUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = authorization.split(" ", 1)[1].strip()
        try:
            return auth.verify_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    def require_admin(user: AuthUser = Depends(require_user)) -> AuthUser:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin requerido")
        return user

    def require_permission(permission: str):
        def _inner(user: AuthUser = Depends(require_user)) -> AuthUser:
            if not _has_permission(user, permission):
                raise HTTPException(status_code=403, detail=f"Permiso requerido: {permission}")
            return user

        return _inner

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": "Abliterador Nexus",
                "allowed_dirs": [str(settings.user_workspaces_root)],
                "server_urls": server_urls,
                "ftp_enabled": settings.ftp_enabled,
                "ftp_urls": ftp_access_urls,
                "ftp_root": str(settings.ftp_root),
                "ftp_libraries": [str(path) for path in settings.ftp_libraries],
                "default_admin_user": settings.username,
                "default_admin_password": settings.password,
            },
        )

    @app.post("/api/login", response_model=LoginResponse)
    async def login(payload: LoginRequest):
        profile = user_store.verify_credentials(payload.username, payload.password)
        if not profile:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        token = auth.issue_token(profile.username, profile.role)
        return LoginResponse(token=token)

    @app.post("/api/signup", response_model=SignupResponse)
    async def signup(payload: SignupRequest):
        try:
            profile = user_store.register_user(payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return SignupResponse(username=profile.username, role=profile.role)

    @app.get("/api/me", response_model=UserProfileResponse)
    async def me(user: AuthUser = Depends(require_user)):
        profile = user_store.get_user(user.username)
        return _to_profile_response(profile) if profile else _to_profile_response(user)

    @app.get("/api/roles")
    async def roles(_user: AuthUser = Depends(require_user)):
        return {"roles": user_store.role_catalog()}

    @app.get("/api/users", response_model=list[UserProfileResponse])
    async def users_list(_admin: AuthUser = Depends(require_permission("manage_users"))):
        return [_to_profile_response(item) for item in user_store.list_users()]

    @app.post("/api/users", response_model=UserProfileResponse)
    async def users_create(payload: UserCreateRequest, _admin: AuthUser = Depends(require_permission("manage_users"))):
        try:
            profile = user_store.create_user(payload.username, payload.password, payload.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _to_profile_response(profile)

    @app.post("/api/users/role", response_model=UserProfileResponse)
    async def users_update_role(
        payload: UserRoleUpdateRequest,
        _admin: AuthUser = Depends(require_permission("manage_users")),
    ):
        try:
            profile = user_store.update_user_role(payload.username, payload.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _to_profile_response(profile)

    @app.post("/api/users/active", response_model=UserProfileResponse)
    async def users_update_active(
        payload: UserActiveUpdateRequest,
        _admin: AuthUser = Depends(require_permission("manage_users")),
    ):
        try:
            profile = user_store.set_user_active(payload.username, payload.active)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _to_profile_response(profile)

    @app.post("/api/users/delete")
    async def users_delete(
        payload: UserDeleteRequest,
        admin: AuthUser = Depends(require_permission("manage_users")),
    ):
        if payload.username.strip().lower() == admin.username.strip().lower():
            raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")
        try:
            user_store.delete_user(payload.username)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"deleted": payload.username}

    @app.get("/api/models")
    async def models(_user: AuthUser = Depends(require_permission("chat"))):
        try:
            return {"models": models_cache.get_or_load(ollama.list_models)}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"No se pudo consultar Ollama: {exc}") from exc

    @app.post("/api/admin/models/pull", response_model=ModelPullJobResponse)
    async def model_pull(
        payload: ModelPullRequest,
        _user: AuthUser = Depends(require_permission("manage_models")),
    ):
        job_id = pull_manager.start(payload.model)
        row = pull_manager.get(job_id) or {}
        return ModelPullJobResponse(
            job_id=job_id,
            model=row.get("model", payload.model),
            status=row.get("status", "queued"),
            output_tail=row.get("output_tail", ""),
        )

    @app.get("/api/admin/models/pull/{job_id}", response_model=ModelPullJobResponse)
    async def model_pull_status(
        job_id: str,
        _user: AuthUser = Depends(require_permission("manage_models")),
    ):
        row = pull_manager.get(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        return ModelPullJobResponse(
            job_id=row.get("job_id", job_id),
            model=row.get("model", ""),
            status=row.get("status", "unknown"),
            output_tail=row.get("output_tail", ""),
        )

    @app.post("/api/admin/gui/launch")
    async def gui_launch(_user: AuthUser = Depends(require_permission("launch_gui"))):
        try:
            studio_exe = Path(sys.executable).resolve().with_name("AbliteradorStudio.exe")
            if studio_exe.exists():
                subprocess.Popen([str(studio_exe)], cwd=str(studio_exe.parent))
                return {"launched": str(studio_exe)}

            source_entry = Path.cwd() / "abliterador_studio.py"
            if source_entry.exists() and not getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable, str(source_entry)], cwd=str(Path.cwd()))
                return {"launched": str(source_entry)}

            if source_entry.exists() and getattr(sys, "frozen", False):
                subprocess.Popen(["python", str(source_entry)], cwd=str(Path.cwd()))
                return {"launched": str(source_entry)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"No se pudo lanzar GUI: {exc}") from exc

        raise HTTPException(status_code=404, detail="No se encontro GUI de escritorio")

    @app.get("/api/admin/self-heal/check")
    async def self_heal_check(_user: AuthUser = Depends(require_permission("self_heal"))):
        return recovery_manager.check(settings, ollama)

    @app.post("/api/admin/self-heal/run")
    async def self_heal_run(_user: AuthUser = Depends(require_permission("self_heal"))):
        return recovery_manager.run(settings, ollama)

    @app.get("/api/server-info")
    async def server_info(_user: AuthUser = Depends(require_user)):
        return {
            "urls": server_urls,
            "host": settings.host,
            "port": settings.port,
            "local_network_only": settings.local_network_only,
            "ftp": {
                "enabled": settings.ftp_enabled,
                "host": settings.ftp_host,
                "port": settings.ftp_port,
                "username": settings.ftp_username,
                "root": str(settings.ftp_root),
                "libraries": [str(path) for path in settings.ftp_libraries],
                "urls": ftp_access_urls,
            },
        }

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, user: AuthUser = Depends(require_permission("chat"))):
        sandbox = user_sandbox(user)
        messages = []
        if payload.use_file_tools:
            messages.append({"role": "system", "content": _tool_system_prompt()})
        messages.append({"role": "user", "content": payload.message})

        try:
            reply = ollama.chat(model=payload.model, messages=messages)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Error de inferencia: {exc}") from exc

        tool_events: list[str] = []
        if payload.use_file_tools:
            tool_call = _extract_tool_call(reply)
            if tool_call:
                try:
                    tool_name = str(tool_call.get("tool", ""))
                    path = str(tool_call.get("path", "")).strip()
                    content = str(tool_call.get("content", ""))
                    if tool_name == "write_file":
                        written = sandbox.write_text(path, content)
                        result = f"write_file ok: {written}"
                    elif tool_name == "read_file":
                        read = sandbox.read_text(path)
                        result = f"read_file ok:\n{read}"
                    elif tool_name == "delete_file":
                        deleted = sandbox.delete_file(path)
                        result = f"delete_file ok: {deleted}"
                    elif tool_name == "list_dir":
                        entries = sandbox.list_dir(path or ".")
                        result = "list_dir ok:\n" + "\n".join(entries)
                    else:
                        result = "tool rechazada: herramienta no permitida"

                    tool_events.append(result)
                    messages.append({"role": "assistant", "content": reply})
                    messages.append({"role": "tool", "content": result})
                    follow_up = ollama.chat(model=payload.model, messages=messages)
                    return ChatResponse(reply=follow_up, tool_events=tool_events)
                except SandboxError as exc:
                    tool_events.append(f"tool rechazada por sandbox: {exc}")
                except Exception as exc:
                    tool_events.append(f"tool error: {exc}")

        return ChatResponse(reply=reply, tool_events=tool_events)

    @app.post("/api/files/list")
    async def files_list(payload: FileListRequest, user: AuthUser = Depends(require_permission("files"))):
        sandbox = user_sandbox(user)
        try:
            return {"entries": sandbox.list_dir(payload.path)}
        except SandboxError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/read")
    async def files_read(payload: FileReadRequest, user: AuthUser = Depends(require_permission("files"))):
        sandbox = user_sandbox(user)
        try:
            return {"content": sandbox.read_text(payload.path)}
        except SandboxError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/write")
    async def files_write(payload: FileWriteRequest, user: AuthUser = Depends(require_permission("files"))):
        sandbox = user_sandbox(user)
        try:
            written = sandbox.write_text(payload.path, payload.content)
            return {"written": written}
        except SandboxError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/delete")
    async def files_delete(payload: FileDeleteRequest, user: AuthUser = Depends(require_permission("files"))):
        sandbox = user_sandbox(user)
        try:
            deleted = sandbox.delete_file(payload.path)
            return {"deleted": deleted}
        except SandboxError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "allowed_dirs": [str(settings.user_workspaces_root)],
            "ollama_url": settings.ollama_url,
            "local_network_only": settings.local_network_only,
            "server_urls": server_urls,
            "models_cache_ttl_s": settings.models_cache_ttl_s,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "ftp_enabled": settings.ftp_enabled,
            "ftp_urls": ftp_access_urls,
            "ftp_root": str(settings.ftp_root),
            "roles": user_store.role_catalog(),
        }

    return app


app = create_app()
