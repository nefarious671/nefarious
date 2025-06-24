import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from handlers import WORD_COUNT  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_word_count(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    file_path = os.path.join(tmp_path, 'sample.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('hello world\nsecond line')
    result = WORD_COUNT({'filename': 'sample.txt'})
    assert '2 lines' in result and '4 words' in result


def test_word_count_missing(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    result = WORD_COUNT({'filename': 'none.txt'})
    assert 'does not exist' in result
