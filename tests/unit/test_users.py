from pathlib import Path

from abliterador_web.users import UserStore


def test_create_and_verify_user(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)
    store.create_user("alice", "Password123", "viewer")

    ok = store.verify_credentials("alice", "Password123")
    bad = store.verify_credentials("alice", "wrong-pass")

    assert ok is not None
    assert ok.username == "alice"
    assert ok.role == "viewer"
    assert bad is None


def test_ensure_admin(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)
    store.ensure_admin("admin", "TopSecret!123")
    profile = store.verify_credentials("admin", "TopSecret!123")
    assert profile is not None
    assert profile.role == "admin"


def test_update_role_and_active(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)
    store.create_user("alice", "Password123", "viewer")

    updated = store.update_user_role("alice", "manager")
    assert updated.role == "manager"

    disabled = store.set_user_active("alice", False)
    assert disabled.active is False
    assert store.verify_credentials("alice", "Password123") is None


def test_register_user_defaults_to_viewer(tmp_path: Path):
    db = tmp_path / "users.json"
    store = UserStore(db)

    profile = store.register_user("newbie", "Password123")
    assert profile.role == "viewer"
