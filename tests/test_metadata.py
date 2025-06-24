import os
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_save_session_metadata(tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    meta = {"topic": "t", "loops": 1}
    path = om.save_session_metadata(meta)
    assert os.path.isfile(path)
    with open(path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == meta
