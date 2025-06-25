# ui_main.py

import os
import re
import json
import streamlit as st
import streamlit.components.v1 as components

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
    load_api_keys,
    save_api_key,
    delete_api_key,
    load_pref_key,
    save_pref_key,
)
from command_registration import register_core_commands


def get_available_models(api_key: str | None = None) -> list[str]:
    """Return available Gemini models using *api_key* if provided."""
    try:
        import google.generativeai as genai_list
        if api_key is None:
            from dotenv import load_dotenv

            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY")
        genai_list.configure(api_key=api_key)  # type: ignore[attr-defined]

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


def selected_api_key_value() -> str:
    """Return the currently selected API key value if available."""
    name = st.session_state.get("api_key_name", "")
    for entry in st.session_state.get("api_keys", []):
        if entry.get("name") == name:
            return entry.get("key", "")
    return os.getenv("GOOGLE_API_KEY", "")


# Initialize singletons
config = Config()
logger = ErrorLogger(config)
output_manager = OutputManager(config, logger)
# Persist ContextManager across reruns so uploaded files aren't lost
if "context_manager" not in st.session_state:
    st.session_state.context_manager = ContextManager(config, logger, output_manager)
context_manager = st.session_state.context_manager
agent_state = AgentState(config, logger)

# Register command handlers
ce = CommandExecutor(logger)
register_core_commands(ce)
try:
    from command_registration import register_plugin_commands
    register_plugin_commands(ce)
except Exception:
    pass

st.set_page_config(page_title="Laser Lens UI", layout="wide")

# Load dynamic model list once per session
if "models_available" not in st.session_state:
    st.session_state.models_available = get_available_models(os.getenv("GOOGLE_API_KEY"))
models_available = st.session_state.models_available

if "model_name" not in st.session_state:
    saved_model = load_pref_model(models_available)
    st.session_state.model_name = (
        saved_model if saved_model in models_available else models_available[0]
    )
if "model_idx" not in st.session_state:
    st.session_state.model_idx = models_available.index(st.session_state.model_name)

if "api_keys" not in st.session_state:
    st.session_state.api_keys = load_api_keys()
if "api_key_name" not in st.session_state:
    names = [k["name"] for k in st.session_state.api_keys]
    default_key = load_pref_key(names) if names else ""
    st.session_state.api_key_name = default_key if default_key in names else (names[0] if names else "")

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
if "thinking_mode" not in st.session_state:
    st.session_state.thinking_mode = config.default_thinking_mode
if "reset_pause_msg" not in st.session_state:
    st.session_state.reset_pause_msg = False

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
    topic_in = st.text_input("Topic", value=st.session_state.topic, key="topic_in")
    loops_in = st.slider(
        "Recursion Loops", min_value=1, max_value=500, value=st.session_state.loops, key="loops_in"
    )
    st.selectbox(
        "Model",
        models_available,
        key="model_name",
    )
    key_names = [k["name"] for k in st.session_state.api_keys]
    if key_names:
        st.selectbox("API Key", key_names, key="api_key_name")
    temp_in = st.slider(
        "Temperature", 0.0, 1.0, value=st.session_state.temperature, key="temp_in"
    )
    seed_in = st.number_input(
        "Seed (optional)",
        min_value=0,
        max_value=2**32 - 1,
        value=st.session_state.seed,
        key="seed_in",
    )
    rpm_in = st.number_input(
        "Requests/minute", min_value=1, max_value=100, value=st.session_state.rpm, key="rpm_in"
    )
    thinking_in = st.checkbox(
        "Thinking Mode",
        value=st.session_state.thinking_mode,
        key="thinking_in",
    )
    btn_cols = st.columns(2)
    with btn_cols[0]:
        apply_btn = st.form_submit_button("Apply")
    with btn_cols[1]:
        start_btn = st.form_submit_button("▶️", help="Start")

manage_btn = st.sidebar.button("Manage Keys")
if manage_btn:
    st.session_state.show_manage_key = True
    st.session_state.manage_selected = st.session_state.get("api_key_name", "")

