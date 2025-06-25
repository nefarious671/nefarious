# handlers.py

import os
import subprocess
from typing import Dict, Any

from output_manager import OutputManager
from error_logger import ErrorLogger
from config import Config

# We’ll assume you have a global OutputManager and ErrorLogger instantiated elsewhere.
# For simplicity in these examples, we’ll create new ones locally.

_cfg = Config()
_logger = ErrorLogger(_cfg)
_output_mgr = OutputManager(_cfg, _logger)

COMMAND_HELP: Dict[str, tuple[str, str]] = {
    "WRITE_FILE": ("filename, content[, dry_run]", "Save text to outputs directory."),
    "APPEND_FILE": ("filename, content", "Append text to an existing file."),
    "READ_FILE": ("filename", "Read a file from outputs."),
    "READ_LINES": ("filename, start, end", "Read a specific line range."),
    "LIST_OUTPUTS": ("", "List files under outputs/"),
    "DELETE_FILE": ("filename", "Delete a file from outputs."),
    "EXEC": ("cmd[, dry_run]", "Run a shell command inside outputs/"),
    "RUN_PYTHON": ("code", "Execute Python code inside outputs/"),
    "WORD_COUNT": ("filename", "Count lines and words in a file."),
    "LS": ("", "Alias for LIST_OUTPUTS"),
    "CAT": ("filename", "Alias for READ_FILE"),
    "RM": ("filename", "Alias for DELETE_FILE"),
    "WC": ("filename", "Alias for WORD_COUNT"),
    "RL": ("filename, start, end", "Alias for READ_LINES"),
    "HELP": ("", "Show this message"),
    "CANCEL": ("reason", "Stop recursion"),
    "PAUSE": ("reason", "Pause recursion"),
}


def WRITE_FILE(args: Dict[str, Any]) -> str:
    """
    Usage in LLM output:
        [[COMMAND: WRITE_FILE filename="notes.md" content="Hello world!"]]
    Writes the given content to ./outputs/filename, returns a confirmation message.
    """
    fname = args.get("filename")
    content = args.get("content", "")
    dry = str(args.get("dry_run", "false")).lower() == "true"
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    if dry:
        safe = _output_mgr.sanitize_filename(fname)
        return f"DRY RUN: would write {len(content)} chars to {safe}"

    try:
        saved_path = _output_mgr.save_output(fname, content)
        return f"Wrote {len(content)} chars to {saved_path}"
    except Exception as e:
        _logger.log("ERROR", f"Failed to WRITE_FILE {fname}", e)
        return f"ERROR: Could not write file {fname}: {e}"


def APPEND_FILE(args: Dict[str, Any]) -> str:
    """Append content to an existing file in the outputs directory."""
    fname = args.get("filename")
    content = args.get("content", "")
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    safe_name = _output_mgr.sanitize_filename(fname)
    path = os.path.join(os.path.expanduser(_cfg.safe_output_dir), safe_name)
    if not os.path.isfile(path):
        return f"ERROR: File {safe_name} does not exist."

    try:
        with open(path, "a", encoding="utf-8", newline="") as f:
            f.write(content)
        return f"Appended {len(content)} chars to {safe_name}"
    except Exception as e:
        _logger.log("ERROR", f"Failed to APPEND_FILE {safe_name}", e)
        return f"ERROR: Could not append to file {safe_name}: {e}"


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
        orig_len = len(lines)
        snippet_lines = lines[:10]
        snippet = "".join(snippet_lines)
        if orig_len > len(snippet_lines):
            warning = f"WARNING: truncated from {orig_len} lines to {len(snippet_lines)} lines\n"
        else:
            warning = ""
        return f"{warning}CONTENT_START\n{snippet}\nCONTENT_END"
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


