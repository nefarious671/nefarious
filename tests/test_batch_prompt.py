import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from command_executor import CommandExecutor  # noqa: E402
from command_registration import register_core_commands  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_multiple_io_in_single_prompt(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    ce = CommandExecutor(logger)
    monkeypatch.setattr("handlers._cfg", cfg)
    monkeypatch.setattr("handlers._output_mgr", om)
    register_core_commands(ce)

    text = (
        '[[COMMAND: WRITE_FILE filename="batch.txt" content="hello"]]'
        '[[COMMAND: APPEND_FILE filename="batch.txt" content=" world"]]'
        '[[COMMAND: READ_FILE filename="batch.txt"]]'
    )
    results = ce.parse_and_execute(text)
    assert len(results) == 3
    assert "Appended" in results[1][1]
    assert "hello world" in results[2][1]
