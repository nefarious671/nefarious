# ui_main.py

import os
import streamlit as st

from config import Config
from error_logger import ErrorLogger
from command_executor import CommandExecutor
from context_manager import ContextManager
from output_manager import OutputManager
from agent_state import AgentState
from recursive_agent import RecursiveAgent

from utils import (
    suggest_filename,
    load_pref_model,
    save_pref_model,
    build_markdown,
)
from handlers import WRITE_FILE, READ_FILE, LIST_OUTPUTS, DELETE_FILE

# Approximate number of characters per page displayed
PAGE_SIZE = 30000


def get_available_models() -> list[str]:
    """
    Attempt to list all Gemini models that support generateContent.
    On failure, return a single default placeholder.
    """
    try:
        import google.generativeai as genai_list
        from dotenv import load_dotenv

        load_dotenv()
        genai_list.configure(api_key=os.getenv("GOOGLE_API_KEY"))  # type: ignore[attr-defined]

        models_available = [
            m.name
            for m in genai_list.list_models()  # type: ignore[attr-defined]
            if "generateContent" in (m.supported_generation_methods or [])
        ]
        models_available = sorted(
            [m for m in models_available if "gemini" in m.lower()],
            reverse=True
        )
        if not models_available:
            models_available = ["models/gemini-2.0-pro"]
    except Exception:
        models_available = ["models/gemini-2.0-pro"]

    return models_available


# Initialize singletons
config = Config()
logger = ErrorLogger(config)
context_manager = ContextManager(config)
output_manager = OutputManager(config, logger)
agent_state = AgentState(config, logger)

# Register command handlers
ce = CommandExecutor(logger)
ce.register_command("WRITE_FILE", WRITE_FILE)
ce.register_command("READ_FILE", READ_FILE)
ce.register_command("LIST_OUTPUTS", LIST_OUTPUTS)
ce.register_command("DELETE_FILE", DELETE_FILE)

st.set_page_config(page_title="Laser Lens UI", layout="wide")

# Load dynamic model list once per session
if "models_available" not in st.session_state:
    st.session_state.models_available = get_available_models()
models_available = st.session_state.models_available

if "model_name" not in st.session_state:
    saved_model = load_pref_model(models_available)
    st.session_state.model_name = (
        saved_model if saved_model in models_available else models_available[0]
    )
if "model_idx" not in st.session_state:
    st.session_state.model_idx = models_available.index(st.session_state.model_name)

# SESSION STATE KEYS
if "agent" not in st.session_state:
    st.session_state.agent = None
if "stream_placeholder" not in st.session_state:
    st.session_state.stream_placeholder = None
if "progress_bar" not in st.session_state:
    st.session_state.progress_bar = None
if "error_container" not in st.session_state:
    st.session_state.error_container = None
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "loops" not in st.session_state:
    st.session_state.loops = config.default_loops
if "pages" not in st.session_state:
    st.session_state.pages = [""]
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "temperature" not in st.session_state:
    st.session_state.temperature = config.default_temperature
if "seed" not in st.session_state:
    st.session_state.seed = config.default_seed or 0
if "rpm" not in st.session_state:
    st.session_state.rpm = config.default_rpm

# We'll keep track of uploaded files in session_state so start_agent() can process them:
if "uploaded_files_list" not in st.session_state:
    st.session_state.uploaded_files_list = []


# Sidebar: File uploader for context or resume (.md, .txt, .tmp)
st.sidebar.header("Upload Context / Resume")
# Each time the user selects files, we append them to session_state.uploaded_files_list
uploaded_files = st.sidebar.file_uploader(
    "Upload .md, .txt or .tmp",
    type=["md", "txt", "tmp"],
    accept_multiple_files=True,
    key="file_uploader"
)
if uploaded_files:
    for uf in uploaded_files:
        # Only add if we haven't seen this file name + size combo already
        marker = (uf.name, len(uf.getvalue()))
        if marker not in st.session_state.uploaded_files_list:
            st.session_state.uploaded_files_list.append(marker)

