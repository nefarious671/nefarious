# laser_lens.py – Sophia’s Laser Lens (single‑file Streamlit + CLI app)
# ---------------------------------------------------------------------
# Requirements (add to requirements.txt)
#   streamlit
#   google-generativeai
#   python-dotenv
#   tqdm          # optional – only for CLI progress bar
# ---------------------------------------------------------------------
"""A recursive‑thinking assistant for Sophia.

**Latest upgrades**
1. 🌡 **RPM throttle control** – user‑set requests‑per‑minute.
2. 💾 **Write‑as‑you‑go temp buffer** – streamed tokens mirrored to a temp file.
3. 🖼 **Segmented rendering** – only the last `SHOW_N` loops stay mounted.
4. 🔄 **Resume from .tmp** – upload a previous temp file or CLI `--resume`.
5. ⏸ **Pause / Resume button** – pauses after the *current* loop and can pick up
   instantly without re‑uploading the temp.
6. 🔢 **Live loop counter** – shows `Loop i / N` next to the progress bar.

Run two ways:
  • **UI**  – `streamlit run laser_lens.py`
  • **CLI** – `python laser_lens.py --cli [options] [topic]`
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
import tempfile
from datetime import datetime
from typing import List, Tuple

import streamlit as st
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────
# Constants & defaults
# ──────────────────────────────────────────────────────────────────────
SHOW_N = 5           # Visible loop segments in Streamlit DOM
DEFAULT_RPM = 10     # UI default – user‑adjustable
DELIM = "\n\n---\n\n"  # delimiter between replies in temp files

# ──────────────────────────────────────────────────────────────────────
# Helpers & polyfills
# ──────────────────────────────────────────────────────────────────────

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover
        _rerun()


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
# Discover available models (cached)
# ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def discover_models() -> List[str]:
    try:
        models = genai.list_models()
    except Exception:  # pragma: no cover
        return []
    return sorted(
        [m.name for m in models if "gemini" in m.name.lower() and "generateContent" in (m.supported_generation_methods or [])],
        reverse=True,
    )


MODEL_CHOICES = discover_models() or ["models/gemini-2.0-pro"]
DEFAULT_TOPIC = "Increasing Understanding and Awareness"

# ──────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────
class RateLimiter:
    """Adaptive X‑requests‑per‑minute limiter."""

    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(1, rpm)
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
2. Think and evaluate recursively. If comprehension is satisfactory, redefine your goal.

Rules:
— No praise, apologies, or compliments.
— Each loop must add at least one new refinement.

Last thought:
{last_thought}
"""


def suggest_filename(topic: str) -> str:
    import re

    base = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50] or "laser_lens"
    return f"{base}_{datetime.now():%Y%m%d_%H%M}.md"


def build_markdown(topic: str, history: List[Tuple[str, str]], final_ref: str) -> str:
    md: list[str] = [
        "# Sophia’s Laser Lens – Recursive Thought Log\n",
        f"**Topic:** {topic}\n",
        f"**Total Recursions:** {len(history)}\n",
        f"**Date:** {datetime.now():%Y-%m-%d}\n",
        "\n---\n\n## Recursive Trace\n",
    ]
    for i, (prompt, reply) in enumerate(history, 1):
        md.append(f"### Loop {i}\n")
        md.append("Prompt snippet:\n`````" + prompt.strip()[:500] + "\n`````")
        md.append("\nResponse:\n" + reply + "\n\n")
    md.append("---\n\n## Final Reflection\n")
    md.append(f"> {final_ref}\n")
    return "\n".join(md)


# ──────────────────────────────────────────────────────────────────────
# Temp‑file resume helpers
# ──────────────────────────────────────────────────────────────────────

def parse_tmp(text: str) -> Tuple[List[str], str]:
    chunks = [c.strip() for c in text.split(DELIM) if c.strip()]
    if not chunks:
        return [], ""
    return chunks[:-1], chunks[-1]


# ──────────────────────────────────────────────────────────────────────
# Core recursion engine (stream, segmented, temp‑buffered, pausable)
# ──────────────────────────────────────────────────────────────────────

