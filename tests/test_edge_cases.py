import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from command_executor import CommandExecutor  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from context_manager import ContextManager  # noqa: E402
from handlers import READ_LINES, EXEC  # noqa: E402


def test_parse_invalid_args():
    cfg = Config()
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)

    def foo(args):
        return "ok"

    ce.register_command("FOO", foo)
    # Missing closing quote should produce no results
    results = ce.parse_and_execute('[[COMMAND: FOO val="broken]]')
    assert results == []


def test_upload_unsupported_extension(tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    cm = ContextManager(cfg, logger, om)
    cm.upload_context("notes.pdf", b"content")
    assert cm.get_context() == ""


def test_save_output_fallback(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)

    real_open = open
    call_count = {"n": 0}

    def open_side_effect(path, mode="r", *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError("fail")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", open_side_effect)
    path = om.save_output("file.md", "data")
    assert os.path.isfile(path)
    assert "output_" in os.path.basename(path)


def test_read_lines_bad_range(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr("handlers._cfg", cfg)
    monkeypatch.setattr("handlers._output_mgr", om)
    file_path = os.path.join(tmp_path, "s.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("one\ntwo\n")
    result = READ_LINES({"filename": "s.txt", "start": "a"})
    assert "start and end" in result


def test_read_lines_negative_start(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr("handlers._cfg", cfg)
    monkeypatch.setattr("handlers._output_mgr", om)
    file_path = os.path.join(tmp_path, "neg.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("one\ntwo\nthree\n")
    result = READ_LINES({"filename": "neg.txt", "start": "-1", "end": "2"})
    assert "Invalid line range" in result


def test_read_lines_end_before_start(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr("handlers._cfg", cfg)
    monkeypatch.setattr("handlers._output_mgr", om)
    file_path = os.path.join(tmp_path, "rev.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("1\n2\n3\n")
    result = READ_LINES({"filename": "rev.txt", "start": "3", "end": "2"})
    assert "Invalid line range" in result


def test_exec_banned_pattern():
    result = EXEC({"cmd": "sudo ls"})
    assert "prohibited" in result
