import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from command_executor import CommandExecutor  # noqa: E402
from command_registration import register_core_commands  # noqa: E402
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
    assert "RUN_PYTHON" in result


def test_rl_alias(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    ce = CommandExecutor(logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    register_core_commands(ce)

    file_path = os.path.join(tmp_path, "sample.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("a\nb\nc\n")

    expected = READ_LINES({"filename": "sample.txt", "start": "1", "end": "2"})
    results = ce.parse_and_execute(
        '[[COMMAND: RL filename="sample.txt" start="1" end="2"]]'
    )
    assert results
    cmd, output = results[0]
    assert cmd == "RL"
    assert output == expected
