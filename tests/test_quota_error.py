import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

# Provide dummy google modules so recursive_agent can be imported
google = types.ModuleType("google")
generativeai = types.ModuleType("generativeai")
class DummyModel:
    def __init__(self, *a, **k):
        pass

generativeai.GenerativeModel = DummyModel

api_core = types.ModuleType("api_core")
exc_mod = types.ModuleType("exceptions")
class QuotaError(Exception):
    pass
exc_mod.ResourceExhausted = QuotaError
api_core.exceptions = exc_mod

google.generativeai = generativeai
google.api_core = api_core
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.generativeai", generativeai)
sys.modules.setdefault("google.api_core", api_core)
sys.modules.setdefault("google.api_core.exceptions", exc_mod)

from recursive_agent import RecursiveAgent  # noqa: E402
from command_executor import CommandExecutor  # noqa: E402
from context_manager import ContextManager  # noqa: E402
from output_manager import OutputManager  # noqa: E402
from agent_state import AgentState  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402


def test_quota_error_aborts(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    cm = ContextManager(cfg, logger, om)
    ce = CommandExecutor(logger)
    state = AgentState(cfg, logger)

    agent = RecursiveAgent(
        config=cfg,
        error_logger=logger,
        command_executor=ce,
        context_manager=cm,
        output_manager=om,
        agent_state=state,
        model_name="dummy",
        topic="t",
        loops=1,
        temperature=0.0,
        seed=None,
        rpm=10,
        api_key="x",
    )

    monkeypatch.setattr(
        agent,
        "_stream_generation",
        lambda prompt: (_ for _ in ()).throw(QuotaError("quota exceeded")),
    )

    events = list(agent.run())
    assert events and events[0][0] == "error"
    assert "quota" in events[0][3][0].lower()
