from command_executor import CommandExecutor
from handlers import (
    WRITE_FILE,
    READ_FILE,
    LIST_OUTPUTS,
    DELETE_FILE,
    EXEC,
)


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

