from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path


ROLE_CATALOG: dict[str, list[str]] = {
    "admin": [
        "chat",
        "files",
        "manage_users",
        "manage_models",
        "launch_gui",
        "self_heal",
    ],
    "manager": ["chat", "files", "manage_models", "self_heal"],
    "operator": ["chat", "files", "manage_models"],
    "viewer": ["chat"],
}


@dataclass(frozen=True)
class UserProfile:
    username: str
    role: str
    active: bool = True
    permissions: list[str] | None = None


class UserStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._write_raw({"users": []})

    def _read_raw(self) -> dict:
        with self.db_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {"users": []}
        users = data.get("users")
        if not isinstance(users, list):
            data["users"] = []
        return data

    def _write_raw(self, data: dict) -> None:
        with self.db_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=True)

    def role_catalog(self) -> dict[str, list[str]]:
        return {key: list(value) for key, value in ROLE_CATALOG.items()}

    def _validate_role(self, role: str) -> str:
        clean = role.strip().lower()
        if clean not in ROLE_CATALOG:
            raise ValueError("invalid role")
        return clean

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")

    @staticmethod
    def _verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
        try:
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(hash_b64.encode("ascii"))
            got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
            return hmac.compare_digest(got, expected)
        except Exception:
            return False

    def ensure_admin(self, username: str, password: str) -> None:
        if self.get_user(username):
            return
        self.create_user(username=username, password=password, role="admin")

    def list_users(self) -> list[UserProfile]:
        data = self._read_raw()
        profiles = []
        for row in data.get("users", []):
            username = str(row.get("username", "")).strip()
            role = str(row.get("role", "viewer")).strip().lower() or "viewer"
            if role not in ROLE_CATALOG:
                role = "viewer"
            active = bool(row.get("active", True))
            if username:
                profiles.append(
                    UserProfile(
                        username=username,
                        role=role,
                        active=active,
                        permissions=list(ROLE_CATALOG.get(role, [])),
                    )
                )
        return profiles

    def get_user(self, username: str) -> UserProfile | None:
        uname = username.strip().lower()
        for user in self.list_users():
            if user.username.lower() == uname:
                return user
        return None

    def create_user(self, username: str, password: str, role: str = "user") -> UserProfile:
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("username required")
        role = self._validate_role(role)
        if self.get_user(clean_username):
            raise ValueError("user already exists")

        salt_b64, hash_b64 = self._hash_password(password)
        data = self._read_raw()
        data["users"].append(
            {
                "username": clean_username,
                "role": role,
                "active": True,
                "password_salt": salt_b64,
                "password_hash": hash_b64,
            }
        )
        self._write_raw(data)
        return UserProfile(
            username=clean_username,
            role=role,
            active=True,
            permissions=list(ROLE_CATALOG[role]),
        )

    def register_user(self, username: str, password: str) -> UserProfile:
        return self.create_user(username=username, password=password, role="viewer")

    def update_user_role(self, username: str, role: str) -> UserProfile:
        clean_role = self._validate_role(role)
        uname = username.strip().lower()
        data = self._read_raw()
        for row in data.get("users", []):
            row_username = str(row.get("username", "")).strip()
            if row_username.lower() != uname:
                continue
            row["role"] = clean_role
            self._write_raw(data)
            return UserProfile(
                username=row_username,
                role=clean_role,
                active=bool(row.get("active", True)),
                permissions=list(ROLE_CATALOG[clean_role]),
            )
        raise ValueError("user not found")

    def set_user_active(self, username: str, active: bool) -> UserProfile:
        uname = username.strip().lower()
        data = self._read_raw()
        for row in data.get("users", []):
            row_username = str(row.get("username", "")).strip()
            if row_username.lower() != uname:
                continue
            row["active"] = bool(active)
            role = str(row.get("role", "viewer")).strip().lower() or "viewer"
            if role not in ROLE_CATALOG:
                role = "viewer"
            self._write_raw(data)
            return UserProfile(
                username=row_username,
                role=role,
                active=bool(active),
                permissions=list(ROLE_CATALOG[role]),
            )
        raise ValueError("user not found")

    def delete_user(self, username: str) -> None:
        uname = username.strip().lower()
        data = self._read_raw()
        old = data.get("users", [])
        kept = [row for row in old if str(row.get("username", "")).strip().lower() != uname]
        if len(kept) == len(old):
            raise ValueError("user not found")
        data["users"] = kept
        self._write_raw(data)

    def verify_credentials(self, username: str, password: str) -> UserProfile | None:
        uname = username.strip().lower()
        data = self._read_raw()
        for row in data.get("users", []):
            row_username = str(row.get("username", "")).strip()
            if row_username.lower() != uname:
                continue
            if not bool(row.get("active", True)):
                return None
            salt_b64 = str(row.get("password_salt", ""))
            hash_b64 = str(row.get("password_hash", ""))
            if self._verify_password(password, salt_b64, hash_b64):
                role = str(row.get("role", "viewer")).strip().lower() or "viewer"
                if role not in ROLE_CATALOG:
                    role = "viewer"
                return UserProfile(
                    username=row_username,
                    role=role,
                    active=True,
                    permissions=list(ROLE_CATALOG[role]),
                )
            return None
        return None