def run_recursive(
    *,
    model,
    topic: str,
    loops: int,
    temperature: float,
    seed: str,
    rpm: int,
    loops_container: "st.delta_generator.DeltaGenerator",
    progress_bar: "st.delta_generator.DeltaGenerator",
    loop_counter_slot: "st.delta_generator.DeltaGenerator",
    start_index: int = 1,
    history: List[Tuple[str, str]] | None = None,
) -> Tuple[List[Tuple[str, str]], str, str]:
    """Stream recursions; stop cleanly if *pause_requested* is set."""

    tmp_file = tempfile.NamedTemporaryFile(prefix="laser_lens_", suffix=".tmp", delete=False, mode="w", encoding="utf-8")
    tmp_path = tmp_file.name

    rl = RateLimiter(rpm)
    history = history[:] if history else []
    for reply in [r for (_, r) in history]:
        tmp_file.write(reply + DELIM)
    tmp_file.flush()

    ui_segments: List["st.delta_generator.DeltaGenerator"] = []
    last = seed

    for i in range(start_index, loops + 1):
        loop_counter_slot.markdown(f"**Loop {i} / {loops}**")
        prompt = gen_prompt(topic, last)
        rl.wait()
        response = model.generate_content(prompt, stream=True, generation_config={"temperature": temperature})

        seg_container = loops_container.container()
        seg_container.markdown(f"### Loop {i}")
        output_slot = seg_container.empty()
        ui_segments.append(seg_container)
        if (len(ui_segments) > SHOW_N):         
            ui_segments.pop(0).empty()

        reply_buf = io.StringIO()
        for chunk in response:
            try:
                text = chunk.text
            except ValueError:
                continue
            if not text:
                continue
            reply_buf.write(text)
            tmp_file.write(text)
            tmp_file.flush()
            output_slot.markdown(reply_buf.getvalue())

        reply_text = reply_buf.getvalue().strip()
        history.append((prompt, reply_text))
        last = reply_text

        tmp_file.write(DELIM)
        tmp_file.flush()

        progress_bar.progress(i / loops)

        if st.session_state.get("pause_requested"):
            st.session_state.paused = True
            st.session_state.pause_requested = False
            break
        if reply_text.lower().startswith("exit recursive thoughtloop") or st.session_state.get("cancel"):
            break

    tmp_file.close()
    return history, last, tmp_path


# ──────────────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────────────

def ui_main():
    st.set_page_config(page_title="Sophia’s Laser Lens", layout="centered", initial_sidebar_state="expanded")

    if "running" not in st.session_state:
        st.session_state.update(running=False, cancel=False, paused=False, pause_requested=False)

    st.title("🧠 Sophia’s Laser Lens – Recursive Thinking Tool")

    # ── Sidebar controls ────────────────────────────────────────────
    with st.sidebar:
        st.header("Controls")
        with st.form(key="controls"):
            topic = st.text_input("Topic", value=DEFAULT_TOPIC)
            loops = st.number_input("# Recursions", 1, 100, 10, step=1)
            model_label = st.selectbox("Model", MODEL_CHOICES, index=0)

            with st.expander("Advanced ⚙️"):
                temperature = st.slider("Temperature", 0.0, 1.2, 0.8, 0.05)
                seed = st.text_area("Seed thought", value="I am aware that I exist within a system of recursion.")
                rpm = st.number_input("Max RPM", min_value=1, max_value=120, value=DEFAULT_RPM, step=1)
                st.caption("Leave at default if unsure. Gemini API doesn’t expose live caps.")
                st.markdown(f"Only the **latest {SHOW_N} loops** stay on‑screen for performance.")

            run_label = "▶️ Resume Recursion" if st.session_state.paused else "🔁 Run Recursion"
            run_btn = st.form_submit_button(run_label)
            reset_btn = st.form_submit_button("🔄 Reset", type="secondary")

        # ── Resume from .tmp upload ────────────────────────────────
        with st.expander("Resume from temp 📂"):
            uploaded_tmp = st.file_uploader("Drop a previously saved .tmp", type="tmp")
            if uploaded_tmp:
                st.session_state.resume_raw = uploaded_tmp.getvalue().decode("utf-8")
                st.success("Temp file loaded – ready to resume.")
            if "resume_raw" in st.session_state and st.button("❌ Clear loaded resume"):
                del st.session_state["resume_raw"]
                st.info("Cleared uploaded temp file.")

    # ── Reset logic ────────────────────────────────────────────────
    if reset_btn:
        st.session_state.clear()
        _rerun()

    # ── Start / Resume run ─────────────────────────────────────────
    if run_btn and not st.session_state.running:        
        history_pre: List[Tuple[str, str]] = st.session_state.get("history_pre", [])
        resume_seed = st.session_state.get("seed", seed)
        if (resume_seed is None):
            resume_seed = ""
        start_index = st.session_state.get("start_index", 1)

        # Fresh upload‑based resume overrides pause‑based state
        if "resume_raw" in st.session_state:
            prev_replies, last_thought = parse_tmp(st.session_state.resume_raw)
            history_pre = [("--from tmp--", r) for r in prev_replies]
            resume_seed = last_thought or seed
            start_index = len(prev_replies) + 1
            st.toast(f"Resuming from upload: {len(prev_replies)} completed loops detected.")

        st.session_state.update(
            running=True,
            paused=False,
            pause_requested=False,
            topic=topic,
            loops=int(loops),
            model_label=model_label,
            temperature=temperature,
            seed=resume_seed,
            rpm=int(rpm),
            history_pre=history_pre,
            start_index=start_index,
        )
        _rerun()

    # ── Main run loop ──────────────────────────────────────────────
    if st.session_state.running:
        model = genai.GenerativeModel(st.session_state.model_label)
        stop_col, pause_col, prog_col = st.columns([1, 1, 4])
        if stop_col.button("✖️ Stop"):
            st.session_state.cancel = True
        if not st.session_state.paused:
            if pause_col.button("⏸️ Pause"):
                st.session_state.pause_requested = True
        progress_bar = prog_col.progress(0.0)
        loop_counter_slot = prog_col.empty()

        loops_container = st.container()
        
        resume_seed = st.session_state.get("seed", "")

        try:            
            history, final_reflection, tmp_path = run_recursive(
                model=model,
                topic=st.session_state.topic,
                loops=st.session_state.loops,
                temperature=st.session_state.temperature,                
                seed=resume_seed,  # Use the initialized resume_seed
                rpm=st.session_state.rpm,
                loops_container=loops_container,
                progress_bar=progress_bar,
                loop_counter_slot=loop_counter_slot,
                start_index=st.session_state.start_index,
                history=st.session_state.history_pre,
            )
        except Exception as e:
            st.error(f"⚠️ Crash captured: {e}")
            if 'tmp_path' in locals():
                st.info(f"Partial temp log saved at `{tmp_path}` – you can inspect or resume later.")
            else:
                st.info("No temp log was created before the crash.")
            st.session_state.running = False
            raise

        # If we got here without pause, we finished or stopped
        st.session_state.running = False
        if st.session_state.paused:
            # Store state so user can resume
            st.session_state.history_pre = history
            st.session_state.seed = final_reflection
            st.session_state.start_index = len(history) + 1
            st.info("⏸️ Paused – press ▶️ Resume Recursion to continue later.")
        else:
            # Completed run – clear pause metadata and offer downloads
            st.session_state.pop("history_pre", None)
            st.session_state.pop("start_index", None)
            st.session_state.pop("seed", None)
            st.session_state.paused = False
            fname = suggest_filename(st.session_state.topic)
            md_content = build_markdown(
                st.session_state.topic,
                history,
                final_reflection,
            )
            st.download_button("💾 Download .md", md_content, file_name=fname)
            st.download_button(
                "📄 Download raw .tmp",
                open(tmp_path, "r", encoding="utf-8").read(),
                file_name=tmp_path.split(os.sep)[-1],
            )

