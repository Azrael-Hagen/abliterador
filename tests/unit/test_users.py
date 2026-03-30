from pathlib import Path

from abliterador_web.users import UserStore


def test_create_and_verify_user(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)
    store.create_user("alice", "Password123", "user")

    ok = store.verify_credentials("alice", "Password123")
    bad = store.verify_credentials("alice", "wrong-pass")

    assert ok is not None
    assert ok.username == "alice"
    assert ok.role == "user"
    assert bad is None


def test_ensure_admin(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)
    store.ensure_admin("admin", "TopSecret!123")
    profile = store.verify_credentials("admin", "TopSecret!123")
    assert profile is not None
    assert profile.role == "admin"
