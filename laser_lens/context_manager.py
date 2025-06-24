# context_manager.py

from typing import List, Tuple, Optional
import time

from output_manager import OutputManager

from config import Config
from utils import count_tokens, parse_tmp
from error_logger import ErrorLogger


class ContextManager:
    """
    Aggregates uploaded context files (.md, .txt) and/or a .tmp stream into a single prompt context.
    """

    def __init__(
        self,
        config: Config,
        error_logger: Optional[ErrorLogger] = None,
        output_manager: Optional[OutputManager] = None,
    ):
        self.config = config
        self.error_logger = error_logger
        self.output_manager = output_manager
        # Internal list of (filename, content) tuples, ordered by upload time
        self._buffers: List[Tuple[str, str]] = []

    def _truncate_large_file(self, text: str, file_name: str, *, limit: Optional[int] = None) -> str:
        """Trim text if it exceeds the given token limit."""
        if limit is None:
            limit = self.config.max_context_tokens
        if count_tokens(text) <= limit:
            return text

        marker = "\n...[truncated]...\n"
        keep = max(0, (limit - len(marker)) // 2)
        truncated = text[:keep] + marker + text[-keep:]
        if self.output_manager:
            safe_name = self.output_manager.sanitize_filename(f"full_{file_name}")
            self.output_manager.save_output(safe_name, text)
            truncated += f"\n\n[Full file saved as {safe_name}]"
        if self.error_logger:
            self.error_logger.log(
                "INFO", f"Truncated {file_name} to fit context window"
            )
        return truncated

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
            merged = self._truncate_large_file(merged, file_name)
            if self.error_logger:
                self.error_logger.log(
                    "DEBUG",
                    f"parsed .tmp file {file_name}; {len(chunks)} chunks"
                )
            self._buffers.append((file_name, merged))
        elif lower.endswith(".md") or lower.endswith(".txt"):
            text = self._truncate_large_file(text, file_name)
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

    def add_inline_context(self, text: str) -> None:
        """Add a short note directly into the context buffers."""
        name = f"user_note_{int(time.time())}.txt"
        self._buffers.append((name, text))
        self._truncate_if_needed()

    def _truncate_if_needed(self) -> None:
        """
        If combined context exceeds max_context_tokens, drop oldest buffers until under limit.
        """
        while True:
            combined = self.get_context()
            if count_tokens(combined) <= self.config.max_context_tokens:
                break
            if len(self._buffers) == 1:
                name, text = self._buffers[0]
                header_overhead = len(self.config.default_prompt_delim) * 2 + len(f" Context from: {name} ")
                limit = max(0, self.config.max_context_tokens - header_overhead)
                self._buffers[0] = (name, self._truncate_large_file(text, name, limit=limit))
                break
            elif self._buffers:
                removed = self._buffers.pop(0)
                if self.error_logger:
                    self.error_logger.log(
                        "DEBUG",
                        f"Dropped {removed[0]} to enforce context size"
                    )
            else:
                break
