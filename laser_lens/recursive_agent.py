# recursive_agent.py

import os
import time
import tempfile
from collections import deque
from typing import Any, Generator, Optional, Tuple

import google.generativeai as genai

from config import Config
from error_logger import ErrorLogger
from command_executor import CommandExecutor
from context_manager import ContextManager
from output_manager import OutputManager
from agent_state import AgentState


class CancelledException(Exception):
    """Raised when the user requests cancellation."""

    pass


class RecursiveAgent:
    """
    Production-ready RecursiveAgent that streams from a Gemini/GenAI client,
    handles retries, pauses, cancels, and persists state.

    Yields tuples of (event_type, loop_index, total_loops, payload):
      - "chunk": payload is a non-empty str (partial text).
      - "loop_end": payload is the full_response (str) for that loop.
      - "error": payload is (message: str, exception: Exception).

    Set *thinking_mode* to ``True`` to remove OS sandbox instructions from the
    system prompt, turning the agent into a chat-only assistant.
    """

    def __init__(
        self,
        config: Config,
        error_logger: ErrorLogger,
        command_executor: CommandExecutor,
        context_manager: ContextManager,
        output_manager: OutputManager,
        agent_state: AgentState,
        model_name: str,
        topic: str,
        loops: int,
        temperature: float,
        seed: Any,
        rpm: int,
        api_key: Optional[str] = None,
        thinking_mode: bool = False,
    ):
        self.config = config
        self.error_logger = error_logger
        self.command_executor = command_executor
        self.context_manager = context_manager
        self.output_manager = output_manager
        self.agent_state = agent_state

        # Core parameters
        self.model_name = model_name
        self.topic = topic
        self.loops = loops
        self.temperature = temperature
        self.seed = seed
        self.rpm = rpm
        self.thinking_mode = thinking_mode

        # Load persistent state (or default)
        self.current_loop = agent_state.get_state("current_loop") or 1
        hist = agent_state.get_state("history") or []
        try:
            self.history = deque(hist, maxlen=3)
        except Exception:
            self.history = deque(maxlen=3)
        self.last_thought = agent_state.get_state("last_thought") or ""
        self.cancelled = False
        self.paused = agent_state.get_state("paused") or False

        # Prepare or resume a NamedTemporaryFile for streaming (.md for easier viewing)
        tmp_path = agent_state.get_state("tmp_path")
        if tmp_path and os.path.isfile(tmp_path):
            try:
                self.tmp_file = open(tmp_path, "a+", encoding="utf-8")
            except Exception as e:
                self.error_logger.log(
                    "WARNING",
                    f"Failed to reopen existing tmp file ({tmp_path}); creating new one",
                    e,
                )
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, mode="w+", encoding="utf-8", suffix=".md"
                )
                self.tmp_file = tmp
                self.agent_state.update_state("tmp_path", tmp.name)
                self.agent_state.save_state()
        else:
            tmp = tempfile.NamedTemporaryFile(
                delete=False, mode="w+", encoding="utf-8", suffix=".md"
            )
            self.tmp_file = tmp
            self.agent_state.update_state("tmp_path", tmp.name)
            self.agent_state.save_state()

        # Rate limiting state
        self._last_request_ts = 0.0

        # Instantiate Gemini/GenAI client using the official SDK
        try:
            genai.api_key = api_key  # type: ignore[attr-defined]
            self.client = genai.GenerativeModel(self.model_name)  # type: ignore[attr-defined]
        except Exception as e:
            self.error_logger.log(
                "ERROR",
                "Failed to initialize Gemini/GenAI client",
                e,
            )
            raise

    def _build_prompt(self, context_str: str) -> str:
        """
        Assemble the prompt by concatenating:
          1. A brief “system” section describing available tools and file formats
          2. Any uploaded context
          3. Recursive instructions for this loop
          4. The last thought, if present
        """
        # 1) The “system” or “instruction” block:
        if self.thinking_mode:
            tool_instructions = (
                "You are 'Laser Lens', a recursive reasoning agent. "
                "Discuss the topic and iteratively refine your thoughts. "
                "All responses appear directly in chat."
            )
        else:
            tool_instructions = """\
You are a “Laser Lens” recursive agent operating inside a limited OS sandbox.
This directory is your sandboxed writable workspace.
You can inspect available functionality using [[COMMAND: HELP]].
Use `outputs/GEMINIOUTPUT.md` to leave notes for the developer and read their replies from `outputs/GEMINIINPUT.md`.
Capabilities:
  • When you embed text of the form [[COMMAND: <NAME> key="value" …]],
    the CLI/UI will invoke a Python function named <NAME>(…) with those arguments.
    Your handler functions can perform file I/O, run shell commands, or anything
    that our CommandExecutor supports, then return a result that will be visible 
    to you in a subsequent loop.

  • You can rely on “uploaded context” (Markdown or TXT files) or on a .tmp stream
    (partial outputs from prior loops). Any previous “.tmp” chunks have already been
    merged into the `context_str` below.

  • After you stream your response each loop, your full text is stored in “history”
    and available to you as your “last_thought” in the next loop.

  • If you wish to halt the recursion early, emit `[[COMMAND: CANCEL reason="your reason here"]]` or `[[COMMAND: PAUSE reason="your reason here"]]`.
    The surrounding code will interpret these commands, using your provided reason, and will either stop or pause execution accordingly.

  • At the end of all loops, the CLI/UI will assemble your prompts/responses into a 
    Markdown summary and save it to disk.
"""

        # 2) Any uploaded context
        if context_str:
            combined = tool_instructions + "\n---\n" + context_str + "\n\n"
        else:
            combined = tool_instructions + "\n"

        # 3) Recursive instructions for this loop
        header = f"You are a recursive agent analyzing: {self.topic}\n"
        header += f"Loop {self.current_loop} of {self.loops}. "
        header += "Decide whether to expand on your previous thought or to summarize.\n"

        # 4) Include last_thought if present
        if self.last_thought:
            header += f"Your last thought:\n{self.last_thought}\n\n"
        prompt_parts = [combined + header]

        # Include recent history
        if self.history:
            history_snippets = "\n".join(
                f"- {h['response'][:200]}" for h in list(self.history)
            )
            prompt_parts.append(f"\n\n## Recent History\n{history_snippets}")

        # Include tool outputs from previous loop
        results = self.agent_state.get_state("command_results") or []
        if results:
            tool_lines = []
            for idx, (name, result) in enumerate(results, start=1):
                snippet = str(result)[:500]
                tool_lines.append(f"\u2022 {idx}. {name}: {snippet}")
            prompt_parts.append("\n\n## Tool Outputs\n" + "\n".join(tool_lines))

        prompt = "".join(prompt_parts)
        if self.error_logger:
            self.error_logger.log("DEBUG", f"prompt length {len(prompt)} chars")
        return prompt

    def run(self) -> Generator[Tuple[str, int, int, Any], None, None]:
        """
        Execute recursive loops with retry handling. Yields:
          - ("chunk", loop_index, total_loops, text)
          - ("loop_end", loop_index, total_loops, full_response)
          - ("error", loop_index, total_loops, (message, exception))
        If an error message contains "503" and "overloaded", the retry wait is
        fixed at 10 seconds before trying again.
        """
        total_loops = self.loops

        while self.current_loop <= total_loops:
            if self.cancelled:
                break

            # Build prompt with any uploaded context
            context_str = self.context_manager.get_context()
            if self.error_logger:
                self.error_logger.log(
                    "DEBUG",
                    f"loop {self.current_loop}: context length {len(context_str)}",
                )
            prompt = self._build_prompt(context_str)

            # Enforce rate limiting
            self._enforce_rate_limit()

            full_response: Optional[str] = None
            retry_count = 0
            backoff = self.config.backoff_base_seconds

            # Retry loop: catch any Exception from the streaming call
            while retry_count <= self.config.max_retries:
                try:
                    # Stream-and-collect the full response
                    chunks = []
                    for text in self._stream_generation(prompt):
                        if text and text.strip():
                            yield ("chunk", self.current_loop, total_loops, text)
                            chunks.append(text)
                    full_response = "".join(chunks)
                    break
                except CancelledException:
                    # Graceful cancellation by user
                    self.agent_state.save_state()
                    return
                except Exception as e:
                    if self._is_quota_error(e):
                        msg = "API quota limit reached. Stopping agent."
                        self.error_logger.log("ERROR", msg, e)
                        err_payload = (msg, e)
                        yield ("error", self.current_loop, total_loops, err_payload)
                        return

                    retry_count += 1
                    msg = (
                        f"Error on loop {self.current_loop}, attempt {retry_count}: {e}"
                    )
                    self.error_logger.log("WARNING", msg, e)
                    if retry_count > self.config.max_retries:
                        err_payload = (
                            f"Exceeded retries on loop {self.current_loop}: {e}",
                            e,
                        )
                        yield ("error", self.current_loop, total_loops, err_payload)
                        return
                    # Special case: Gemini may return HTTP 503 when overloaded.
                    # Pause for 10 seconds before retrying in that case.
                    error_msg = str(e)
                    if "503" in error_msg and "overloaded" in error_msg.lower():
                        time.sleep(10)
                    else:
                        time.sleep(backoff)
                        backoff *= 2

            if full_response is None:
                full_response = ""

            # Save loop result to history and state
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.history.append({"prompt": prompt, "response": full_response, "timestamp": timestamp})
            self.agent_state.update_state("history", list(self.history))
            self.last_thought = full_response
            self.agent_state.update_state("last_thought", self.last_thought)

            # Parse and execute embedded commands
            try:
                results = self.command_executor.parse_and_execute(full_response)
                if results:
                    self.agent_state.update_state("command_results", results)
                    for name, res in results:
                        if name == "CANCEL" and not str(res).startswith("ERROR"):
                            self.request_cancel(str(res))
                        elif name == "PAUSE" and not str(res).startswith("ERROR"):
                            self.request_pause(str(res))
            except Exception as e:
                self.error_logger.log(
                    "ERROR",
                    f"Error parsing/executing commands on loop {self.current_loop}",
                    e,
                )

            # Signal end of loop
            yield ("loop_end", self.current_loop, total_loops, full_response)

            # Advance loop counter and persist state
            self.current_loop += 1
            self.agent_state.update_state("current_loop", self.current_loop)
            self.agent_state.save_state()

            if self.paused:
                break

        # If recursion completed normally, cap current_loop at total_loops so
        # the UI does not show an impossible "loop N+1 of N" status.
        if not self.paused and not self.cancelled and self.current_loop > total_loops:
            self.current_loop = total_loops
            self.agent_state.update_state("current_loop", self.current_loop)

        self.agent_state.save_state()

    def _enforce_rate_limit(self) -> None:
        """
        Ensure at least (60 / rpm) seconds pass between requests.
        """
        interval = 60.0 / self.rpm
        elapsed = time.time() - self._last_request_ts
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_request_ts = time.time()

    def _is_quota_error(self, exc: Exception) -> bool:
        """Return True if *exc* indicates the API quota was exceeded."""
        try:
            from google.api_core.exceptions import ResourceExhausted

            if isinstance(exc, ResourceExhausted):
                return True
        except Exception:
            # google.api_core may not be installed during tests
            pass

        text = str(exc).lower()
        return "quota" in text and "exceeded" in text

    def _stream_generation(self, prompt: str) -> Generator[str, None, None]:
        """
        Call Gemini's streaming endpoint. If the first call fails, attempt to
        reinitialize the client once. For each chunk:
          - If chunk.text is empty or whitespace, skip.
          - Otherwise write to the temp file and yield the text.
        """
        try:
            stream = self.client.generate_content(prompt, stream=True)
        except Exception as e:
            self.error_logger.log("WARNING", "Initial stream call failed", e)
            try:
                self.client = genai.GenerativeModel(self.model_name) # type: ignore[attr-defined]
                stream = self.client.generate_content(prompt, stream=True)
            except Exception:
                raise

        for chunk in stream:
            if hasattr(chunk, "text"):
                text = chunk.text
            elif (
                hasattr(chunk, "choices")
                and isinstance(chunk.choices, list)  # type: ignore[attr-defined]
                and len(chunk.choices) > 0  # type: ignore[attr-defined]
                and hasattr(chunk.choices[0], "text")  # type: ignore[attr-defined]
            ):
                text = chunk.choices[0].text  # type: ignore[attr-defined]
            else:
                continue

            if not text or not text.strip():
                continue

            try:
                self.tmp_file.write(text)
                self.tmp_file.flush()
            except Exception as e:
                self.error_logger.log(
                    "WARNING", "Failed to write chunk to tmp file; continuing", e
                )

            yield text

            if self.cancelled:
                raise CancelledException()
            if self.paused:
                return

    def request_cancel(self, reason: str) -> None:
        """
        Request cancellation: this flag causes _stream_generation to abort
        and run() to exit after yielding the current error or chunk.
        """
        self.cancelled = True
        self.agent_state.update_state("cancelled", reason)
        self.agent_state.save_state()

    def request_pause(self, reason: str) -> None:
        """
        Request pause: run() will complete the current loop and then stop.
        """
        self.paused = True
        self.agent_state.update_state("paused", reason)
        self.agent_state.save_state()

    def resume(self) -> None:
        """
        Resume from pause: clears the paused flag so run() can continue.
        """
        self.paused = False
        self.agent_state.update_state("paused", False)
        self.agent_state.save_state()
