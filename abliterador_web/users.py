from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserProfile:
    username: str
    role: str


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
            role = str(row.get("role", "user")).strip() or "user"
            if username:
                profiles.append(UserProfile(username=username, role=role))
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
        if role not in {"admin", "user"}:
            raise ValueError("invalid role")
        if self.get_user(clean_username):
            raise ValueError("user already exists")

        salt_b64, hash_b64 = self._hash_password(password)
        data = self._read_raw()
        data["users"].append(
            {
                "username": clean_username,
                "role": role,
                "password_salt": salt_b64,
                "password_hash": hash_b64,
            }
        )
        self._write_raw(data)
        return UserProfile(username=clean_username, role=role)

    def verify_credentials(self, username: str, password: str) -> UserProfile | None:
        uname = username.strip().lower()
        data = self._read_raw()
        for row in data.get("users", []):
            row_username = str(row.get("username", "")).strip()
            if row_username.lower() != uname:
                continue
            salt_b64 = str(row.get("password_salt", ""))
            hash_b64 = str(row.get("password_hash", ""))
            if self._verify_password(password, salt_b64, hash_b64):
                role = str(row.get("role", "user")).strip() or "user"
                return UserProfile(username=row_username, role=role)
            return None
        return None
