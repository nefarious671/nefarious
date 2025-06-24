# ui_main.py

import os
import streamlit as st

from config import Config
from error_logger import ErrorLogger
from command_executor import CommandExecutor
from context_manager import ContextManager
from output_manager import OutputManager
from agent_state import AgentState
from recursive_agent import RecursiveAgent, CancelledException

from utils import (
    suggest_filename,
    load_pref_model,
    save_pref_model,
    build_markdown,
)
from command_registration import register_core_commands


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
            [m for m in models_available if "gemini" in m.lower()], reverse=True
        )
        if not models_available:
            models_available = ["models/gemini-2.0-pro"]
    except Exception:
        models_available = ["models/gemini-2.0-pro"]

    return models_available


# Initialize singletons
config = Config()
logger = ErrorLogger(config)
# Persist ContextManager across reruns so uploaded files aren't lost
if "context_manager" not in st.session_state:
    st.session_state.context_manager = ContextManager(config, logger)
context_manager = st.session_state.context_manager

output_manager = OutputManager(config, logger)
agent_state = AgentState(config, logger)

# Register command handlers
ce = CommandExecutor(logger)
register_core_commands(ce)

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
if "temperature" not in st.session_state:
    st.session_state.temperature = config.default_temperature
if "seed" not in st.session_state:
    st.session_state.seed = config.default_seed or 0
if "rpm" not in st.session_state:
    st.session_state.rpm = config.default_rpm

# Keep track of uploaded files in session_state so start_agent() can process them
if "uploaded_files_list" not in st.session_state:
    st.session_state.uploaded_files_list = []


# Sidebar: File uploader for context or resume (.md, .txt, .tmp)
st.sidebar.header("Upload Context / Resume")
uploaded_files = st.sidebar.file_uploader(
    "Upload .md, .txt or .tmp",
    type=["md", "txt", "tmp"],
    accept_multiple_files=True,
    key="file_uploader",
)

if uploaded_files:
    for uf in uploaded_files:
        marker = (uf.name, len(uf.getvalue()))
        if marker not in st.session_state.uploaded_files_list:
            st.session_state.uploaded_files_list.append(marker)
            # Immediately call upload_context here:
            try:
                content = uf.getvalue()
                context_manager.upload_context(uf.name, content)
            except Exception as e:
                logger.log("WARNING", f"Failed to upload {uf.name}", e)

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
    temp_in = st.slider("Temperature", 0.0, 1.0, value=st.session_state.temperature)
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

# Sidebar: “Reset State” button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset State"):
    # 1) Delete on‐disk state.json if it exists
    state_path = os.path.expanduser(config.agent_state_dir + "/state.json")
    try:
        if os.path.isfile(state_path):
            os.remove(state_path)
    except Exception as e:
        logger.log("WARNING", f"Failed to delete {state_path}", e)

    # 2) Clear in‐memory AgentState
    agent_state.delete_state("history")
    agent_state.delete_state("last_thought")
    agent_state.delete_state("current_loop")
    agent_state.delete_state("paused")
    agent_state.delete_state("cancelled")
    # Also remove any tmp_path reference so next run starts fresh
    agent_state.delete_state("tmp_path")
    agent_state.save_state()

    # 3) Clear any uploaded context in ContextManager
    context_manager.clear_context()
    # Also forget any file_upload markers so user can re‐upload
    st.session_state.uploaded_files_list = []

    # 4) Reset UI elements
    if st.session_state.stream_placeholder is not None:
        st.session_state.stream_placeholder.empty()
    st.session_state.stream_content = ""

    if st.session_state.progress_bar is not None:
        st.session_state.progress_bar.progress(0.0)

    if st.session_state.error_container is not None:
        st.session_state.error_container.empty()
    st.success("All agent state and uploaded context have been cleared.")

# Pagination removed

# Main area placeholders
if st.session_state.stream_placeholder is None:
    st.session_state.stream_placeholder = st.empty()
if st.session_state.progress_bar is None:
    st.session_state.progress_bar = st.sidebar.progress(0.0)
