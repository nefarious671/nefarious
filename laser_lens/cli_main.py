# cli_main.py

import argparse
import os
import re
import sys

from config import Config
from error_logger import ErrorLogger
from command_executor import CommandExecutor
from command_registration import register_core_commands
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

def get_available_models(api_key: str | None = None) -> list[str]:
    """Return available Gemini models using *api_key* if provided."""
    try:
        import google.generativeai as genai_list
        if api_key is None:
            from dotenv import load_dotenv

            load_dotenv()  # This loads GOOGLE_API_KEY from .env if present
            api_key = os.getenv("GOOGLE_API_KEY")
        genai_list.configure(api_key=api_key)

        # Filter models to those that support generateContent and have "gemini" in their name
        models_available = [
            m.name
            for m in genai_list.list_models()
            if "generateContent" in (m.supported_generation_methods or [])
        ]
        # Keep only those with "gemini" in the name, sort descending so latest appear first
        models_available = sorted(
            [m for m in models_available if "gemini" in m.lower()],
            reverse=True
        )
        if not models_available:
            models_available = ["models/gemini-2.0-pro"]
    except Exception:
        models_available = ["models/gemini-2.0-pro"]

    return models_available


def main():
    # First, fetch list of available models
    models_available = get_available_models(os.getenv("GOOGLE_API_KEY"))

    # Load the last‐used model if present; else default to first
    saved_model = load_pref_model(models_available)
    default_index = models_available.index(saved_model) if saved_model in models_available else 0

    parser = argparse.ArgumentParser(description="Run laser_lens recursive agent.")
    parser.add_argument("--topic", type=str, required=True, help="Topic to analyze.")
    parser.add_argument(
        "--loops",
        type=int,
        default=Config().default_loops,
        help="Number of recursive loops."
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=models_available,
        default=models_available[default_index],
        help="Model name (choose from available Gemini models)."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=Config().default_temperature,
        help="Sampling temperature."
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed (optional).")
    parser.add_argument(
        "--rpm",
        type=int,
        default=Config().default_rpm,
        help="Requests per minute (rate limiting)."
    )
    parser.add_argument("--thinking-mode",
        action="store_true",
        help="Enable chat-only reasoning mode without OS instructions.")
    parser.add_argument(
        "--resume",
        type=str,
        help="Path to existing .tmp file to resume from."
    )
    parser.add_argument(
        "--resume-current-loop",
        type=int,
        help="If resuming, what loop index to start from (1-based)."
    )

    args = parser.parse_args()

    # Save the chosen model so next time it's the default
    save_pref_model(args.model)

    # Initialize modules
    config = Config()
    logger = ErrorLogger(config)
    ce = CommandExecutor(logger)
    register_core_commands(ce)
    try:
        from command_registration import register_plugin_commands
        register_plugin_commands(ce)
    except Exception:
        pass
    om = OutputManager(config, logger)
    cm = ContextManager(config, logger, om)
    as_state = AgentState(config, logger)

    # Handle resume from .tmp if provided
    if args.resume:
        try:
            with open(args.resume, "rb") as f:
                content = f.read()
            cm.upload_context(args.resume, content)
            if args.resume_current_loop:
                as_state.update_state("current_loop", args.resume_current_loop)
        except Exception as e:
            logger.log("WARNING", f"Could not load resume file: {args.resume}", e)

    # Instantiate RecursiveAgent with the real Gemini client
    try:
        agent = RecursiveAgent(
            config=config,
            error_logger=logger,
            command_executor=ce,
            context_manager=cm,
            output_manager=om,
            agent_state=as_state,
            model_name=args.model,
            topic=args.topic,
            loops=args.loops,
            temperature=args.temperature,
            seed=args.seed,
            rpm=args.rpm,
            api_key=os.getenv("GOOGLE_API_KEY"),
            thinking_mode=args.thinking_mode,
        )
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to instantiate agent: {e}\n")
        sys.exit(1)

    # Stream the output with basic command rendering
    cmd_pattern = re.compile(r"\[\[COMMAND:\s*(?P<name>\w+)(?P<args>.*?)\]\]", re.DOTALL)
    buffer = ""
    try:
        for event_type, loop_idx, total_loops, payload in agent.run():
            if event_type == "chunk":
                buffer += payload
                sys.stdout.write(payload)
                sys.stdout.flush()
            elif event_type == "loop_end":
                full_text = buffer
                buffer = ""
                results = as_state.get_state("command_results") or []
                pos = 0
                r_idx = 0
                for m in cmd_pattern.finditer(full_text):
                    pre = full_text[pos:m.start()]
                    if pre.strip():
                        sys.stdout.write(pre)
                    cmd_name = m.group("name")
                    arg_str = m.group("args").strip()
                    result = results[r_idx][1] if r_idx < len(results) else ""
                    sys.stdout.write(f"\n\u25B6 {cmd_name} {arg_str}\n")
                    sys.stdout.write(f"{result}\n")
                    pos = m.end()
                    r_idx += 1
                if pos < len(full_text):
                    sys.stdout.write(full_text[pos:])
                sys.stdout.write(
                    f"\n\n--- End of loop {loop_idx} of {total_loops} ---\n\n"
                )
            elif event_type == "error":
                message, exc = payload
                sys.stderr.write(f"[ERROR] {message}\n")
                sys.exit(1)
    except KeyboardInterrupt:
        # User interrupted; request cancel and save state
        agent.request_cancel()
        sys.stderr.write("\n[Interrupted by user; saving state...]\n")
        as_state.save_state()
        sys.exit(1)

    # After completion, build final Markdown and save
    history = as_state.get_state("history") or []
    md_content = build_markdown(history, args.topic)
    suggested_name = suggest_filename(args.topic)
    try:
        saved_path = om.save_output(suggested_name, md_content)
        print(f"\nFinal Markdown saved to: {saved_path}")
        session_meta = {
            "topic": args.topic,
            "loops": args.loops,
            "model": args.model,
            "temperature": args.temperature,
            "seed": args.seed,
            "rpm": args.rpm,
            "output_file": saved_path,
        }
        om.save_session_metadata(session_meta)
    except Exception:
        sys.stderr.write("Failed to save final Markdown.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
