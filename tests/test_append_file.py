import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from handlers import APPEND_FILE, WRITE_FILE, READ_FILE  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_append_file_success(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)

    WRITE_FILE({"filename": "file.txt", "content": "first\n"})
    result = APPEND_FILE({"filename": "file.txt", "content": "second"})
    assert "Appended" in result
    with open(os.path.join(tmp_path, "file.txt"), "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "first\nsecond"


def test_append_file_missing(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)

    result = APPEND_FILE({"filename": "nofile.txt", "content": "x"})
    assert "does not exist" in result


def test_write_file_dry_run(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)

    result = WRITE_FILE({"filename": "x.txt", "content": "hi", "dry_run": "true"})
    assert "DRY RUN" in result
    assert not os.path.exists(os.path.join(tmp_path, "x.txt"))


def test_read_file_truncation(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)

    lines = "\n".join(str(i) for i in range(20))
    WRITE_FILE({"filename": "big.txt", "content": lines})
    result = READ_FILE({"filename": "big.txt"})
    assert result.startswith("WARNING:")
    assert "CONTENT_START" in result
