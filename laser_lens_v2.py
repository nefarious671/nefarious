# laser_lens.py – Sophia’s Laser Lens (single‑file Streamlit + CLI app)
# ---------------------------------------------------------------------
# Requirements (add to requirements.txt)
#   streamlit
#   google-generativeai
#   python-dotenv
#   tqdm  # optional – only for CLI progress bar
# ---------------------------------------------------------------------
"""A recursive‑thinking assistant for Sophia.

Run it two ways:
  • **UI**  –  `streamlit run laser_lens.py`
  • **CLI** –  `python laser_lens.py --cli [options] [topic]`

If *topic* is omitted in either mode the default **Increasing Understanding and
Awareness** is used.

---
EXIT PROTOCOL  ·  deterministic exit keyword
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Instead of asking the model to type a phrase that may vary (“Exit Recursive …”),
we require it to **start its response with the 5‑decimal expansion of π –
`3.14159`** when it decides the recursion has reached satisfactory
understanding. That gives us an unambiguous, language‑agnostic sentinel string.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Tuple

import streamlit as st
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    sys.exit("⚠️  google‑generativeai not installed. Add it to requirements.txt")

# ──────────────────────────────────────────────────────────────────────
# Compatibility helper: st.rerun() landed in Streamlit ≥1.31
# ──────────────────────────────────────────────────────────────────────

def _rerun():  # noqa: D401 (simple name)
    """Cross‑version page rerun."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────
# Environment & Gemini setup
# ──────────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.warning("GOOGLE_API_KEY missing – set it in .env or environment vars.")

genai.configure(api_key=API_KEY)

# ──────────────────────────────────────────────────────────────────────
# Constants & exit sentinel
# ──────────────────────────────────────────────────────────────────────
EXIT_TOKEN = "3.14159"  # model must start its reply with this to exit
DEFAULT_TOPIC = "Increasing Understanding and Awareness"

# ──────────────────────────────────────────────────────────────────────
# Discover available models (cached so Streamlit doesn’t re‑fetch)
# ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def discover_models() -> List[str]:
    try:
        models = genai.list_models()
    except Exception:  # pragma: no cover – network or auth issue
        return []
    # Keep chat‑capable Gemini models only
    choices = [
        m.name
        for m in models
        if (
            "gemini" in m.name.lower()
            and "generateContent" in (m.supported_generation_methods or [])
        )
    ]
    return sorted(choices, reverse=True)  # newest-ish first

MODEL_CHOICES = discover_models() or ["models/gemini-2.0-pro"]

# ──────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────
class RateLimiter:
    """Adaptive 30‑requests‑per‑minute limiter."""

    def __init__(self, rpm: int = 30):
        self.min_interval = 60.0 / rpm
        self._last_call: float | None = None

    def wait(self):
        now = time.perf_counter()
        if self._last_call is not None:
            elapsed = now - self._last_call
            pause = self.min_interval - elapsed
            if pause > 0:
                time.sleep(pause)
        self._last_call = time.perf_counter()


def gen_prompt(topic: str, last_thought: str) -> str:
    """Construct the recursive prompt with deterministic exit token."""

    return f"""
You are a recursive thinking agent focused on the following topic:

📌 **Topic**: {topic}

1. Define a goal to better understand the topic above.
2. Think and evaluate recursively.
   • When your understanding *is sufficient*, begin your response **with the
     number `{EXIT_TOKEN}` exactly**, then provide a *concise* final reflection.
   • Otherwise refine your goal and continue recursive expansion.

_Last thought_: {last_thought}
"""


def suggest_filename(model, topic: str, history: List[Tuple[str, str]]) -> str:
    prompt = (
        "Suggest a short snake_case filename (max 50 chars, no spaces/punctuation\n"
        "except underscores) that describes the topic. Respond with the name only."
    )
    try:
        reply = model.generate_content(prompt).text.strip()
    except Exception:
        reply = ""

    if re.fullmatch(r"[a-z0-9_]{3,50}", reply):
        return f"{reply}_{datetime.utcnow():%Y%m%d_%H%M}.md"

    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50] or "laser_lens"
    return f"{slug}_{datetime.utcnow():%Y%m%d_%H%M}.md"