if st.session_state.get("show_manage_key"):
    with st.sidebar.form("manage_key_form"):
        names = [k["name"] for k in st.session_state.api_keys]
        choices = ["<New>"] + names
        idx = choices.index(st.session_state.get("manage_selected", "<New>")) if st.session_state.get("manage_selected", "<New>") in choices else 0
        choice = st.selectbox("Select", choices, index=idx, key="manage_select")
        if choice != "<New>":
            entry = next((e for e in st.session_state.api_keys if e.get("name") == choice), {})
            key_name = st.text_input("Name", value=entry.get("name", ""), key="edit_key_name")
            key_value = st.text_input("Value", value=entry.get("key", ""), type="password", key="edit_key_value")
            key_desc = st.text_input("Description", value=entry.get("description", ""), key="edit_key_desc")
        else:
            key_name = st.text_input("Name", key="edit_key_name")
            key_value = st.text_input("Value", type="password", key="edit_key_value")
            key_desc = st.text_input("Description", key="edit_key_desc")
        save_k = st.form_submit_button("Save")
        delete_k = st.form_submit_button("Delete")
        cancel_k = st.form_submit_button("Cancel")
    if save_k and key_name and key_value:
        save_api_key(key_name, key_value, key_desc) # type: ignore[call-arg]
        st.session_state.api_keys = load_api_keys()
        st.session_state.api_key_name = key_name
        save_pref_key(key_name)
        st.session_state.show_manage_key = False
    elif delete_k and choice != "<New>":
        delete_api_key(choice)
        st.session_state.api_keys = load_api_keys()
        remaining = [k["name"] for k in st.session_state.api_keys]
        st.session_state.api_key_name = remaining[0] if remaining else ""
        save_pref_key(st.session_state.api_key_name)
        st.session_state.show_manage_key = False
    elif cancel_k:
        st.session_state.show_manage_key = False

if apply_btn or start_btn:
    st.session_state.topic = topic_in
    st.session_state.loops = loops_in
    st.session_state.temperature = temp_in
    st.session_state.seed = seed_in
    st.session_state.rpm = rpm_in
    st.session_state.thinking_mode = thinking_in
    new_models = get_available_models(selected_api_key_value())
    st.session_state.models_available = new_models
    if st.session_state.model_name not in new_models:
        st.session_state.model_name = new_models[0]
    st.session_state.model_idx = new_models.index(st.session_state.model_name)

# Keep model_idx consistent with model_name on every run
if st.session_state.model_name in st.session_state.models_available:
    st.session_state.model_idx = st.session_state.models_available.index(
        st.session_state.model_name
    )
else:
    st.session_state.model_name = st.session_state.models_available[0]
    st.session_state.model_idx = 0

# Sidebar: Control Buttons
st.sidebar.markdown("---")

paused_reason = agent_state.get_state("paused")
cancel_reason = agent_state.get_state("cancelled")
reason_display = paused_reason or cancel_reason or ""
reason_disabled = bool(reason_display)

if reason_disabled:
    action_reason = st.sidebar.text_input(
        "Reason", value=reason_display, key="action_reason", disabled=True
    )
else:
    action_reason = st.sidebar.text_input("Reason", key="action_reason")
btn_cols = st.sidebar.columns(3, gap="small")
with btn_cols[0]:
    pause_btn = st.button("⏸️", help="Pause", use_container_width=True)
with btn_cols[1]:
    resume_btn = st.button("▶️", help="Resume", use_container_width=True)
with btn_cols[2]:
    stop_btn = st.button("⏹️", help="Stop", use_container_width=True)
