from pathlib import Path

from abliterador_web.web_knowledge import WebKnowledgeStore


def test_web_knowledge_store_persists_and_filters_by_hint(tmp_path: Path):
    path = tmp_path / "web_knowledge.json"
    store = WebKnowledgeStore(path, max_queries=50)

    store.record(
        "python noticias",
        [
            {
                "title": "Python 3.14",
                "url": "https://example.com/python314",
                "snippet": "Nueva version disponible",
                "source": "duckduckgo",
            }
        ],
    )
    store.record(
        "economia global",
        [
            {
                "title": "Mercados",
                "url": "https://example.com/markets",
                "snippet": "Resumen diario",
                "source": "wikipedia",
            }
        ],
    )

    restored = WebKnowledgeStore(path, max_queries=50)
    python_rows = restored.recent("python", limit=3)
    all_rows = restored.recent("", limit=5)

    assert len(python_rows) == 1
    assert python_rows[0]["url"] == "https://example.com/python314"
    assert len(all_rows) == 2
