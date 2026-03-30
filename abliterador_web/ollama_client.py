from __future__ import annotations

import json
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

    def chat_stream(self, model: str, messages: list[dict[str, Any]], timeout_s: int = 120):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "stream": True,
            "messages": messages,
        }

        with self._session.post(url, json=payload, timeout=timeout_s, stream=True) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                line = (raw_line or "").strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue

                msg = row.get("message", {}) if isinstance(row, dict) else {}
                delta = str(msg.get("content", ""))
                done = bool(row.get("done", False)) if isinstance(row, dict) else False

                chunk: dict[str, Any] = {
                    "delta": delta,
                    "done": done,
                }
                if done:
                    chunk["total_duration"] = row.get("total_duration")
                    chunk["eval_count"] = row.get("eval_count")
                    chunk["eval_duration"] = row.get("eval_duration")
                yield chunk
