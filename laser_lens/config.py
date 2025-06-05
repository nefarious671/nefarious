# config.py

from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class Config:
    # Model parameters
    default_model_name: str = "Gemini1Pro"
    default_temperature: float = 0.7
    default_seed: Optional[int] = None
    default_rpm: int = 20  # requests per minute for rate limiting

    # Recursive parameters
    default_loops: int = 3
    default_prompt_delim: str = "###"  # delimiter for parsing .tmp streams

    # Context parameters
    max_context_tokens: int = 8000  # maximum tokens/characters allowed in combined context

    # Output directories
    safe_output_dir: str = "./outputs/"
    ui_autosave_dir: str = "~/.laser_lens_logs/"

    # Agent state
    agent_state_dir: str = "./agent_state/"

    # Retry/Circuit-Breaker
    max_retries: int = 3
    backoff_base_seconds: float = 2.0  # for exponential backoff

    # Logging
    error_log_file: str = "~/.laser_lens_logs/errors.log"
    log_level: str = "INFO"  # default logging level

    # File extensions
    allowed_extensions: Tuple[str, ...] = (".md", ".txt", ".log", ".tmp")
