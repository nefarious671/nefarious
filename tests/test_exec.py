import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)  # noqa: E402

from handlers import EXEC  # noqa: E402


def test_exec_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = EXEC({"cmd": "sleep 20"})
    assert "timed out" in result


def test_exec_success(monkeypatch):
    def fake_run(*args, **kwargs):
        class Res:
            stdout = "ok"
            stderr = ""
        return Res()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = EXEC({"cmd": "echo ok"})
    assert result == "ok"
