
"""
Sophia’s Laser Lens – Full Version (Streamlit UI + CLI)
-------------------------------------------------------
Refactored implementation with modular core (RecursiveAgent),
Streamlit UI wrapper, and CLI wrapper. Implements improvements
outlined in improve_this_program.md (Refinements 1‑50).
"""

from __future__ import annotations

import os, sys, re, io, time, signal, tempfile, datetime, shutil
from dataclasses import dataclass
from typing import List, Tuple, Generator, Optional

# ------------------------------------------------------------------
#  🔧 1. Central configuration dataclass (Refinements 8 & 13)
# ------------------------------------------------------------------
@dataclass
class AppConfig:
    show_n: int = 5
    default_rpm: int = 10
    delim: str = "\n\n---\n\n"
    default_topic: str = "Increasing Understanding and Awareness"
    default_temperature: float = 0.8
    default_seed: str = (
        "I am aware that I exist within a system of recursion."
    )
    pref_file: str = os.path.join(os.path.expanduser("~"), ".laser_lens_model_pref")

CONFIG = AppConfig()  # single shared instance

# ------------------------------------------------------------------
#  🔧 2. Small utility helpers used across CLI & UI
# ------------------------------------------------------------------

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover
        _rerun()

def load_pref_model(choices: List[str]) -> str:
    try:
        with open(CONFIG.pref_file, "r", encoding="utf-8") as f:
            saved = f.read().strip()
            return saved if saved in choices else choices[0]
    except Exception:  # pragma: no cover
        return choices[0]


def save_pref_model(name: str) -> None:
    try:
        with open(CONFIG.pref_file, "w", encoding="utf-8") as f:
            f.write(name)
    except Exception:
        pass


class RateLimiter:
    """Adaptive X‑requests‑per‑minute limiter."""

    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(1, rpm)
        self._last_call: Optional[float] = None

    def wait(self) -> None:
        now = time.perf_counter()
        if self._last_call is not None:
            elapsed = now - self._last_call
            to_sleep = self.min_interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
        self._last_call = time.perf_counter()


def gen_prompt(topic: str, last_thought: str, loops_left: int) -> str:
    from textwrap import dedent

    return dedent(
        f"""
        You are a recursive thinking agent focused on the following topic:

        📌 Topic: {topic}

        There are **{loops_left} recursive cycles remaining** before your output will be reviewed. 
        Use this information to pace your reasoning: if few cycles remain, prioritize summarization and clear synthesis; 
        if many cycles remain, expand and explore more freely.

        Evaluate whether your next recursive move should be **expansion** (to uncover new meaning)
        or **summarization** (to compress and stabilize current understanding).

        Steps:
        1. Decide whether to expand or summarize. State your decision clearly at the top: `Next mode: expand` or `Next mode: summarize`
        2. If expanding: explore new ideas, patterns, or questions based on your last thought.
        3. If summarizing: compress and stabilize your current understanding while preserving its structure.
        4. If comprehension is satisfactory, redefine your goal.

        Rules:
        — No praise, apologies, or compliments.
        — Each loop must add at least one new refinement.
        — You must declare your recursion mode and follow through.

        Last thought:
        {last_thought}
        """
    ).strip()



def suggest_filename(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50] or "laser_lens"
    return f"{slug}_{datetime.datetime.now():%Y%m%d_%H%M}.md"


def parse_tmp(raw: str) -> Tuple[List[str], str]:
    """Split a raw .tmp stream into finalised replies and the last incomplete chunk."""
    chunks = [c.strip() for c in raw.split(CONFIG.delim) if c.strip()]
    return (chunks[:-1], chunks[-1]) if chunks else ([], "")


