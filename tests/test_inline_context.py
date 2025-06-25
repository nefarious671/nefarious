import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from context_manager import ContextManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from config import Config  # noqa: E402


def test_inline_message_added(tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    cm = ContextManager(cfg, logger, om)

    cm.add_inline_context("hello world")
    ctx = cm.get_context()
    assert "hello world" in ctx
