from command_executor import CommandExecutor
from handlers import (
    WRITE_FILE,
    APPEND_FILE,
    READ_FILE,
    READ_LINES,
    LIST_OUTPUTS,
    DELETE_FILE,
    EXEC,
    RUN_PYTHON,
    WORD_COUNT,
    HELP,
    CANCEL,
    PAUSE,
)

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore


def register_core_commands(ce: CommandExecutor) -> None:
    """Register built-in handlers and their aliases."""
    ce.register_command("WRITE_FILE", WRITE_FILE)
    ce.register_command("APPEND_FILE", APPEND_FILE)
    ce.register_command("READ_FILE", READ_FILE)
    ce.register_command("READ_LINES", READ_LINES)
    ce.register_command("LIST_OUTPUTS", LIST_OUTPUTS)
    ce.register_command("DELETE_FILE", DELETE_FILE)
    ce.register_command("EXEC", EXEC)
    ce.register_command("RUN_PYTHON", RUN_PYTHON)
    ce.register_command("WORD_COUNT", WORD_COUNT)
    ce.register_command("HELP", HELP)
    ce.register_command("CANCEL", CANCEL)
    ce.register_command("PAUSE", PAUSE)

    for alias, target in {
        "LS": "LIST_OUTPUTS",
        "CAT": "READ_FILE",
        "RM": "DELETE_FILE",
        "WC": "WORD_COUNT",
        "RL": "READ_LINES",
    }.items():
        ce.register_command(alias, ce._registry[target])


def register_plugin_commands(ce: CommandExecutor) -> None:
    """Load commands from entry points under 'laser_lens.commands'."""
    for ep in importlib_metadata.entry_points().get("laser_lens.commands", []):
        try:
            handler = ep.load()
            ce.register_command(ep.name, handler)
        except Exception as e:  # pragma: no cover - best effort
            print(f"Failed to load plugin command {ep.name}: {e}")

