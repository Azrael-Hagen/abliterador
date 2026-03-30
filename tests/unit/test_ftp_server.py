from pathlib import Path

from abliterador_web.ftp_server import discover_windows_libraries


def test_discover_windows_libraries_returns_existing_only(tmp_path: Path):
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Videos").mkdir()

    found = discover_windows_libraries(tmp_path)
    names = {path.name for path in found}

    assert names == {"Desktop", "Downloads", "Videos"}
