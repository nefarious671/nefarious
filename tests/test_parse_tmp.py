import os
import importlib.util
import sys
import types

ROOT = os.path.dirname(os.path.dirname(__file__))

# Stub external dependencies so laser_lens modules can be imported without them
streamlit_stub = types.ModuleType("streamlit")
streamlit_stub.cache_resource = lambda **kw: (lambda f: f)
streamlit_stub.warning = lambda *a, **kw: None
streamlit_stub.rerun = lambda: None
sys.modules.setdefault("streamlit", streamlit_stub)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_stub)

genai_stub = types.ModuleType("generativeai")
genai_stub.configure = lambda **kw: None
genai_stub.list_models = lambda: []

google_stub = types.ModuleType("google")
google_stub.generativeai = genai_stub
sys.modules.setdefault("google", google_stub)
sys.modules.setdefault("google.generativeai", genai_stub)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

laser_lens = load_module(os.path.join(ROOT, "laser_lens", "laser_lens.py"), "laser_lens")
laser_lens_v2 = load_module(os.path.join(ROOT, "laser_lens", "laser_lens_v2.py"), "laser_lens_v2")


def test_parse_tmp_empty():
    assert laser_lens.parse_tmp("") == ([], "")
    assert laser_lens_v2.parse_tmp("") == ([], "")


def test_parse_tmp_partial_segment():
    raw1 = f"One{laser_lens.DELIM}Two{laser_lens.DELIM}Part"
    assert laser_lens.parse_tmp(raw1) == (["One", "Two"], "Part")

    raw2 = f"One{laser_lens_v2.CONFIG.delim}Two{laser_lens_v2.CONFIG.delim}Part"
    assert laser_lens_v2.parse_tmp(raw2) == (["One", "Two"], "Part")
