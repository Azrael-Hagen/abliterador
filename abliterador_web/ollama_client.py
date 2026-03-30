from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def list_models(self) -> list[str]:
        url = f"{self.base_url}/api/tags"
        response = self._session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        models = []
        for item in data.get("models", []):
            name = item.get("name")
            if isinstance(name, str) and name:
                models.append(name)
        return models

    def chat(self, model: str, messages: list[dict[str, Any]], timeout_s: int = 120) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "stream": False,
            "messages": messages,
        }
        response = self._session.post(url, json=payload, timeout=timeout_s)
        response.raise_for_status()
        data = response.json()
        msg = data.get("message", {})
        return str(msg.get("content", "")).strip()