# Sidebar: Parameters in a form to avoid auto-refresh
st.sidebar.markdown("---")
with st.sidebar.form("agent_settings"):
    st.header("Agent Settings")
    topic_in = st.text_input("Topic", value=st.session_state.topic)
    loops_in = st.slider(
        "Recursion Loops", min_value=1, max_value=500, value=st.session_state.loops
    )
    st.selectbox(
        "Model",
        models_available,
        index=models_available.index(st.session_state.model_name),
        key="model_name",
    )
    temp_in = st.slider(
        "Temperature", 0.0, 1.0, value=st.session_state.temperature
    )
    seed_in = st.number_input(
        "Seed (optional)",
        min_value=0,
        max_value=2**32 - 1,
        value=st.session_state.seed,
    )
    rpm_in = st.number_input(
        "Requests/minute", min_value=1, max_value=100, value=st.session_state.rpm
    )
    apply_btn = st.form_submit_button("Apply")

if apply_btn:
    st.session_state.topic = topic_in
    st.session_state.loops = loops_in
    st.session_state.temperature = temp_in
    st.session_state.seed = seed_in
    st.session_state.rpm = rpm_in
    st.session_state.model_idx = models_available.index(st.session_state.model_name)

# Keep model_idx consistent with model_name on every run
if st.session_state.model_name in models_available:
    st.session_state.model_idx = models_available.index(st.session_state.model_name)
else:
    st.session_state.model_name = models_available[0]
    st.session_state.model_idx = 0

# Sidebar: Control Buttons
st.sidebar.markdown("---")
start_btn = st.sidebar.button("▶️ Start")
pause_btn = st.sidebar.button("⏸️ Pause")
resume_btn = st.sidebar.button("▶️ Resume")
stop_btn = st.sidebar.button("⏹️ Stop")

# Pagination buttons
prev_page_btn = st.sidebar.button("⬅️ Prev Page")
next_page_btn = st.sidebar.button("Next Page ➡️")
st.sidebar.markdown(
    f"Page {st.session_state.current_page + 1} / {len(st.session_state.pages)}"
)

# Main area placeholders
if st.session_state.stream_placeholder is None:
    st.session_state.stream_placeholder = st.empty()
if st.session_state.progress_bar is None:
    st.session_state.progress_bar = st.sidebar.progress(0.0)
if st.session_state.error_container is None:
    st.session_state.error_container = st.empty()