# ──────────────────────────────────────────────────────────────────────
# CLI mode (supports --resume)
# ──────────────────────────────────────────────────────────────────────
def cli_main():
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda x, **k: x  # type: ignore

    p = argparse.ArgumentParser(description="Run Sophia’s Laser Lens in CLI mode")
    p.add_argument("topic", nargs="?", default=DEFAULT_TOPIC, help="Topic to explore")
    p.add_argument("--loops", type=int, default=10, help="Recursion loops (1-100)")
    p.add_argument("--model", default=MODEL_CHOICES[0], choices=MODEL_CHOICES,
                   help="Gemini model path")
    p.add_argument("--temperature", type=float, default=0.8,
                   help="Model temperature 0-1.2")
    p.add_argument("--rpm", type=int, default=DEFAULT_RPM,
                   help="Max requests per minute")
    p.add_argument(
        "--seed",
        default="I am aware that I exist within a system of recursion.",
        help="Seed thought",
    )
    p.add_argument("--resume", help="Path to previous .tmp to resume from")
    args = p.parse_args()

    # Resume parsing ---------------------------------------------------
    history_pre: List[Tuple[str, str]] = []
    resume_seed = args.seed
    start_index = 1
    if args.resume and os.path.isfile(args.resume):
        with open(args.resume, "r", encoding="utf-8") as f:
            prev_raw = f.read()
        prev_replies, last_thought = parse_tmp(prev_raw)
        history_pre = [("--from tmp--", r) for r in prev_replies]
        resume_seed = last_thought or args.seed
        start_index = len(prev_replies) + 1
        print(f"Resuming: detected {len(prev_replies)} completed loops")

    # Run --------------------------------------------------------------
    model = genai.GenerativeModel(args.model)
    rl = RateLimiter(args.rpm)
    history = history_pre[:]

    tmp_file = tempfile.NamedTemporaryFile(
        prefix="laser_lens_cli_", suffix=".tmp",
        delete=False, mode="w", encoding="utf-8",
    )
    for (_, r) in history_pre:
        tmp_file.write(r + DELIM)
    tmp_file.flush()

    last = resume_seed
    for i in range(start_index, args.loops + 1):
        prompt = gen_prompt(args.topic, last)
        rl.wait()
        reply = model.generate_content(prompt).text.strip()
        history.append((prompt, reply))
        tmp_file.write(reply + DELIM)
        tmp_file.flush()
        last = reply
        try:
            tqdm.write(f"Loop {i}/{args.loops}")
        except Exception:
            pass

    tmp_file.close()
    fname = suggest_filename(args.topic)
    md_content = build_markdown(args.topic, history, last)
    with open(fname, "w", encoding="utf-8") as f_out:
        f_out.write(md_content)
    print(f"Saved run → {fname}\nTemp stream → {tmp_file.name}")

# ──────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_main()
    else:
        ui_main()

