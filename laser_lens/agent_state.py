# agent_state.py

import json
import os
from typing import Any, Dict, Optional

from config import Config
from error_logger import ErrorLogger


class AgentState:
    """
    Maintains a JSON-backed state dictionary for the agent, enabling persistence across runs.
    """

    def __init__(self, config: Config, error_logger: ErrorLogger):
        self.config = config
        self.error_logger = error_logger
        self.state_dir = os.path.expanduser(config.agent_state_dir)
        os.makedirs(self.state_dir, exist_ok=True)
        self.state_path = os.path.join(self.state_dir, "state.json")
        self.state: Dict[str, Any] = {}
        self.load_state()

    def update_state(self, key: str, value: Any) -> None:
        """Sets state[key] = value."""
        self.state[key] = value

    def get_state(self, key: str) -> Optional[Any]:
        """Returns state[key] or None if missing."""
        return self.state.get(key)

    def delete_state(self, key: str) -> None:
        """Deletes a key from state if it exists."""
        if key in self.state:
            del self.state[key]

    def save_state(self) -> None:
        """Writes the state dictionary to a JSON file (atomic write)."""
        try:
            tmp_path = self.state_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp_path, self.state_path)
        except Exception as e:
            self.error_logger.log(
                "ERROR", f"Failed to save agent state to {self.state_path}", e
            )

    def load_state(self) -> None:
        """Loads state from the JSON file if it exists; otherwise initializes to empty."""
        if not os.path.isfile(self.state_path):
            self.state = {}
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except Exception as e:
            self.error_logger.log(
                "WARNING", f"Could not load agent state from {self.state_path}", e
            )
            self.state = {}

# Simple test (place in test.py or run directly):
if __name__ == "__main__":
    from config import Config
    from error_logger import ErrorLogger

    cfg = Config()
    logger = ErrorLogger(cfg)
    as_state = AgentState(cfg, logger)

    print("Initial state:", as_state.state)
    as_state.update_state("key1", "value1")
    as_state.save_state()
    print("After update:", as_state.get_state("key1"))

    # Create a new instance to test loading
    as_state2 = AgentState(cfg, logger)
    print("Loaded state in new instance:", as_state2.get_state("key1"))
