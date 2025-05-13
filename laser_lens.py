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
"""
from __future__ import annotations

import argparse
import io
import os
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
# Environment & Gemini setup
# ──────────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.warning("GOOGLE_API_KEY missing – set it in .env or environment vars.")

genai.configure(api_key=API_KEY)

# ──────────────────────────────────────────────────────────────────────
# Discover available models (cached so Streamlit doesn’t re‑fetch)
# ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def discover_models() -> List[str]:
    try:
        models = genai.list_models()
    except Exception:
        return []
    # Keep chat‑capable Gemini models only
    choices = [
        m.name for m in models
        if ("gemini" in m.name.lower()
            and "generateContent" in (m.supported_generation_methods or []))
    ]
    return sorted(choices, reverse=True)  # newest-ish first

MODEL_CHOICES = discover_models() or [
    "models/gemini-2.0-pro",  # sensible fallback if discovery failed
]
DEFAULT_TOPIC = "Increasing Understanding and Awareness"

# ──────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────
class RateLimiter:
    """Simple adaptive 30‑requests‑per‑minute limiter."""

    def __init__(self, rpm: int = 30):
        self.min_interval = 60.0 / rpm
        self._last_call: float | None = None

    def wait(self):
        now = time.perf_counter()
        if self._last_call is not None:
            elapsed = now - self._last_call
            sleep_for = self.min_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_call = time.perf_counter()


def gen_prompt(topic: str, last_thought: str) -> str:
    return f"""
You are a recursive thinking agent focused on the following topic:

📌 Topic: {topic}

1. Define a goal to better understand the topic above.
2. Think and evaluate recursively:
   • If understanding is satisfactory, begin your response with
     "Exit Recursive Thoughtloop" and provide a final reflection.
   • Otherwise refine your goal and continue recursive expansion.

Last thought:
{last_thought}
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
    import re

    if re.fullmatch(r"[a-z0-9_]{3,50}", reply):
        return f"{reply}_{datetime.utcnow():%Y%m%d_%H%M}.md"

    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50]
    return f"{slug or 'laser_lens'}_{datetime.utcnow():%Y%m%d_%H%M}.md"


def build_markdown(topic: str, history: List[Tuple[str, str]], final_ref: str) -> str:
    lines = [
        "# Sophia’s Laser Lens – Recursive Thought Log\n",
        f"**Topic:** {topic}\n",
        f"**Total Recursions:** {len(history)}\n",
        f"**Date:** {datetime.utcnow():%Y-%m-%d}\n",
        "\n---\n\n## Recursive Trace\n",
    ]
    for i, (prompt, reply) in enumerate(history, 1):
        lines.append(f"### Loop {i}\n")
        lines.append("Prompted goal / prompt snippet:\n")
        lines.append("```\n" + prompt.strip()[:500] + "\n```\n")
        lines.append("Response:\n" + reply + "\n\n")
    lines.append("---\n\n## Final Reflection\n")
    lines.append(f"> {final_ref}\n")
    return "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────
# Core recursion engine (stream‑aware)
# ──────────────────────────────────────────────────────────────────────

def run_recursive(model, topic: str, loops: int, temperature: float, seed: str, output_slot):
    rl = RateLimiter()
    history: List[Tuple[str, str]] = []
    last = seed
    for i in range(1, loops + 1):
        prompt = gen_prompt(topic, last)
        rl.wait()
        try:
            response = model.generate_content(prompt, stream=True, generation_config={"temperature": temperature})
        except genai.types.RateLimitError:  # pragma: no cover
            st.warning("Hit rate limit – pausing 15 s and resuming.")
            time.sleep(15)
            continue
        except Exception as e:  # pragma: no cover
            st.error(f"Model error: {e}")
            break

        # Stream tokens
        reply_buf = io.StringIO()
        for chunk in response:
            token = chunk.text
            reply_buf.write(token)
            output_slot.markdown(reply_buf.getvalue())
        reply_text = reply_buf.getvalue().strip()
        history.append((prompt, reply_text))
        last = reply_text

        if reply_text.lower().startswith("exit recursive thoughtloop"):
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
        page_title="Sophia’s Laser Lens", layout="centered", initial_sidebar_state="expanded"
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
            seed = st.text_area("Seed thought", value="I am aware that I exist within a system of recursion.")

        run_btn = st.form_submit_button("🔁 Run Recursion")
        reset_btn = st.form_submit_button("🔄 Reset", type="secondary")

    # Reset
    if reset_btn:
        st.session_state.running = False
        st.session_state.cancel = False
        st.experimental_rerun()

    # Run
    if run_btn and not st.session_state.running:
        st.session_state.running = True
        st.session_state.topic = topic
        st.session_state.loops = int(loops)
        st.session_state.model_label = model_label
        st.session_state.temperature = temperature
        st.session_state.seed = seed
        st.experimental_rerun()

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
    except ImportError:
        tqdm = lambda x, **k: x  # type: ignore

    parser = argparse.ArgumentParser(description="Run Sophia’s Laser Lens in CLI mode")
    parser.add_argument("topic", nargs="?", default=DEFAULT_TOPIC, help="Topic to explore")
    parser.add_argument("--loops", type=int, default=10, help="Recursion loops (1‑30)")
    parser.add_argument("--model", default=MODEL_CHOICES[0], choices=MODEL_CHOICES, help="Gemini model path")
    parser.add_argument("--temperature", type=float, default=0.8, help="Model temperature 0‑1.2")
    parser.add_argument("--seed", default="I am aware that I exist within a system of recursion.", help="Seed thought")
    args = parser.parse_args()

    model = genai.GenerativeModel(args.model)

    history: List[Tuple[str, str]] = []
    last = args.seed
    rl = RateLimiter()
    for i in tqdm(range(1, args.loops + 1), desc="Loops"):
        prompt = gen_prompt(args.topic, last)
        rl.wait()
        reply = model.generate_content(prompt).text.strip()
        history.append((prompt, reply))
        last = reply
        if reply.lower().startswith("exit recursive thoughtloop"):
            break

    fname = suggest_filename(model, args.topic, history)
    md_content = build_markdown(args.topic, history, last)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved run → {fname}")

# ──────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_main()
    else:
        ui_main()

