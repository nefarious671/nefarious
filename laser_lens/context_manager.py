# context_manager.py

import os
from typing import List, Tuple

from config import Config
from utils import count_tokens, parse_tmp


class ContextManager:
    """
    Aggregates uploaded context files (.md, .txt) and/or a .tmp stream into a single prompt context.
    """

    def __init__(self, config: Config):
        self.config = config
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
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")

        if lower.endswith(".tmp"):
            # parse_tmp returns (chunks, last_partial)
            chunks, _ = parse_tmp(text, self.config.default_prompt_delim)
            merged = "\n".join(chunks)
            self._buffers.append((file_name, merged))
        elif lower.endswith(".md") or lower.endswith(".txt"):
            self._buffers.append((file_name, text))
        else:
            # Unsupported extension; ignore
            return

        # Enforce max context size after adding
        self._truncate_if_needed()

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
        return combined

    def clear_context(self) -> None:
        """Remove all stored buffers."""
        self._buffers = []

    def _truncate_if_needed(self) -> None:
        """
        If combined context exceeds max_context_tokens, drop oldest buffers until under limit.
        """
        while True:
            combined = self.get_context()
            if count_tokens(combined) <= self.config.max_context_tokens:
                break
            if self._buffers:
                self._buffers.pop(0)
            else:
                break
