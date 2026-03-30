from __future__ import annotations

import json
import time
from pathlib import Path


class WebKnowledgeStore:
    def __init__(self, memory_path: Path, max_queries: int = 200):
        self.memory_path = memory_path
        self.max_queries = max(20, max_queries)
        self._state = self._load()

    def _load(self) -> dict:
        if not self.memory_path.exists():
            return {"queries": []}
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("queries"), list):
                return data
        except Exception:
            pass
        return {"queries": []}

    def _save(self) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record(self, query: str, results: list[dict[str, str]]) -> None:
        cleaned = [
            {
                "title": str(item.get("title", ""))[:200],
                "url": str(item.get("url", ""))[:500],
                "snippet": str(item.get("snippet", ""))[:700],
                "source": str(item.get("source", ""))[:50],
            }
            for item in (results or [])
            if item.get("url")
        ]
        if not cleaned:
            return

        self._state.setdefault("queries", []).append(
            {
                "query": (query or "").strip()[:300],
                "timestamp": int(time.time()),
                "results": cleaned,
            }
        )
        self._state["queries"] = self._state["queries"][-self.max_queries :]
        self._save()

    def recent(self, query_hint: str = "", limit: int = 5) -> list[dict[str, str]]:
        hint = (query_hint or "").strip().lower()
        seen: set[str] = set()
        out: list[dict[str, str]] = []
        rows = list(self._state.get("queries", []))

        for row in reversed(rows):
            query = str(row.get("query", "")).lower()
            if hint and hint not in query:
                continue
            for item in row.get("results", []):
                url = str(item.get("url", "")).strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                out.append(
                    {
                        "title": str(item.get("title", "")),
                        "url": url,
                        "snippet": str(item.get("snippet", "")),
                        "source": str(item.get("source", "memory")) or "memory",
                    }
                )
                if len(out) >= limit:
                    return out

        if hint:
            return out

        for row in reversed(rows):
            for item in row.get("results", []):
                url = str(item.get("url", "")).strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                out.append(
                    {
                        "title": str(item.get("title", "")),
                        "url": url,
                        "snippet": str(item.get("snippet", "")),
                        "source": str(item.get("source", "memory")) or "memory",
                    }
                )
                if len(out) >= limit:
                    return out

        return out