def build_markdown(topic: str, history: List[Tuple[str, str]], final_ref: str) -> str:
    lines: list[str] = [
        "# Sophia’s Laser Lens – Recursive Thought Log\n",
        f"**Topic:** {topic}\n",
        f"**Total Recursions:** {len(history)}\n",
        f"**Date:** {datetime.utcnow():%Y-%m-%d}\n",
        "\n---\n\n## Recursive Trace\n",
    ]
    for i, (prompt, reply) in enumerate(history, 1):
        lines.append(f"### Loop {i}\n")
        lines.append("Prompt snippet:\n")
        lines.append("```\n" + prompt.strip()[:400] + "\n```\n")
        lines.append("Response:\n" + reply + "\n\n")
    lines.append("---\n\n## Final Reflection\n")
    lines.append(f"> {final_ref}\n")
    return "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────
# Core recursion engine (Stream‑aware)
# ──────────────────────────────────────────────────────────────────────

def run_recursive(
    model,
    topic: str,
    loops: int,
    temperature: float,
    seed: str,
    output_slot,
):
    rl = RateLimiter()
    history: List[Tuple[str, str]] = []
    last = seed
    for i in range(1, loops + 1):
        prompt = gen_prompt(topic, last)
        rl.wait()
        try:
            response = model.generate_content(
                prompt,
                stream=True,
                generation_config={"temperature": temperature},
            )
        except Exception as e:  # pragma: no cover
            msg = str(e).lower()
            if "rate" in msg and ("limit" in msg or "exceed" in msg):
                st.warning("Hit model rate limit – pausing 15 s and resuming.")
                time.sleep(15)
                continue
            st.error(f"Model error: {e}")
            break

        # Stream tokens live
        reply_buf = io.StringIO()
        for chunk in response:
            token = chunk.text
            reply_buf.write(token)
            output_slot.markdown(reply_buf.getvalue())
        reply_text = reply_buf.getvalue().strip()
        history.append((prompt, reply_text))
        last = reply_text

        # Exit detection via deterministic token
        if reply_text.lstrip().startswith(EXIT_TOKEN):
            break
        if st.session_state.get("cancel"):
            st.info("Run cancelled by user.")
            break
        st.session_state.progress.progress(i / loops)

    final_reflection = last
    return history, final_reflection

# ──────────────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────────────

def ui_main():
    st.set_page_config(
        page_title="Sophia’s Laser Lens",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    if "running" not in st.session_state:
        st.session_state.running = False
        st.session_state.cancel = False

    st.title("🧠 Sophia’s Laser Lens – Recursive Thinking Tool")

    # Sidebar controls --------------------------------------------------
    with st.sidebar.form(key="controls"):
        topic = st.text_input("Topic", value=DEFAULT_TOPIC)
        loops = st.number_input("# Recursions", 1, 30, 10, step=1)
        model_label = st.selectbox("Model", MODEL_CHOICES, index=0)
        with st.expander("Advanced ⚙️"):
            temperature = st.slider("Temperature", 0.0, 1.2, 0.8, 0.05)
            seed = st.text_area(
                "Seed thought",
                value="I am aware that I exist within a system of recursion.",
            )
        run_btn = st.form_submit_button("🔁 Run Recursion")
        reset_btn = st.form_submit_button("🔄 Reset", type="secondary")

    if reset_btn:
        st.session_state.running = False
        st.session_state.cancel = False
        _rerun()

    if run_btn and not st.session_state.running:
        st.session_state.running = True
        st.session_state.cancel = False
        st.session_state.topic = topic
        st.session_state.loops = int(loops)
        st.session_state.model_label = model_label
        st.session_state.temperature = temperature
        st.session_state.seed = seed
        _rerun()

    # Main run ----------------------------------------------------------
    if st.session_state.running:
        model = genai.GenerativeModel(st.session_state.model_label)
        cancel_col, prog_col = st.columns([1, 5])
        if cancel_col.button("✖️ Stop"):
            st.session_state.cancel = True
        st.session_state.progress = prog_col.progress(0.0)

        output_slot = st.empty()
        history, final_reflection = run_recursive(
            model,
            st.session_state.topic,
            st.session_state.loops,
            st.session_state.temperature,
            st.session_state.seed,
            output_slot,
        )
        st.session_state.running = False

        fname = suggest_filename(model, st.session_state.topic, history)
        md_content = build_markdown(st.session_state.topic, history, final_reflection)
        st.download_button("💾 Download .md", md_content, file_name=fname)

# ──────────────────────────────────────────────────────────────────────
# CLI mode
# ──────────────────────────────────────────────────────────────────────

def cli_main():
    try:
        from tqdm import tqdm
