import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

import utils  # noqa: E402


def test_save_and_load(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    monkeypatch.setattr(utils, "KEYS_PATH", str(path))
    utils.save_api_key("main", "ABC", "desc")
    keys = utils.load_api_keys()
    assert keys == [{"name": "main", "key": "ABC", "description": "desc"}]
    utils.save_api_key("main", "XYZ", "new")
    keys = utils.load_api_keys()
    assert keys[0]["key"] == "XYZ"
    assert keys[0]["description"] == "new"


def test_pref_key(tmp_path, monkeypatch):
    prefs = tmp_path / "prefs.json"
    monkeypatch.setattr(utils, "PREFS_PATH", str(prefs))
    utils.save_pref_key("k1")
    choice = utils.load_pref_key(["k0", "k1"])
    assert choice == "k1"
