from types import SimpleNamespace

from abliterador_web.desktop_launcher import launch_desktop_gui


def test_gui_launch_uses_env_command_if_configured(monkeypatch):
    launched = {"cmd": None}

    def fake_popen(cmd, **kwargs):
        launched["cmd"] = cmd

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    settings = SimpleNamespace(gui_launch_command="echo launch")

    out = launch_desktop_gui(settings)
    assert out == "echo launch"
    assert launched["cmd"] == "echo launch"


def test_gui_launch_raises_if_no_target(monkeypatch):
    monkeypatch.setattr("abliterador_web.desktop_launcher.find_gui_launch_targets", lambda: [])
    settings = SimpleNamespace(gui_launch_command="")

    try:
        launch_desktop_gui(settings)
    except FileNotFoundError:
        assert True
        return

    assert False, "Expected FileNotFoundError when no GUI target is available"