def start_agent() -> bool:
    """
    Initialize a fresh agent, upload any files the user has selected,
    and clear previous displays and state.
    """
    # First, upload all files that were chosen in the sidebar
    for (name, size) in st.session_state.uploaded_files_list:
        try:
            # Find the corresponding UploadedFile object in st.session_state["file_uploader"]
            if uploaded_files:
                for uf in uploaded_files:
                    if uf.name == name and len(uf.getvalue()) == size:
                        content = uf.getvalue()
                        context_manager.upload_context(uf.name, content)
                        break
        except Exception as e:
            logger.log("WARNING", f"Failed to upload {name}", e)

    # Save the chosen model so next time it’s the default
    chosen_model = models_available[st.session_state.model_idx]
    save_pref_model(chosen_model)

    # Clear previous run state if any
    agent_state.delete_state("history")
    agent_state.delete_state("last_thought")
    agent_state.delete_state("current_loop")
    agent_state.delete_state("paused")
    agent_state.delete_state("cancelled")
    agent_state.save_state()

    # Clear UI placeholders and pagination
    st.session_state.stream_placeholder.empty()
    st.session_state.progress_bar.progress(0.0)
    st.session_state.error_container.empty()
    st.session_state.pages = [""]
    st.session_state.current_page = 0

    # Instantiate agent with the real Gemini client
    try:
        st.session_state.agent = RecursiveAgent(
            config=config,
            error_logger=logger,
            command_executor=ce,
            context_manager=context_manager,
            output_manager=output_manager,
            agent_state=agent_state,
            model_name=models_available[st.session_state.model_idx],
            topic=st.session_state.topic,
            loops=st.session_state.loops,
            temperature=st.session_state.temperature,
            seed=st.session_state.seed or None,
            rpm=st.session_state.rpm,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
        return True
    except Exception as e:
        st.session_state.agent = None
        st.session_state.error_container.error(
            f"Failed to initialize agent: {e}"
        )
        return False


def show_current_page() -> None:
    """Render the currently selected page in the main placeholder."""
    if st.session_state.pages:
        idx = st.session_state.current_page
        content = st.session_state.pages[idx]
        st.session_state.stream_placeholder.markdown(content)


def run_stream():
    """Run agent.run() and render streaming output, progress, and errors."""
    agent = st.session_state.agent
    if agent is None:
        st.session_state.error_container.error("Agent is not initialized")
        return
    total_loops = agent.loops

    buffer = ""
    sentence_enders = {".", "?", "!"}

    def flush_buffer_ui(final: bool = False) -> None:
        """Append buffered text to pages and update display."""
        nonlocal buffer
        if not buffer.strip():
            return
        while buffer:
            remaining = PAGE_SIZE - len(st.session_state.pages[-1])
            if remaining <= 0:
                st.session_state.pages.append("")
                st.session_state.current_page = len(st.session_state.pages) - 1
                remaining = PAGE_SIZE
            to_write = buffer[:remaining]
            st.session_state.pages[-1] += to_write
            buffer = buffer[remaining:]
        # Show the last page if it’s the current one or if final
        if st.session_state.current_page == len(st.session_state.pages) - 1 or final:
            show_current_page()
        buffer = ""

    try:
        for event_type, loop_idx, _, payload in agent.run():
            if event_type == "chunk":
                buffer += payload
                # Flush when buffer ends in a sentence ender or is large
                if any(buffer.rstrip().endswith(p) for p in sentence_enders) or len(buffer) > 200:
                    flush_buffer_ui()

            elif event_type == "loop_end":
                # Flush remaining buffer before updating progress
                flush_buffer_ui(final=True)
                frac = loop_idx / total_loops
                st.session_state.progress_bar.progress(frac)

            elif event_type == "error":
                # Flush remaining buffer before showing error
                flush_buffer_ui(final=True)
                message, exc = payload
                st.session_state.error_container.empty()
                logger.display_interactive(st.session_state.error_container, message, exc)
                return

        # After all loops finish, flush any leftover buffer
        flush_buffer_ui(final=True)

    except Exception as e:
        logger.log("ERROR", "Unexpected exception in UI stream", e)
        logger.display_interactive(st.session_state.error_container, "Unexpected error", e)
        return

    # Completed all loops: build and save final Markdown
    history = agent_state.get_state("history") or []
    md_content = build_markdown(history, st.session_state.topic)
    filename = suggest_filename(st.session_state.topic)
    try:
        saved = output_manager.save_output(filename, md_content)
        st.success(f"Final Markdown saved to {saved}")
        st.download_button("Download Markdown", data=md_content, file_name=filename, mime="text/markdown")
    except Exception as e:
        logger.log("ERROR", "Failed to save final Markdown in UI", e)
        logger.display_interactive(st.session_state.error_container, "Failed to save final output", e)


# Button interactions
if start_btn:
    if start_agent():
        run_stream()

if pause_btn and st.session_state.agent:
    st.session_state.agent.request_pause()

if resume_btn and st.session_state.agent:
    st.session_state.agent.resume()
    run_stream()

if stop_btn and st.session_state.agent:
    st.session_state.agent.request_cancel()

if prev_page_btn and st.session_state.current_page > 0:
    st.session_state.current_page -= 1
    show_current_page()

if next_page_btn and st.session_state.current_page < len(st.session_state.pages) - 1:
    st.session_state.current_page += 1
    show_current_page()
