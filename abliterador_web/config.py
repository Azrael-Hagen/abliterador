import os
from dataclasses import dataclass
from pathlib import Path


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
    )
