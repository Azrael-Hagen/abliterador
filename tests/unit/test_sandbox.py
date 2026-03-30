from pathlib import Path

import pytest

from abliterador_web.sandbox import FileSandbox, SandboxError


@pytest.fixture()
def sandbox(tmp_path: Path) -> FileSandbox:
    root = tmp_path / "allowed"
    root.mkdir(parents=True, exist_ok=True)
    return FileSandbox([root])


def test_write_and_read_file(sandbox: FileSandbox):
    sandbox.write_text("notes/hello.txt", "hola")
    assert sandbox.read_text("notes/hello.txt") == "hola"


def test_list_dir(sandbox: FileSandbox):
    sandbox.write_text("a.txt", "a")
    sandbox.write_text("z.txt", "z")
    entries = sandbox.list_dir(".")
    assert "a.txt" in entries
    assert "z.txt" in entries


def test_reject_path_traversal(sandbox: FileSandbox):
    with pytest.raises(SandboxError):
        sandbox.write_text("../escape.txt", "boom")


def test_reject_absolute_path(sandbox: FileSandbox):
    with pytest.raises(SandboxError):
        sandbox.read_text("C:/Windows/system.ini")
