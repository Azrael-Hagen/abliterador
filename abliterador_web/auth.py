import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str


class TokenAuth:
    def __init__(self, secret: str, token_ttl_seconds: int = 60 * 60 * 8):
        self.secret = secret.encode("utf-8")
        self.token_ttl_seconds = token_ttl_seconds

    def _sign(self, payload_bytes: bytes) -> str:
        digest = hmac.new(self.secret, payload_bytes, hashlib.sha256).hexdigest()
        return digest

    def issue_token(self, username: str, role: str) -> str:
        payload = {
            "sub": username,
            "role": role,
            "exp": int(time.time()) + self.token_ttl_seconds,
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = self._sign(payload_bytes)
        token_raw = base64.urlsafe_b64encode(payload_bytes).decode("ascii") + "." + signature
        return token_raw

    def verify_token(self, token: str) -> AuthUser:
        try:
            payload_b64, signature = token.split(".", 1)
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
            expected = self._sign(payload_bytes)
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid signature")
            payload = json.loads(payload_bytes.decode("utf-8"))
            if int(payload.get("exp", 0)) < int(time.time()):
                raise ValueError("Token expired")
            username = str(payload.get("sub", "")).strip()
            role = str(payload.get("role", "user")).strip() or "user"
            if not username:
                raise ValueError("Invalid subject")
            return AuthUser(username=username, role=role)
        except Exception as exc:
            raise ValueError("Invalid token") from exc
