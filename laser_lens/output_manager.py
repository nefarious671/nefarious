# output_manager.py

import os
import re
from typing import List

from config import Config
from error_logger import ErrorLogger


class OutputManager:
    """
    Manages safe file output: sanitizes filenames, writes content to a controlled directory,
    and can list saved files.
    """

    def __init__(self, config: Config, error_logger: ErrorLogger):
        self.config = config
        self.error_logger = error_logger
        # Expand and create the safe directory
        self.safe_dir = os.path.expanduser(config.safe_output_dir)
        os.makedirs(self.safe_dir, exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """
        - Replace spaces with underscores.
        - Remove any characters except alphanumeric, dash, underscore, and dot.
        - Ensure extension is one of allowed_extensions; if not, append '.txt'.
        """
        # Remove directory components
        base_name = os.path.basename(name.strip().replace(" ", "_"))
        # Remove disallowed chars
        base_name = re.sub(r"[^A-Za-z0-9_.\-]", "", base_name)
        root, ext = os.path.splitext(base_name)
        if ext.lower() not in self.config.allowed_extensions:
            ext = ".txt"
        safe = root + ext
        return safe

    def save_output(self, filename: str, content: str) -> str:
        """
        Write 'content' to 'filename' under safe_dir. Returns the full path or raises on error.
        """
        safe_name = self.sanitize_filename(filename)
        full_path = os.path.join(self.safe_dir, safe_name)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return full_path
        except Exception as e:
            self.error_logger.log("ERROR", f"Failed to save output to {full_path}", e)
            raise

    def list_outputs(self) -> List[str]:
        """Return a sorted list of filenames in safe_dir."""
        try:
            return sorted(os.listdir(self.safe_dir))
        except Exception as e:
            self.error_logger.log("WARNING", f"Could not list outputs in {self.safe_dir}", e)
            return []