st.sidebar.markdown(
    """
    <style>
    div[data-testid="column"] > div.stButton button {
        width: 3em;
        height: 3em;
        padding: 0;
        margin: 0 0.25em 0.25em 0;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Message box (enabled when paused)
if st.session_state.reset_pause_msg:
    st.session_state.pause_msg = ""
    st.session_state.reset_pause_msg = False
msg = st.sidebar.text_input(
    "Message to Agent", key="pause_msg", disabled=not agent_state.get_state("paused")
)
send_msg_btn = st.sidebar.button(
    "Send Message", key="send_msg", disabled=not agent_state.get_state("paused")
)
if send_msg_btn and msg.strip():
    context_manager.add_inline_context(msg.strip())
    st.sidebar.success("Message queued for next run.")
    st.session_state.reset_pause_msg = True

if paused_reason:
    st.sidebar.info(f"Agent paused: {paused_reason}")
if cancel_reason:
    st.sidebar.info(f"Agent cancelled: {cancel_reason}")
current_loop = agent_state.get_state("current_loop") or 0
status = "Idle"
if cancel_reason:
    status = f"Cancelled at loop {current_loop}"
elif paused_reason:
    status = f"Paused at loop {current_loop}"
elif st.session_state.agent is not None:
    status = f"Running loop {current_loop} of {st.session_state.loops}"
st.sidebar.markdown(f"**Status:** {status}")

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
st.sidebar.markdown("[📖 Documentation](/docs/index.html)")


def start_agent() -> bool:
    """
    Initialize a fresh agent, clearing previous displays and state.
    Any files already uploaded into `context_manager` will remain.
    """
    # Save the chosen model so next time it’s the default
    chosen_model = models_available[st.session_state.model_idx]
    save_pref_model(chosen_model)
    save_pref_key(st.session_state.api_key_name)

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
    st.session_state.stream_blocks = []

    # Instantiate the agent (it will call get_context() under the hood)
    try:
        api_key_val = selected_api_key_value()
        if not api_key_val:
            st.session_state.error_container.error("No API key selected")
            return False

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
            api_key=api_key_val,
            thinking_mode=st.session_state.thinking_mode,
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

    # Pattern to intercept command markers
    cmd_pattern = re.compile(r"\[\[COMMAND:\s*(?P<name>\w+)(?P<args>.*?)\]\]", re.DOTALL)

    loop_container = None
    text_placeholder = None
    render_container = None
    current_loop = 0
    buffer = ""

    try:
        for event_type, loop_idx, _, payload in agent.run():
            if loop_idx != current_loop:
                current_loop = loop_idx
                loop_container = st.expander(f"Loop {loop_idx}", expanded=True)
                text_placeholder = loop_container.empty()
                render_container = loop_container.container()
                st.session_state.stream_blocks.append(loop_container)
                buffer = ""

            if event_type == "chunk":
                buffer += payload
                if text_placeholder:
                    text_placeholder.markdown(buffer)

            elif event_type == "loop_end":
                # Re-render final loop with command outputs
                full_text = buffer
                if text_placeholder:
                    text_placeholder.empty()
                render_container = loop_container.container() # type: ignore[assignment]
                results = agent_state.get_state("command_results") or []
                pos = 0
                r_idx = 0
                for m in cmd_pattern.finditer(full_text):
                    pre = full_text[pos:m.start()]
                    if pre.strip():
                        render_container.markdown(pre)
                    cmd_name = m.group("name")
                    arg_str = m.group("args").strip()
                    result = results[r_idx][1] if r_idx < len(results) else ""
                    render_container.info(f"\u25B6 {cmd_name} {arg_str}")
                    render_container.code(str(result), language="bash")
                    pos = m.end()
                    r_idx += 1
                if pos < len(full_text):
                    render_container.markdown(full_text[pos:])
                copy_id = f"copy_{loop_idx}"
                safe = json.dumps(full_text)
                # Embed button and script so clipboard copy works reliably
                copy_html = f"""
                <button id='{copy_id}'>\U0001F4CB Copy</button>
                <script>
                document.getElementById('{copy_id}').addEventListener('click', function() {{
                    navigator.clipboard.writeText({safe});
                }});
                </script>
                """
                components.html(copy_html, height=32)
                buffer = ""

                frac = loop_idx / total_loops
                st.session_state.progress_bar.progress(frac)

                # Auto-scroll to newest output
                st.markdown(
                    "<script>window.scrollTo(0, document.body.scrollHeight);</script>",
                    unsafe_allow_html=True,
                )
                # Next loop expander will be created on-demand when output for
                # that loop arrives. This avoids showing a blank container.

            elif event_type == "error":
                message, exc = payload
                if "quota" in message.lower():
                    st.session_state.error_container.error(message)
                else:
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

    except CancelledException:
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
        session_meta = {
            "topic": st.session_state.topic,
            "loops": st.session_state.loops,
            "model": models_available[st.session_state.model_idx],
            "temperature": st.session_state.temperature,
            "seed": st.session_state.seed,
            "rpm": st.session_state.rpm,
            "output_file": saved,
        }
        output_manager.save_session_metadata(session_meta)
        # Mark run as complete so sidebar status shows "Idle"
        st.session_state.agent = None
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
    st.session_state.agent.request_pause(action_reason or "user pause")

if resume_btn and st.session_state.agent:
    # Scroll to the bottom so rendering continues from the last loop
    st.markdown(
        "<script>window.scrollTo(0, document.body.scrollHeight);</script>",
        unsafe_allow_html=True,
    )
    st.session_state.agent.resume()
    run_stream()

if stop_btn and st.session_state.agent:
    st.session_state.agent.request_cancel(action_reason or "user cancel")