def EXEC(args: Dict[str, Any]) -> str:
    """Execute a shell command within the outputs sandbox."""
    cmd = args.get("cmd")
    dry = str(args.get("dry_run", "false")).lower() == "true"
    if not cmd:
        return "ERROR: Missing required argument 'cmd'."

    banned = ["sudo", "rm -rf", "curl", "wget", "ssh"]
    if any(b in cmd for b in banned):
        return "ERROR: Command contains prohibited patterns."

    if dry:
        return f"DRY RUN: would execute '{cmd}'"

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=os.path.expanduser(_cfg.safe_output_dir),
            timeout=10,
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out."
    except Exception as e:
        _logger.log("ERROR", f"Failed to EXEC '{cmd}'", e)
        return f"ERROR: Could not execute command: {e}"


def RUN_PYTHON(args: Dict[str, Any]) -> str:
    """Execute Python code inside the outputs sandbox."""
    code = args.get("code")
    if not code:
        return "ERROR: Missing required argument 'code'."
    try:
        proc = subprocess.run(
            ["python", "-c", code],
            cwd=os.path.expanduser(_cfg.safe_output_dir),
            timeout=10,
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Python execution timed out."
    except Exception as e:
        _logger.log("ERROR", "Failed to RUN_PYTHON", e)
        return f"ERROR: Could not execute python: {e}"


def WORD_COUNT(args: Dict[str, Any]) -> str:
    """Return the line and word count of a file in the outputs directory."""
    fname = args.get("filename")
    if not fname:
        return "ERROR: Missing required argument 'filename'."

    safe_name = _output_mgr.sanitize_filename(fname)
    path = os.path.join(os.path.expanduser(_cfg.safe_output_dir), safe_name)
    if not os.path.isfile(path):
        return f"ERROR: File {safe_name} does not exist."

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        lines = len(text.splitlines())
        words = len(text.split())
        return f"{lines} lines, {words} words"
    except Exception as e:  # pragma: no cover - unexpected
        _logger.log("ERROR", f"Failed to WORD_COUNT {safe_name}", e)
        return f"ERROR: Could not read file {safe_name}: {e}"


def READ_LINES(args: Dict[str, Any]) -> str:
    """Read a specific line range from a file in outputs."""
    fname = args.get("filename")
    try:
        start = int(args.get("start", 1))
        end = int(args.get("end", start + 9))
    except (TypeError, ValueError):
        return "ERROR: start and end must be integers."
    if not fname:
        return "ERROR: Missing required argument 'filename'."
    if start <= 0 or end < start:
        return "ERROR: Invalid line range."

    safe_name = _output_mgr.sanitize_filename(fname)
    path = os.path.join(os.path.expanduser(_cfg.safe_output_dir), safe_name)
    if not os.path.isfile(path):
        return f"ERROR: File {safe_name} does not exist."

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[start - 1 : end]
        return "".join(lines)
    except Exception as e:
        _logger.log("ERROR", f"Failed to READ_LINES {safe_name}", e)
        return f"ERROR: Could not read file {safe_name}: {e}"


def HELP(args: Dict[str, Any]) -> str:
    """Return OS info and detailed command usage."""
    import platform

    lines = ["Available commands:"]
    for name, (params, desc) in COMMAND_HELP.items():
        if name in {"LS", "CAT", "RM", "WC", "RL"}:
            prefix = "- "
        else:
            prefix = "* "
        lines.append(f"{prefix}{name}({params}) - {desc}")

    lines.append(f"OS: {platform.platform()}")
    return "\n".join(lines)


def CANCEL(args: Dict[str, Any]) -> str:
    """Return the reason for cancelling recursion."""
    reason = args.get("reason", "").strip()
    if not reason:
        return "ERROR: Missing required argument 'reason'."
    return reason


def PAUSE(args: Dict[str, Any]) -> str:
    """Return the reason for pausing recursion."""
    reason = args.get("reason", "").strip()
    if not reason:
        return "ERROR: Missing required argument 'reason'."
    return reason

