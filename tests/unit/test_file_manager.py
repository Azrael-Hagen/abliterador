"""Unit tests for FileManager."""

import pytest
from pathlib import Path
from abliterador_web.file_manager import FileManager


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def file_manager(temp_workspace):
    """Create FileManager instance."""
    return FileManager(temp_workspace)


def test_init_creates_root(temp_workspace):
    """FileManager should create root directory."""
    fm = FileManager(temp_workspace)
    assert fm.root.exists()


def test_list_empty_directory(file_manager):
    """Listing empty directory should return empty list."""
    files = file_manager.list_files("")
    assert files == []


def test_list_files_with_metadata(file_manager, temp_workspace):
    """List files should include metadata."""
    (temp_workspace / "test.txt").write_text("hello")
    files = file_manager.list_files("")
    assert len(files) == 1
    assert files[0].name == "test.txt"
    assert files[0].size_bytes > 0
    assert files[0].file_type == ".txt"


def test_create_folder(file_manager):
    """Should create nested folders."""
    path = file_manager.create_folder("data/models")
    assert path == "data/models"
    assert (file_manager.root / "data" / "models").exists()


def test_path_traversal_protection(file_manager):
    """Should prevent directory traversal attacks."""
    with pytest.raises(ValueError, match="traversal"):
        file_manager._resolve_safe("../../etc/passwd")


def test_copy_file(file_manager, temp_workspace):
    """Should copy files correctly."""
    src_file = temp_workspace / "source.txt"
    src_file.write_text("data")
    
    new_path = file_manager.copy_file("source.txt", "dest.txt")
    assert new_path == "dest.txt"
    assert (temp_workspace / "dest.txt").exists()
    assert (temp_workspace / "dest.txt").read_text() == "data"


def test_move_file(file_manager, temp_workspace):
    """Should move/rename files."""
    src_file = temp_workspace / "original.txt"
    src_file.write_text("content")
    
    new_path = file_manager.move_file("original.txt", "renamed.txt")
    assert not (temp_workspace / "original.txt").exists()
    assert (temp_workspace / "renamed.txt").exists()


def test_delete_file(file_manager, temp_workspace):
    """Should delete files."""
    test_file = temp_workspace / "delete_me.txt"
    test_file.write_text("bye")
    
    assert file_manager.delete_file("delete_me.txt")
    assert not test_file.exists()


def test_get_preview_text_file(file_manager, temp_workspace):
    """Should preview text files."""
    test_file = temp_workspace / "data.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3")
    
    preview = file_manager.get_preview("data.txt")
    assert preview["content"] != ""
    assert "Line 1" in preview["content"]
    assert preview["truncated"] == False


def test_get_preview_unsupported(file_manager, temp_workspace):
    """Should refuse to preview binary files."""
    binary_file = temp_workspace / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02")
    
    preview = file_manager.get_preview("binary.bin")
    assert preview["content"] == ""
    assert "not supported" in preview.get("reason", "").lower()


def test_search_files(file_manager, temp_workspace):
    """Should search for files by name."""
    (temp_workspace / "test1.txt").write_text("a")
    (temp_workspace / "test2.txt").write_text("b")
    (temp_workspace / "data.json").write_text("c")
    
    results = file_manager.search("test")
    assert len(results) == 2
    assert all("test" in r.name.lower() for r in results)


def test_format_size():
    """Should format sizes correctly."""
    assert FileManager._format_size(512) == "512.0 B"
    assert FileManager._format_size(1024) == "1.0 KB"
    assert FileManager._format_size(1024 * 1024) == "1.0 MB"
