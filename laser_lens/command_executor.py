# command_executor.py

import re
from typing import Any, Callable, Dict, List, Tuple

from error_logger import ErrorLogger


class CommandExecutor:
    """
    Parses and executes embedded [[COMMAND: ...]] tokens in text.
    """

    COMMAND_PATTERN = re.compile(r"\[\[COMMAND:\s*(?P<name>\w+)(?P<args>.*?)\]\]", re.DOTALL)

    def __init__(self, error_logger: ErrorLogger):
        self.error_logger = error_logger
        # Map command name to handler: handler(args_dict) -> Any
        self._registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_command(self, name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """
        Register a command handler by name (case-insensitive).
        """
        self._registry[name.upper()] = handler

    def parse_and_execute(self, text: str) -> List[Tuple[str, Any]]:
        """
        Scan 'text' for [[COMMAND: NAME key="val" ...]] patterns.
        For each, parse arguments, look up handler, execute, and collect (command_name, result).
        """
        results: List[Tuple[str, Any]] = []
        for match in self.COMMAND_PATTERN.finditer(text):
            name = match.group("name").strip().upper()
            raw_args = match.group("args").strip()
            try:
                args = self._parse_args(raw_args)
            except ValueError as e:
                self.error_logger.log(
                    "WARNING", f"Failed to parse args for command {name}: {e}"
                )
                results.append((name, f"ERROR: {e}"))
                continue

            if name not in self._registry:
                self.error_logger.log(
                    "WARNING", f"Ignoring unregistered command: {name}"
                )
                continue

            handler = self._registry[name]
            try:
                result = handler(args)
                results.append((name, result))
            except Exception as e:
                self.error_logger.log(
                    "ERROR", f"Error executing handler for command {name}", e
                )
                results.append((name, f"ERROR: {e}"))
        return results

    def _parse_args(self, raw: str) -> Dict[str, Any]:
        """
        Parse space-separated key="value" pairs from 'raw'.
        Returns dict of key->value.
        Raises ValueError if format is invalid.
        """
        args: Dict[str, Any] = {}
        pair_pattern = re.compile(r'(\w+)\s*=\s*"(.*?)"', re.DOTALL)
        for key, val in pair_pattern.findall(raw):
            args[key] = val
        # Validate that we consumed all text
        reconstructed = " ".join(f'{k}="{v}"' for k, v in args.items())
        cleaned_raw = raw.replace("\n", " ").strip()
        if args:
            if reconstructed not in cleaned_raw:
                raise ValueError(f"Invalid argument format: {raw}")
        elif cleaned_raw:
            raise ValueError(f"Invalid argument format: {raw}")
        return args