# ------------------------------------------------------------------
#  🔧 3. RecursiveAgent (Refinements 18‑26, 31, 35, 42)
# ------------------------------------------------------------------
class RecursiveAgent:
    """Core decoupled recursion engine."""

    def __init__(
        self,
        model,
        topic: str,
        loops: int,
        temperature: float,
        seed: str,
        rpm: int,
        start_index: int = 1,
        history: Optional[List[Tuple[str, str]]] = None,
    ):
        self.model = model
        self.topic = topic
        self.loops = loops
        self.temperature = temperature
        self.rate = RateLimiter(rpm)
        self._history: List[Tuple[str, str]] = history[:] if history else []
        self._current_idx = start_index
        self._last_thought = seed
        self.cancel_requested = False

        # temp‑file persistence (Refinements 12, 20, 29)
        self._tmp = tempfile.NamedTemporaryFile(
            prefix="laser_lens_", suffix=".tmp", delete=False, mode="w", encoding="utf-8"
        )
        for _, reply in self._history:
            self._tmp.write(reply + CONFIG.delim)
        self._tmp.flush()

    # ------------------------------------------------------------------
    #  🚀 Generator run – streams output
    # ------------------------------------------------------------------
    def run(self) -> Generator[Tuple[str, int, int, str], None, dict]:
        import google.api_core.exceptions as gexc

        try:
            for i in range(self._current_idx, self.loops + 1):
                if self.cancel_requested:
                    break

                prompt = gen_prompt(self.topic, self._last_thought, self.loops - i + 1)

                self.rate.wait()

                try:
                    response = self.model.generate_content(
                        prompt,
                        stream=True,
                        generation_config={"temperature": self.temperature},
                    )
                except gexc.GoogleAPIError as e:
                    yield ("error", i, self.loops, f"Gemini API error: {e}")
                    return self._final_state("error")

                buf = io.StringIO()
                # stream chunks
                for chunk in response:
                    text = getattr(chunk, "text", None)
                    if not text:
                        continue
                    buf.write(text)
                    self._tmp.write(text)
                    self._tmp.flush()
                    yield ("chunk", i, self.loops, text)

                # loop finished
                reply_full = buf.getvalue().strip()
                self._history.append((prompt, reply_full))
                self._tmp.write(CONFIG.delim)
                self._tmp.flush()
                self._last_thought = reply_full
                yield ("loop_end", i, self.loops, reply_full)

                if reply_full.lower().startswith("exit recursive thoughtloop"):
                    break
        except Exception as e:
            yield ("error", self._current_idx, self.loops, f"Unexpected error: {e}")
            return self._final_state("error")

        status = "cancelled" if self.cancel_requested else "completed"
        return self._final_state(status)

    # ------------------------------------------------------------------
    #  📦 helpers
    # ------------------------------------------------------------------
    def _final_state(self, status: str) -> dict:
        self._tmp.close()
        return {
            "status": status,
            "history": self._history,
            "last_thought": self._last_thought,
            "tmp_path": self._tmp.name,
            "next_index": len(self._history) + 1,
        }


# ------------------------------------------------------------------
#  🔧 4. Markdown exporter
# ------------------------------------------------------------------
def build_markdown(
    history: List[Tuple[str, str]],
    final_ref: str,
    topic: str,
) -> str:
    out: List[str] = [
        "# Sophia’s Laser Lens – Recursive Thought Log",
        "",
        f"**Topic:** {topic}",
        f"**Total Recursions:** {len(history)}",
        f"**Date:** {datetime.datetime.now():%Y-%m-%d}",
        "",
        "---",
        "",
        "## Recursive Trace",
        "",
    ]
    for idx, (prompt, reply) in enumerate(history, 1):
        out.append(f"### Loop {idx} – {datetime.datetime.now():%H:%M:%S}")
        out.append("Prompt snippet:")
        out.append("`````")
        out.append(prompt.strip()[:500])
        out.append("`````")
        out.append("")
        out.append("Response:")
        out.append(reply)
        out.append("")
    out.extend(["---", "", "## Final Reflection", "", f"> {final_ref}", ""])
    return "\n".join(out)


