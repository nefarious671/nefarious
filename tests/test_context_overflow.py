import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from context_manager import ContextManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from config import Config  # noqa: E402


def test_drop_oldest_when_exceeding_limit(tmp_path):
    cfg = Config(max_context_tokens=80, safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    cm = ContextManager(cfg, logger, om)

    cm.upload_context("one.txt", b"A" * 50)
    cm.upload_context("two.txt", b"B" * 50)
    ctx = cm.get_context()
    assert "two.txt" in ctx
    assert "one.txt" not in ctx
