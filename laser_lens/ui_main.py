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

from utils import suggest_filename, load_pref_model, save_pref_model

# Helper to fetch model list (same as in cli_main.py)
def get_available_models() -> list[str]:
    try:
        import google.generativeai as genai_list
        from dotenv import load_dotenv

        load_dotenv()
        genai_list.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        models_available = [
            m.name
            for m in genai_list.list_models()
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
command_executor = CommandExecutor(logger)
context_manager = ContextManager(config)
output_manager = OutputManager(config, logger)
agent_state = AgentState(config, logger)

st.set_page_config(page_title="Laser Lens UI", layout="wide")

# Load dynamic model list and default index
models_available = get_available_models()
saved_model = load_pref_model(models_available)
default_index = models_available.index(saved_model) if saved_model in models_available else 0

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
if "model_idx" not in st.session_state:
    st.session_state.model_idx = default_index
if "model_name" not in st.session_state:
    st.session_state.model_name = models_available[default_index]

# Sidebar: File uploader for context or resume (.md, .txt, .tmp)
st.sidebar.header("Upload Context / Resume")
uploaded_files = st.sidebar.file_uploader(
    "Upload .md, .txt or .tmp", type=["md", "txt", "tmp"], accept_multiple_files=True
)
if uploaded_files:
    for uf in uploaded_files:
        try:
            content = uf.read()
            context_manager.upload_context(uf.name, content)
        except Exception as e:
            logger.log("WARNING", f"Failed to upload {uf.name}", e)

# Sidebar: Parameters
st.sidebar.markdown("---")
st.sidebar.header("Agent Settings")

topic = st.sidebar.text_input("Topic", value=st.session_state.topic)
st.session_state.topic = topic

loops = st.sidebar.slider(
    "Recursion Loops", min_value=1, max_value=10, value=st.session_state.loops
)
st.session_state.loops = loops

# Dynamic Model Selection
selected_model = st.sidebar.selectbox(
    "Model",
    models_available,
    index=st.session_state.model_idx,
    key="model_name"
)
st.session_state.model_name = selected_model
model_idx = models_available.index(selected_model)
st.session_state.model_idx = model_idx

temperature = st.sidebar.slider("Temperature", 0.0, 1.0, value=config.default_temperature)
seed = st.sidebar.number_input("Seed (optional)", min_value=0, max_value=2**32 - 1, value=0)
rpm = st.sidebar.number_input("Requests/minute", min_value=1, max_value=100, value=config.default_rpm)

# Sidebar: Control Buttons
st.sidebar.markdown("---")
start_btn = st.sidebar.button("▶️ Start")
pause_btn = st.sidebar.button("⏸️ Pause")
resume_btn = st.sidebar.button("▶️ Resume")
stop_btn = st.sidebar.button("⏹️ Stop")

# Main area placeholders
if st.session_state.stream_placeholder is None:
    st.session_state.stream_placeholder = st.empty()
if st.session_state.progress_bar is None:
    st.session_state.progress_bar = st.sidebar.progress(0.0)
if st.session_state.error_container is None:
    st.session_state.error_container = st.empty()


def start_agent():
    """Initialize a fresh agent and clear previous displays."""
    # Save the chosen model so next time it’s the default
    chosen_model = models_available[st.session_state.model_idx]
    save_pref_model(chosen_model)

    # Clear previous state if any
    agent_state.delete_state("history")
    agent_state.delete_state("last_thought")
    agent_state.delete_state("current_loop")
    agent_state.delete_state("paused")
    agent_state.delete_state("cancelled")
    agent_state.save_state()

    st.session_state.stream_placeholder.empty()
    st.session_state.progress_bar.progress(0.0)
    st.session_state.error_container.empty()

    # Instantiate agent with the real Gemini client
    try:
        st.session_state.agent = RecursiveAgent(
            config=config,
            error_logger=logger,
            command_executor=command_executor,
            context_manager=context_manager,
            output_manager=output_manager,
            agent_state=agent_state,
            model_name=models_available[st.session_state.model_idx],
            topic=topic,
            loops=loops,
            temperature=temperature,
            seed=seed or None,
            rpm=rpm,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    except Exception as e:
        st.session_state.error_container.error(f"Failed to initialize agent: {e}")
        return


def run_stream():
    """Run agent.run() and render streaming output, progress, and errors."""
    agent = st.session_state.agent
    total_loops = agent.loops

    try:
        for event_type, loop_idx, _, payload in agent.run():
            if event_type == "chunk":
                # Display chunk text
                st.session_state.stream_placeholder.write(payload, unsafe_allow_html=True)
            elif event_type == "loop_end":
                frac = loop_idx / total_loops
                st.session_state.progress_bar.progress(frac)
            elif event_type == "error":
                message, exc = payload
                st.session_state.error_container.empty()
                logger.display_interactive(st.session_state.error_container, message, exc)
                return
    except Exception as e:
        logger.log("ERROR", "Unexpected exception in UI stream", e)
        logger.display_interactive(st.session_state.error_container, "Unexpected error", e)
        return

    # Completed all loops: build and save final Markdown
    history = agent_state.get_state("history") or []
    md_content = build_markdown(history, topic)
    filename = suggest_filename(topic)
    try:
        saved = output_manager.save_output(filename, md_content)
        st.success(f"Final Markdown saved to {saved}")
        st.download_button("Download Markdown", data=md_content, file_name=filename, mime="text/markdown")
    except Exception as e:
        logger.log("ERROR", "Failed to save final Markdown in UI", e)
        logger.display_interactive(st.session_state.error_container, "Failed to save final output", e)


# Button interactions
if start_btn:
    start_agent()
    run_stream()

if pause_btn and st.session_state.agent:
    st.session_state.agent.request_pause()

if resume_btn and st.session_state.agent:
    st.session_state.agent.resume()
    run_stream()

if stop_btn and st.session_state.agent:
    st.session_state.agent.request_cancel()
