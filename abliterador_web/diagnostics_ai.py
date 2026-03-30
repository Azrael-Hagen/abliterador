from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from abliterador_web.config import WebSettings
from abliterador_web.desktop_launcher import find_gui_launch_targets
from abliterador_web.ollama_client import OllamaClient


class MiniAIDiagnosticsEngine:
    def __init__(self, memory_path: Path):
        self.memory_path = memory_path.resolve()
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if self.memory_path.exists():
            try:
                with self.memory_path.open("r", encoding="utf-8") as fh:
                    obj = json.load(fh)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        return {
            "issue_stats": {},
            "action_stats": {},
            "history": [],
        }

    def _save_state(self) -> None:
        with self.memory_path.open("w", encoding="utf-8") as fh:
            json.dump(self._state, fh, indent=2, ensure_ascii=True)

    def _mark_issue_seen(self, issue_code: str) -> None:
        row = self._state["issue_stats"].setdefault(issue_code, {"seen": 0, "resolved": 0})
        row["seen"] += 1

    def _mark_issue_resolved(self, issue_code: str) -> None:
        row = self._state["issue_stats"].setdefault(issue_code, {"seen": 0, "resolved": 0})
        row["resolved"] += 1

    def _action_success_rate(self, action: str) -> float:
        row = self._state["action_stats"].get(action, {})
        attempts = int(row.get("attempts", 0))
        success = int(row.get("success", 0))
        return (success + 1) / (attempts + 2)

    def _record_action_result(self, action: str, ok: bool, detail: str) -> None:
        row = self._state["action_stats"].setdefault(action, {"attempts": 0, "success": 0})
        row["attempts"] += 1
        if ok:
            row["success"] += 1
        self._state["history"].append({"action": action, "ok": ok, "detail": detail})
        self._state["history"] = self._state["history"][-80:]

    def _recommended_actions(self, issue_code: str) -> list[str]:
        mapping = {
            "ollama_unreachable": ["start_ollama_service"],
            "users_db_missing": ["create_users_db"],
            "users_db_permissions": ["fix_users_db_permissions_hint"],
            "workspace_root_missing": ["ensure_workspace_root"],
            "workspace_root_permissions": ["fix_workspace_permissions_hint"],
            "gui_not_available": ["configure_gui_launch_command_hint"],
            "default_admin_credentials": ["rotate_admin_credentials_hint"],
            "default_signing_secret": ["rotate_signing_secret_hint"],
        }
        actions = list(mapping.get(issue_code, []))
        actions.sort(key=self._action_success_rate, reverse=True)
        return actions

    def check(self, settings: WebSettings, ollama: OllamaClient) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []

        try:
            _ = ollama.list_models()
        except Exception:
            findings.append(
                {
                    "code": "ollama_unreachable",
                    "severity": "high",
                    "message": "Ollama no responde en el endpoint configurado.",
                }
            )

        if not settings.users_db_path.exists():
            findings.append(
                {
                    "code": "users_db_missing",
                    "severity": "high",
                    "message": "La base de usuarios no existe.",
                }
            )
        elif not os.access(settings.users_db_path, os.R_OK | os.W_OK):
            findings.append(
                {
                    "code": "users_db_permissions",
                    "severity": "high",
                    "message": "La base de usuarios no tiene permisos de lectura/escritura.",
                }
            )

        if not settings.user_workspaces_root.exists():
            findings.append(
                {
                    "code": "workspace_root_missing",
                    "severity": "medium",
                    "message": "La raiz de workspaces de usuarios no existe.",
                }
            )
        elif not os.access(settings.user_workspaces_root, os.R_OK | os.W_OK | os.X_OK):
            findings.append(
                {
                    "code": "workspace_root_permissions",
                    "severity": "high",
                    "message": "La raiz de workspaces no tiene permisos suficientes.",
                }
            )

        if not find_gui_launch_targets() and not settings.gui_launch_command:
            findings.append(
                {
                    "code": "gui_not_available",
                    "severity": "medium",
                    "message": "No se detecto GUI de escritorio para lanzamiento remoto.",
                }
            )

        if settings.username == "admin" and settings.password == "change_me_now":
            findings.append(
                {
                    "code": "default_admin_credentials",
                    "severity": "critical",
                    "message": "El sistema sigue usando credenciales admin por defecto.",
                }
            )

        if settings.secret == "replace-me-with-random-secret":
            findings.append(
                {
                    "code": "default_signing_secret",
                    "severity": "critical",
                    "message": "El secret de firmado de tokens esta en valor por defecto.",
                }
            )

        for finding in findings:
            code = finding["code"]
            self._mark_issue_seen(code)
            finding["recommended_actions"] = self._recommended_actions(code)

        self._save_state()
        return {
            "ok": len(findings) == 0,
            "findings": findings,
            "learning": {
                "issue_stats": self._state.get("issue_stats", {}),
                "action_stats": self._state.get("action_stats", {}),
            },
        }

    def _apply_action(self, action: str, settings: WebSettings) -> tuple[bool, str]:
        try:
            if action == "start_ollama_service":
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "Se ejecuto 'ollama serve'."

            if action == "create_users_db":
                settings.users_db_path.parent.mkdir(parents=True, exist_ok=True)
                if not settings.users_db_path.exists():
                    settings.users_db_path.write_text('{"users": []}', encoding="utf-8")
                return True, "Base de usuarios creada o validada."

            if action == "ensure_workspace_root":
                settings.user_workspaces_root.mkdir(parents=True, exist_ok=True)
                return True, "Raiz de workspaces creada o validada."

            if action.endswith("_hint"):
                return False, "Accion manual recomendada en configuracion."

            return False, "Accion no reconocida."
        except Exception as exc:
            return False, str(exc)

    def run_repair(
        self,
        settings: WebSettings,
        ollama: OllamaClient,
        requested_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        pre = self.check(settings, ollama)
        actions_to_run: list[str] = []

        if requested_actions:
            actions_to_run = [item.strip() for item in requested_actions if item.strip()]
        else:
            for finding in pre["findings"]:
                for action in finding.get("recommended_actions", []):
                    if action not in actions_to_run:
                        actions_to_run.append(action)

        executed: list[dict[str, Any]] = []
        for action in actions_to_run:
            ok, detail = self._apply_action(action, settings)
            self._record_action_result(action, ok, detail)
            executed.append({"action": action, "ok": ok, "detail": detail})

        post = self.check(settings, ollama)
        pre_codes = {item["code"] for item in pre["findings"]}
        post_codes = {item["code"] for item in post["findings"]}
        for code in sorted(pre_codes - post_codes):
            self._mark_issue_resolved(code)

        self._save_state()
        return {
            "executed": executed,
            "before": pre,
            "after": post,
        }