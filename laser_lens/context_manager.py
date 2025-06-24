# context_manager.py

from typing import List, Tuple, Optional

from config import Config
from utils import count_tokens, parse_tmp
from error_logger import ErrorLogger


class ContextManager:
    """
    Aggregates uploaded context files (.md, .txt) and/or a .tmp stream into a single prompt context.
    """

    def __init__(self, config: Config, error_logger: Optional[ErrorLogger] = None):
        self.config = config
        self.error_logger = error_logger
        # Internal list of (filename, content) tuples, ordered by upload time
        self._buffers: List[Tuple[str, str]] = []

    def upload_context(self, file_name: str, content: bytes) -> None:
        """
        Accept an uploaded file (bytes) named file_name.
        - If .tmp: parse using parse_tmp, join completed chunks, store as one buffer entry.
        - If .md or .txt: decode as UTF-8 and store directly.
        Otherwise, ignore.
        """
        lower = file_name.lower()
        if self.error_logger:
            self.error_logger.log(
                "DEBUG",
                f"upload_context called for {file_name} ({len(content)} bytes)"
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")

        if lower.endswith(".tmp"):
            # parse_tmp returns (chunks, last_partial)
            chunks, _ = parse_tmp(text, self.config.default_prompt_delim)
            merged = "\n".join(chunks)
            if self.error_logger:
                self.error_logger.log(
                    "DEBUG",
                    f"parsed .tmp file {file_name}; {len(chunks)} chunks"
                )
            self._buffers.append((file_name, merged))
        elif lower.endswith(".md") or lower.endswith(".txt"):
            if self.error_logger:
                self.error_logger.log(
                    "DEBUG",
                    f"stored text file {file_name}; {len(text)} chars"
                )
            self._buffers.append((file_name, text))
        else:
            # Unsupported extension; ignore
            if self.error_logger:
                self.error_logger.log("DEBUG", f"ignored unsupported file {file_name}")
            return

        # Enforce max context size after adding
        self._truncate_if_needed()
        if self.error_logger:
            total_chars = len(self.get_context())
            self.error_logger.log(
                "DEBUG", f"context now has {len(self._buffers)} file(s), {total_chars} chars"
            )

    def get_context(self) -> str:
        """
        Return concatenated context buffers in upload order, each preceded by a delimiter header.
        """
        parts: List[str] = []
        delim = self.config.default_prompt_delim
        for fname, text in self._buffers:
            parts.append(f"{delim} Context from: {fname} {delim}")
            parts.append(text)
        combined = "\n\n".join(parts).strip()
        if self.error_logger:
            self.error_logger.log(
                "DEBUG",
                f"get_context assembled {len(self._buffers)} files -> {len(combined)} chars"
            )
        return combined

    def clear_context(self) -> None:
        """Remove all stored buffers."""
        self._buffers = []
        if self.error_logger:
            self.error_logger.log("DEBUG", "Context cleared")

    def _truncate_if_needed(self) -> None:
        """
        If combined context exceeds max_context_tokens, drop oldest buffers until under limit.
        """
        while True:
            combined = self.get_context()
            if count_tokens(combined) <= self.config.max_context_tokens:
                break
            if self._buffers:
                removed = self._buffers.pop(0)
                if self.error_logger:
                    self.error_logger.log(
                        "DEBUG",
                        f"Dropped {removed[0]} to enforce context size"
                    )
            else:
                break
