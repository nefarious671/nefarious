import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)  # noqa: E402

from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402

def test_sanitize_filename_basic():
    cfg = Config()
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    assert om.sanitize_filename("my file.txt") == "my_file.txt"

def test_sanitize_filename_extension():
    cfg = Config()
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    assert om.sanitize_filename("weird.exe") == "weird.txt"
