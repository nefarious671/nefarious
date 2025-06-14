# handlers.py

import os
from typing import Dict, Any

from output_manager import OutputManager
from error_logger import ErrorLogger
from config import Config

# We’ll assume you have a global OutputManager and ErrorLogger instantiated elsewhere.
# For simplicity in these examples, we’ll create new ones locally.

_cfg = Config()
_logger = ErrorLogger(_cfg)
_output_mgr = OutputManager(_cfg, _logger)


def WRITE_FILE(args: Dict[str, Any]) -> str:
    """
    Usage in LLM output:
        [[COMMAND: WRITE_FILE filename="notes.md" content="Hello world!"]]
    Writes the given content to ./outputs/filename, returns a confirmation message.
    """
    fname = args.get("filename")
    content = args.get("content", "")
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    try:
        saved_path = _output_mgr.save_output(fname, content)
        return f"Wrote {len(content)} chars to {saved_path}"
    except Exception as e:
        _logger.log("ERROR", f"Failed to WRITE_FILE {fname}", e)
        return f"ERROR: Could not write file {fname}: {e}"


def READ_FILE(args: Dict[str, Any]) -> str:
    """
    Usage:
        [[COMMAND: READ_FILE filename="notes.md"]]
    Reads from ./outputs/filename and returns its first few lines.
    """
    fname = args.get("filename")
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    safe_name = _output_mgr.sanitize_filename(fname)
    path = os.path.join(os.path.expanduser(_cfg.safe_output_dir), safe_name)
    if not os.path.isfile(path):
        return f"ERROR: File {safe_name} does not exist."

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Return up to first 10 lines (or entire file if shorter)
        snippet = "".join(lines[:10])
        return f"CONTENT_START\n{snippet}\nCONTENT_END"
    except Exception as e:
        _logger.log("ERROR", f"Failed to READ_FILE {safe_name}", e)
        return f"ERROR: Could not read file {safe_name}: {e}"


def LIST_OUTPUTS(args: Dict[str, Any]) -> str:
    """
    Usage:
        [[COMMAND: LIST_OUTPUTS]]
    Returns a newline-separated list of filenames under ./outputs/.
    """
    try:
        files = _output_mgr.list_outputs()
        if not files:
            return "(no files found in outputs/)"
        return "\n".join(files)
    except Exception as e:
        _logger.log("ERROR", "Failed to LIST_OUTPUTS", e)
        return f"ERROR: Could not list outputs: {e}"


def DELETE_FILE(args: Dict[str, Any]) -> str:
    """
    Usage:
        [[COMMAND: DELETE_FILE filename="notes.md"]]
    Deletes ./outputs/filename if it exists.
    """
    fname = args.get("filename")
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    safe_name = _output_mgr.sanitize_filename(fname)
    path = os.path.join(os.path.expanduser(_cfg.safe_output_dir), safe_name)
    if not os.path.isfile(path):
        return f"ERROR: File {safe_name} does not exist."

    try:
        os.remove(path)
        return f"Deleted {safe_name}"
    except Exception as e:
        _logger.log("ERROR", f"Failed to DELETE_FILE {safe_name}", e)
        return f"ERROR: Could not delete file {safe_name}: {e}"
