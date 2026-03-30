from abliterador_web.web_search import WebSearchService


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.content = b"{}"

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_web_search_uses_duckduckgo_and_wikipedia_fallback(monkeypatch):
    service = WebSearchService(timeout_s=3, ttl_s=120, max_results=4)
    calls = {"count": 0}

    def fake_get(url, params=None, timeout=None):
        calls["count"] += 1
        if "duckduckgo" in url:
            return DummyResponse(
                {
                    "AbstractText": "Resumen principal",
                    "AbstractURL": "https://example.com/main",
                    "Heading": "Tema Principal",
                    "RelatedTopics": [],
                }
            )
        return DummyResponse(
            {
                "query": {
                    "search": [
                        {
                            "title": "Articulo Wiki",
                            "pageid": 123,
                            "snippet": "<b>Dato</b> actualizado",
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(service._session, "get", fake_get)
    rows = service.search("noticia tecnologica", limit=3)

    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/main"
    assert rows[1]["url"] == "https://es.wikipedia.org/?curid=123"
    assert "Dato actualizado" in rows[1]["snippet"]

    cached = service.search("noticia tecnologica", limit=3)
    assert len(cached) == 2
    assert calls["count"] == 2
