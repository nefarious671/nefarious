# error_logger.py

import os
import sys
import traceback
from datetime import datetime
from typing import Optional

from config import Config


class ErrorLogger:
    """
    Centralized error-logging class that writes to a file and prints to stderr.
    Can also display expandable tracebacks in Streamlit (only when called).
    """

    def __init__(self, config: Config):
        self.config = config
        # Expand the user path for the log file and ensure the directory exists
        self.log_path = os.path.expanduser(config.error_log_file)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, level: str, message: str, exception: Optional[Exception] = None) -> None:
        """
        Writes a log entry to the error log file and prints to stderr.
        - level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        - message: short description
        - exception: optional Exception; includes stack trace if provided
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        entry_lines = [f"[{timestamp}] [{level}] {message}"]
        if exception:
            tb = traceback.format_exc()
            entry_lines.append(tb)
        entry = "\n".join(entry_lines) + "\n\n"

        # Attempt to write to the log file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            # If writing fails, ignore and continue to print to stderr
            pass

        # Print to stderr regardless
        print(entry, file=sys.stderr)

    def display_interactive(self, st_container, message: str, exception: Optional[Exception] = None) -> None:
        """
        In Streamlit, display an error message with an optional expandable traceback.
        - st_container: a Streamlit object (e.g., st or a specific placeholder)
        Note: We import Streamlit here so that CLI usage doesn't require it.
        """
        try:
            import importlib
            if importlib.util.find_spec("streamlit") is None: # type: ignore
                raise ImportError
        except ImportError:
            # If Streamlit is not installed, fall back to printing the message
            print(f"[Streamlit missing] {message}", file=sys.stderr)
            if exception:
                traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)
            return

        st_container.error(message)
        if exception:
            with st_container.expander("Show traceback"):
                tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
                st_container.text("".join(tb))
