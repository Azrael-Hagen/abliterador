import os
from dataclasses import dataclass
from pathlib import Path

from abliterador_web.ftp_server import discover_windows_libraries


@dataclass(frozen=True)
class WebSettings:
    host: str
    port: int
    username: str
    password: str
    secret: str
    ollama_url: str
    allowed_dirs: list[Path]
    users_db_path: Path
    user_workspaces_root: Path
    local_network_only: bool
    models_cache_ttl_s: int
    rate_limit_per_minute: int
    ftp_enabled: bool
    ftp_host: str
    ftp_port: int
    ftp_username: str
    ftp_password: str
    ftp_root: Path
    ftp_libraries: list[Path]
    diagnostics_memory_path: Path
    gui_launch_command: str
    web_search_enabled: bool
    web_search_timeout_s: int
    web_search_cache_ttl_s: int
    web_search_max_results: int
    web_knowledge_path: Path
    web_knowledge_max_queries: int


def _parse_allowed_dirs(raw: str) -> list[Path]:
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    resolved = [Path(p).resolve() for p in parts]
    unique = []
    seen = set()
    for path in resolved:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def load_settings() -> WebSettings:
    workspace = Path.cwd().resolve()
    home = Path.home().resolve()
    default_sandbox = workspace / "web_workspace"
    default_sandbox.mkdir(parents=True, exist_ok=True)
    user_workspaces_root = default_sandbox / "users"
    user_workspaces_root.mkdir(parents=True, exist_ok=True)
    users_db_path = workspace / "abliterador_users.json"

    allowed_raw = os.getenv("ABLITERADOR_ALLOWED_DIRS", str(default_sandbox))
    allowed_dirs = _parse_allowed_dirs(allowed_raw)
    if not allowed_dirs:
        allowed_dirs = [default_sandbox]

    for path in allowed_dirs:
        path.mkdir(parents=True, exist_ok=True)

    ftp_root = Path(os.getenv("ABLITERADOR_FTP_ROOT", str(home))).resolve()
    ftp_root.mkdir(parents=True, exist_ok=True)
    ftp_libraries = discover_windows_libraries(home)

    return WebSettings(
        host=os.getenv("ABLITERADOR_WEB_HOST", "0.0.0.0"),
        port=int(os.getenv("ABLITERADOR_WEB_PORT", "8088")),
        username=os.getenv("ABLITERADOR_WEB_USER", "admin"),
        password=os.getenv("ABLITERADOR_WEB_PASSWORD", "change_me_now"),
        secret=os.getenv("ABLITERADOR_WEB_SECRET", "replace-me-with-random-secret"),
        ollama_url=os.getenv("ABLITERADOR_OLLAMA_URL", "http://127.0.0.1:11434"),
        allowed_dirs=allowed_dirs,
        users_db_path=Path(os.getenv("ABLITERADOR_USERS_DB", str(users_db_path))).resolve(),
        user_workspaces_root=Path(
            os.getenv("ABLITERADOR_USER_WORKSPACES_ROOT", str(user_workspaces_root))
        ).resolve(),
        local_network_only=os.getenv("ABLITERADOR_LOCAL_NETWORK_ONLY", "1") == "1",
        models_cache_ttl_s=int(os.getenv("ABLITERADOR_MODELS_CACHE_TTL_S", "20")),
        rate_limit_per_minute=int(os.getenv("ABLITERADOR_RATE_LIMIT_PER_MINUTE", "120")),
        ftp_enabled=os.getenv("ABLITERADOR_FTP_ENABLED", "1") == "1",
        ftp_host=os.getenv("ABLITERADOR_FTP_HOST", "0.0.0.0"),
        ftp_port=int(os.getenv("ABLITERADOR_FTP_PORT", "2121")),
        ftp_username=os.getenv("ABLITERADOR_FTP_USER", "lanuser"),
        ftp_password=os.getenv("ABLITERADOR_FTP_PASSWORD", "change_me_ftp"),
        ftp_root=ftp_root,
        ftp_libraries=ftp_libraries,
        diagnostics_memory_path=Path(
            os.getenv("ABLITERADOR_DIAGNOSTICS_MEMORY", str(default_sandbox / "diagnostics_memory.json"))
        ).resolve(),
        gui_launch_command=os.getenv("ABLITERADOR_GUI_LAUNCH_CMD", "").strip(),
        web_search_enabled=os.getenv("ABLITERADOR_WEB_SEARCH_ENABLED", "1") == "1",
        web_search_timeout_s=int(os.getenv("ABLITERADOR_WEB_SEARCH_TIMEOUT_S", "8")),
        web_search_cache_ttl_s=int(os.getenv("ABLITERADOR_WEB_SEARCH_CACHE_TTL_S", "600")),
        web_search_max_results=int(os.getenv("ABLITERADOR_WEB_SEARCH_MAX_RESULTS", "5")),
        web_knowledge_path=Path(
            os.getenv("ABLITERADOR_WEB_KNOWLEDGE_PATH", str(default_sandbox / "web_knowledge.json"))
        ).resolve(),
        web_knowledge_max_queries=int(os.getenv("ABLITERADOR_WEB_KNOWLEDGE_MAX_QUERIES", "200")),
    )
