from command_executor import CommandExecutor
from handlers import (
    WRITE_FILE,
    READ_FILE,
    LIST_OUTPUTS,
    DELETE_FILE,
    EXEC,
)

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore


def register_core_commands(ce: CommandExecutor) -> None:
    """Register built-in handlers and their aliases."""
    ce.register_command("WRITE_FILE", WRITE_FILE)
    ce.register_command("READ_FILE", READ_FILE)
    ce.register_command("LIST_OUTPUTS", LIST_OUTPUTS)
    ce.register_command("DELETE_FILE", DELETE_FILE)
    ce.register_command("EXEC", EXEC)

    for alias, target in {
        "LS": "LIST_OUTPUTS",
        "CAT": "READ_FILE",
        "RM": "DELETE_FILE",
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