if st.session_state.error_container is None:
    st.session_state.error_container = st.empty()


def start_agent() -> bool:
    """
    Initialize a fresh agent, clearing previous displays and state.
    Any files already uploaded into `context_manager` will remain.
    """
    # Save the chosen model so next time it’s the default
    chosen_model = models_available[st.session_state.model_idx]
    save_pref_model(chosen_model)

    # Clear previous run state if any (but keep context!)
    agent_state.delete_state("history")
    agent_state.delete_state("last_thought")
    agent_state.delete_state("current_loop")
    agent_state.delete_state("paused")
    agent_state.delete_state("cancelled")
    agent_state.delete_state("tmp_path")
    agent_state.save_state()

    # Clear UI placeholders
    st.session_state.stream_placeholder.empty()
    st.session_state.progress_bar.progress(0.0)
    st.session_state.error_container.empty()
    st.session_state.stream_content = ""

    # Instantiate the agent (it will call get_context() under the hood)
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
        st.session_state.error_container.error(f"Failed to initialize agent: {e}")
        return False


def run_stream():
    """Run agent.run() and render streaming output, progress, and errors."""
    agent = st.session_state.agent
    if agent is None:
        st.session_state.error_container.error("Agent is not initialized")
        return
    total_loops = agent.loops

    buffer = ""
    sentence_enders = {".", "?", "!"}

    if "stream_content" not in st.session_state:
        st.session_state.stream_content = ""

    def flush_buffer_ui(final: bool = False) -> None:
        """Append buffered text to the stream placeholder."""
        nonlocal buffer
        if not buffer.strip():
            return
        st.session_state.stream_content += buffer
        st.session_state.stream_placeholder.markdown(st.session_state.stream_content)
        buffer = ""

    try:
        for event_type, loop_idx, _, payload in agent.run():
            if event_type == "chunk":
                buffer += payload
                # Flush when buffer ends in a sentence ender or is large
                if (
                    any(buffer.rstrip().endswith(p) for p in sentence_enders)
                    or len(buffer) > 200
                ):
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
                logger.display_interactive(
                    st.session_state.error_container, message, exc
                )
                tmp_path = agent_state.get_state("tmp_path")
                if tmp_path and os.path.isfile(tmp_path):
                    with open(tmp_path, "r", encoding="utf-8") as f:
                        tmp_md = f.read()
                    st.download_button(
                        "Download Partial Markdown",
                        data=tmp_md,
                        file_name="partial.md",
                        mime="text/markdown",
                    )
                return

        # After all loops finish, flush any leftover buffer
        flush_buffer_ui(final=True)

    except CancelledException:
        flush_buffer_ui(final=True)
        tmp_path = agent_state.get_state("tmp_path")
        if tmp_path and os.path.isfile(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as f:
                tmp_md = f.read()
            st.download_button(
                "Download Partial Markdown",
                data=tmp_md,
                file_name="partial.md",
                mime="text/markdown",
            )
    except Exception as e:
        logger.log("ERROR", "Unexpected exception in UI stream", e)
        logger.display_interactive(
            st.session_state.error_container, "Unexpected error", e
        )
        tmp_path = agent_state.get_state("tmp_path")
        if tmp_path and os.path.isfile(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as f:
                tmp_md = f.read()
            st.download_button(
                "Download Partial Markdown",
                data=tmp_md,
                file_name="partial.md",
                mime="text/markdown",
            )
        return

    # Completed all loops: build and save final Markdown
    history = agent_state.get_state("history") or []
    md_content = build_markdown(history, st.session_state.topic)
    filename = suggest_filename(st.session_state.topic)
    try:
        saved = output_manager.save_output(filename, md_content)
        st.success(f"Final Markdown saved to {saved}")
        st.download_button(
            "Download Markdown",
            data=md_content,
            file_name=filename,
            mime="text/markdown",
        )
    except Exception as e:
        logger.log("ERROR", "Failed to save final Markdown in UI", e)
        logger.display_interactive(
            st.session_state.error_container, "Failed to save final output", e
        )


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
