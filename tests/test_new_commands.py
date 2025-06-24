import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from handlers import READ_LINES, HELP  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_read_lines(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    file_path = os.path.join(tmp_path, "sample.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("one\ntwo\nthree\nfour\n")
    result = READ_LINES({"filename": "sample.txt", "start": "2", "end": "3"})
    assert "two" in result and "three" in result


def test_help():
    result = HELP({})
    assert "Available commands" in result
