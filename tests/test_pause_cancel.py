import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from command_executor import CommandExecutor  # noqa: E402
from command_registration import register_core_commands  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_cancel_with_reason():
    cfg = Config()
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)
    register_core_commands(ce)

    results = ce.parse_and_execute('[[COMMAND: CANCEL reason="stop"]]')
    assert results == [("CANCEL", "stop")]


def test_pause_requires_reason():
    cfg = Config()
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)
    register_core_commands(ce)

    results = ce.parse_and_execute('[[COMMAND: PAUSE]]')
    assert results and results[0][1].startswith("ERROR:")

