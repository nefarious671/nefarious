import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from context_manager import ContextManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from config import Config  # noqa: E402


def test_oversize_file_truncated():
    cfg = Config(max_context_tokens=120, safe_output_dir="./test_outputs")
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    cm = ContextManager(cfg, logger, om)
    cm.upload_context("big.txt", b"A" * 200)
    ctx = cm.get_context()
    assert "WARNING:" in ctx
    assert "[truncated]" in ctx
    assert "Context from: big.txt" in ctx
    files = om.list_outputs()
    assert any("full_big.txt" in f for f in files)
