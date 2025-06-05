from agent_state import AgentState
from config import Config
from error_logger import ErrorLogger

cfg = Config()
logger = ErrorLogger(cfg)
state = AgentState(cfg, logger)

# Explicitly reset loop index so run() will start at loop 1 again:
state.delete_state("current_loop")
# If you also want a completely fresh history:
state.delete_state("history")
state.delete_state("last_thought")
state.save_state()