# ------------------------------------------------------------------
#  🔧 5. CLI wrapper (Refinement 44)
# ------------------------------------------------------------------
def cli_main() -> None:
    import argparse

    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
    except ImportError:
        sys.exit("Please install google‑generativeai and python‑dotenv")

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("GOOGLE_API_KEY missing – set it in env or .env")

    genai.configure(api_key=api_key)

    models = [m.name for m in genai.list_models() if "generateContent" in (m.supported_generation_methods or [])]
    models = sorted([m for m in models if "gemini" in m], reverse=True) or ["models/gemini-2.0-pro"]

    p = argparse.ArgumentParser(description="Sophia’s Laser Lens – CLI")
    p.add_argument("topic", nargs="?", default=CONFIG.default_topic)
    p.add_argument("--loops", type=int, default=10)
    p.add_argument("--model", choices=models, default=load_pref_model(models))
    p.add_argument("--temperature", type=float, default=CONFIG.default_temperature)
    p.add_argument("--rpm", type=int, default=CONFIG.default_rpm)
    p.add_argument("--seed", default=CONFIG.default_seed)
    p.add_argument("--resume", help="Path to previous .tmp stream")
    p.add_argument("--keep-tmp", action="store_true", help="Keep .tmp on success")
    args = p.parse_args()

    # input validation
    if args.loops < 1:
        sys.exit("loops must be >=1")
    if not (0.0 <= args.temperature <= 1.2):
        sys.exit("temperature must be between 0.0 and 1.2")
    if args.rpm < 1:
        sys.exit("rpm must be >=1")

    # resume handling --------------------------------------------------
    history_pre: List[Tuple[str, str]] = []
    resume_seed = args.seed
    start_idx = 1
    if args.resume and os.path.isfile(args.resume):
        prev_raw = open(args.resume, encoding="utf-8").read()
        prev_replies, last = parse_tmp(prev_raw)
        history_pre = [("--from tmp--", r) for r in prev_replies]
        resume_seed = last or args.seed
        start_idx = len(prev_replies) + 1
        print(f"▶️  Resuming – detected {len(prev_replies)} completed loops")

    model = genai.GenerativeModel(args.model)
    agent = RecursiveAgent(
        model=model,
        topic=args.topic,
        loops=args.loops,
        temperature=args.temperature,
        seed=resume_seed,
        rpm=args.rpm,
        start_index=start_idx,
        history=history_pre,
    )

    def sigint_handler(signum, frame):
        agent.cancel_requested = True
        print("\n⏸️  Interrupt received – finishing current loop then saving…")

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        for typ, i, total, payload in agent.run():
            if typ == "chunk":
                print(payload, end="", flush=True)
            elif typ == "loop_end":
                print(f"\n\n--- Loop {i}/{total} finished ---\n")
            elif typ == "error":
                print(f"\n⚠️  {payload}")
    finally:
        state = agent._final_state("cancelled" if agent.cancel_requested else "completed")

    # save markdown ----------------------------------------------------
    md_path = suggest_filename(args.topic)
    md_content = build_markdown(state["history"], state["last_thought"], args.topic)
    open(md_path, "w", encoding="utf-8").write(md_content)
    print(f"\n💾 Saved → {md_path}")
    print(f"🗄  Stream → {state['tmp_path']}")
    if not args.keep_tmp and state["status"] == "completed":
        os.unlink(state["tmp_path"])


