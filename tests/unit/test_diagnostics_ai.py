from pathlib import Path
from types import SimpleNamespace

from abliterador_web.diagnostics_ai import MiniAIDiagnosticsEngine


class BrokenOllama:
    def list_models(self):
        raise RuntimeError("offline")


class HealthyOllama:
    def list_models(self):
        return ["qwen2.5:7b"]


def _settings(tmp_path: Path):
    return SimpleNamespace(
        users_db_path=tmp_path / "users.json",
        user_workspaces_root=tmp_path / "workspaces",
        username="admin",
        password="change_me_now",
        secret="replace-me-with-random-secret",
        gui_launch_command="",
    )


def test_ai_diagnostics_detects_issues_and_tracks_learning(tmp_path: Path, monkeypatch):
    memory = tmp_path / "memory.json"
    engine = MiniAIDiagnosticsEngine(memory)
    settings = _settings(tmp_path)
    monkeypatch.setattr("abliterador_web.diagnostics_ai.find_gui_launch_targets", lambda: [])

    result = engine.check(settings, BrokenOllama())

    codes = {item["code"] for item in result["findings"]}
    assert "ollama_unreachable" in codes
    assert "users_db_missing" in codes
    assert "default_admin_credentials" in codes
    assert "default_signing_secret" in codes
    assert memory.exists()


def test_ai_diagnostics_repair_creates_user_db_and_workspace(tmp_path: Path, monkeypatch):
    memory = tmp_path / "memory.json"
    engine = MiniAIDiagnosticsEngine(memory)
    settings = _settings(tmp_path)
    monkeypatch.setattr("abliterador_web.diagnostics_ai.find_gui_launch_targets", lambda: [])

    repair = engine.run_repair(
        settings,
        HealthyOllama(),
        requested_actions=["create_users_db", "ensure_workspace_root"],
    )

    assert settings.users_db_path.exists()
    assert settings.user_workspaces_root.exists()
    assert any(item["action"] == "create_users_db" and item["ok"] for item in repair["executed"])
    assert any(item["action"] == "ensure_workspace_root" and item["ok"] for item in repair["executed"])
