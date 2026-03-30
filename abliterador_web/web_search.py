from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&quot;", '"').strip()


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str
    source: str


class WebSearchService:
    def __init__(self, timeout_s: int = 8, ttl_s: int = 600, max_results: int = 5):
        self.timeout_s = max(2, timeout_s)
        self.ttl_s = max(30, ttl_s)
        self.max_results = max(1, min(max_results, 10))
        self._cache: dict[str, tuple[float, list[WebSearchResult]]] = {}

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "AbliteradorWeb/0.8 (+https://github.com/Azrael-Hagen/abliterador)",
                "Accept": "application/json,text/plain,*/*",
            }
        )
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def search(self, query: str, limit: int | None = None) -> list[dict[str, str]]:
        q = (query or "").strip()
        if not q:
            return []

        result_limit = max(1, min(limit or self.max_results, 10))
        now = time.monotonic()
        cached = self._cache.get(q.lower())
        if cached and now < cached[0]:
            return [self._to_dict(item) for item in cached[1][:result_limit]]

        results: list[WebSearchResult] = []
        success_calls = 0
        errors: list[str] = []

        try:
            results = self._search_duckduckgo(q, result_limit)
            success_calls += 1
        except Exception as exc:
            errors.append(f"duckduckgo: {exc}")

        if len(results) < result_limit:
            try:
                wiki = self._search_wikipedia(q, result_limit)
                success_calls += 1
            except Exception as exc:
                errors.append(f"wikipedia: {exc}")
                wiki = []

            existing = {item.url for item in results}
            for item in wiki:
                if item.url not in existing:
                    results.append(item)
                if len(results) >= result_limit:
                    break

        if not results and errors and success_calls == 0:
            raise RuntimeError("; ".join(errors))

        results = results[:result_limit]
        self._cache[q.lower()] = (now + self.ttl_s, results)
        return [self._to_dict(item) for item in results]

    def _to_dict(self, item: WebSearchResult) -> dict[str, str]:
        return {
            "title": item.title,
            "url": item.url,
            "snippet": item.snippet,
            "source": item.source,
        }

    def _search_duckduckgo(self, query: str, limit: int) -> list[WebSearchResult]:
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "no_redirect": 1,
        }
        response = self._session.get("https://api.duckduckgo.com/", params=params, timeout=self.timeout_s)
        response.raise_for_status()
        data = response.json() if response.content else {}

        out: list[WebSearchResult] = []
        abstract = str(data.get("AbstractText", "")).strip()
        abstract_url = str(data.get("AbstractURL", "")).strip()
        heading = str(data.get("Heading", "")).strip() or "DuckDuckGo"
        if abstract and abstract_url:
            out.append(
                WebSearchResult(
                    title=heading,
                    url=abstract_url,
                    snippet=abstract,
                    source="duckduckgo",
                )
            )

        def append_topic(topic: dict) -> None:
            text = str(topic.get("Text", "")).strip()
            url = str(topic.get("FirstURL", "")).strip()
            if text and url:
                out.append(
                    WebSearchResult(
                        title=text.split(" - ", 1)[0][:120] or "DuckDuckGo",
                        url=url,
                        snippet=text[:500],
                        source="duckduckgo",
                    )
                )

        for item in data.get("RelatedTopics", []) or []:
            if isinstance(item, dict) and isinstance(item.get("Topics"), list):
                for nested in item.get("Topics"):
                    if isinstance(nested, dict):
                        append_topic(nested)
                        if len(out) >= limit:
                            return out
            elif isinstance(item, dict):
                append_topic(item)
                if len(out) >= limit:
                    return out

        return out

    def _search_wikipedia(self, query: str, limit: int) -> list[WebSearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": 1,
            "format": "json",
            "srlimit": limit,
        }
        response = self._session.get("https://es.wikipedia.org/w/api.php", params=params, timeout=self.timeout_s)
        response.raise_for_status()
        data = response.json() if response.content else {}

        out: list[WebSearchResult] = []
        for item in data.get("query", {}).get("search", []) or []:
            title = str(item.get("title", "")).strip() or "Wikipedia"
            page_id = item.get("pageid")
            snippet = _strip_html(str(item.get("snippet", "")))
            if page_id is None:
                continue
            out.append(
                WebSearchResult(
                    title=title,
                    url=f"https://es.wikipedia.org/?curid={page_id}",
                    snippet=snippet[:500],
                    source="wikipedia",
                )
            )
            if len(out) >= limit:
                break
        return out