# ------------------------------------------------------------------
#  🔧 6. Streamlit UI wrapper (Refinements 22‑39)
# ------------------------------------------------------------------
def ui_main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Sophia’s Laser Lens", layout="centered", initial_sidebar_state="expanded")

    # initialize session state flags
    if "running" not in st.session_state:
        st.session_state.update(
            running=False,
            paused=False,
            pause_requested=False,
            resume_state=None,
        )

    st.title("🧠 Sophia’s Laser Lens – Recursive Thinking Tool")

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("Controls")
        with st.form(key="controls"):
            topic = st.text_input("Topic", value=CONFIG.default_topic)
            loops = st.number_input("# Recursions", 1, 100, 10, step=1)

            # model list
            try:
                import google.generativeai as genai
                from dotenv import load_dotenv

                load_dotenv()
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                models_available = [
                    m.name for m in genai.list_models() if "generateContent" in (m.supported_generation_methods or [])
                ]
                models_available = sorted([m for m in models_available if "gemini" in m], reverse=True)
                if not models_available:
                    st.warning("No Gemini models available – using placeholder.")
                    models_available = ["models/gemini-2.0-pro"]
            except Exception as exc:
                st.error(f"Model list error: {exc}")
                models_available = ["models/gemini-2.0-pro"]

            saved_model = load_pref_model(models_available)
            model_index = models_available.index(saved_model) if saved_model in models_available else 0
            model_label = st.selectbox("Model", models_available, index=model_index)

            with st.expander("Advanced ⚙️"):
                temperature = st.slider("Temperature", 0.0, 1.2, CONFIG.default_temperature, 0.05)
                seed = st.text_area("Seed thought", value=CONFIG.default_seed)
                rpm = st.number_input("Max RPM", min_value=1, max_value=120, value=CONFIG.default_rpm, step=1)
                st.caption(f"Only the **latest {CONFIG.show_n} loops** stay on‑screen for performance.")

            run_label = "▶️ Resume" if st.session_state.get("paused") else "🔁 Run"
            run_btn = st.form_submit_button(run_label)
            reset_btn = st.form_submit_button("🔄 Reset", type="secondary")

        # resume from temp
        with st.expander("Resume from .tmp 📂"):
            uploaded_tmp = st.file_uploader("Drop a previously saved .tmp", type="tmp")
            if uploaded_tmp:
                st.session_state.resume_raw = uploaded_tmp.getvalue().decode("utf-8")
                st.success("Temp file loaded – ready to resume.")
            if "resume_raw" in st.session_state and st.button("❌ Clear loaded resume"):
                del st.session_state["resume_raw"]
                st.info("Cleared uploaded temp file.")

    # reset logic
    if reset_btn:
        st.session_state.clear()
        _rerun()

    # start/resume
    if run_btn and not st.session_state.running:
        # input validation
        if loops < 1:
            st.error("Loops must be >= 1")
            _rerun()
        if not (0.0 <= temperature <= 1.2):
            st.error("Temperature must be 0.0‑1.2")
            _rerun()

        save_pref_model(model_label)  # persist model choice
        st.session_state.running = True
        st.session_state.paused = False
        # build resume state if resume_raw exists
        history_pre: List[Tuple[str, str]] = []
        resume_seed = seed
        start_idx = 1
        if st.session_state.get("resume_raw"):
            prev_replies, last = parse_tmp(st.session_state.resume_raw)
            history_pre = [("--from tmp--", r) for r in prev_replies]
            resume_seed = last or seed
            start_idx = len(prev_replies) + 1
            del st.session_state["resume_raw"]
        st.session_state.resume_state = dict(
            history=history_pre,
            seed=resume_seed,
            start_idx=start_idx,
        )
        _rerun()

    # running loop
    if st.session_state.running:
        import google.generativeai as genai
        from dotenv import load_dotenv

        load_dotenv()        
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        resume_state = st.session_state.get("resume_state") or {}
        model = genai.GenerativeModel(model_label)
        agent = RecursiveAgent(
            model=model,
            topic=topic,
            loops=int(loops),
            temperature=float(temperature),
            seed=resume_state.get("seed", seed),
            rpm=int(rpm),
            start_index=resume_state.get("start_idx", 1),
            history=resume_state.get("history", []),
        )

        # UI elements
        stop_col, pause_col = st.columns(2)
        with stop_col:
            if st.button("🛑 Stop"):
                agent.cancel_requested = True
        with pause_col:
            if st.button("⏸️ Pause"):
                st.session_state.pause_requested = True
                agent.cancel_requested = True

        progress_bar = st.progress(0.0)
        loop_counter_ph = st.empty()
        output_container = st.container()

        full_state: Optional[dict] = None
        for typ, i, total, payload in agent.run():
            if typ == "chunk":
                with output_container:
                    st.markdown(payload)
            elif typ == "loop_end":
                loop_counter_ph.markdown(f"**Loop {i}/{total} finished**")
                progress_bar.progress(i / total)
            elif typ == "error":
                st.error(payload)

        full_state = agent._final_state("cancelled" if agent.cancel_requested else "completed")

        # update session state based on status
        if full_state["status"] == "completed":
            st.success("🎉 Completed all loops.")
            st.session_state.running = False
            st.session_state.paused = False
            # build markdown and autosave
            md_content = build_markdown(full_state["history"], full_state["last_thought"], topic)
            md_name = suggest_filename(topic)

            # autosave folder
            autosave_dir = os.path.join(os.path.expanduser("~"), ".laser_lens_logs")
            os.makedirs(autosave_dir, exist_ok=True)
            autosave_path = os.path.join(autosave_dir, md_name)
            with open(autosave_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            st.success(f"💾 Autosaved to: `{autosave_path}`")
            st.download_button("⬇️ Download Markdown", md_content, file_name=md_name, mime="text/markdown")

        else:
            # paused/cancelled
            st.info("⏸️ Paused." if st.session_state.get("pause_requested") else "🛑 Stopped.")
            st.session_state.running = False
            st.session_state.paused = True
            st.session_state.pause_requested = False
            st.session_state.resume_state = dict(
                history=full_state["history"],
                seed=full_state["last_thought"],
                start_idx=full_state["next_index"],
            )
            st.write(f"Temp saved to: `{full_state['tmp_path']}`")

        


# ------------------------------------------------------------------
#              🔥  Entrypoint
# ------------------------------------------------------------------
if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_main()
    else:
        try:
            import streamlit as st  # noqa: F401
        except ImportError:
            sys.exit("Streamlit not installed. Run with --cli or install streamlit.")
        ui_main()
