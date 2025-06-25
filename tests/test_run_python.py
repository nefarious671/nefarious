import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from handlers import RUN_PYTHON  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_run_python_success(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)

    result = RUN_PYTHON({"code": "print('hi')"})
    assert "hi" in result


def test_run_python_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python", timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = RUN_PYTHON({"code": "print('x')"})
    assert "timed out" in result


def test_run_python_missing():
    result = RUN_PYTHON({})
    assert "Missing required" in result
