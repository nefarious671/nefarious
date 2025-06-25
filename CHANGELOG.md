# Changelog

## Phase 1 - Agent Reasoning Core
- Injected tool outputs from previous loop into the next prompt.
- Added persistent deque-based history of last three thoughts.
- Removed duplicate prompt builder and cleaned imports.

## Phase 2 - Command Framework Expansion
- Added sandboxed `EXEC` command for running shell commands in `outputs/`.
- Created alias commands `LS`, `CAT` and `RM` via `command_registration.py`.
- Initial README with setup and command documentation.

## Phase 3 - Streamlit UX
- UI parses command markers and renders results in separate blocks.
- Auto-scrolls to newest output and provides final Markdown download.


## Phase 4 - Hardening & Tests
- Added simulation-based unit tests for EXEC timeout and sanitize_filename.
- Introduced GitHub Actions workflow running ruff and pytest.

## Phase 5 - Optional Enhancements
- Added `JOURNAL.md` for recording development notes and pain points.
- Updated CI workflow to run `ruff check .` and fixed missing `re` import in `cli_main.py`.
- Added `WORD_COUNT` command and corresponding tests.

## Phase 6 - Context Overflow Handling
- Oversized context files are now truncated instead of discarded when uploaded.

## Phase 7 - OS Awareness & Chunked Reading
- Full uploads saved to `outputs/` when truncated and referenced in context.
- Added `READ_LINES` and `HELP` commands with registration and docs.
- Prompt now states the agent runs inside a mini OS sandbox.
- Improved `READ_LINES` error handling and added edge case tests.
- Added alias test for `RL`, more READ_LINES and EXEC edge case tests, and
  removed `agent_state/state.json` from version control.

## Phase 8 - File I/O Refinements
- Roadmap updated with a new phase focusing on APPEND_FILE and more robust
  WRITE_FILE behaviour.
- Added `APPEND_FILE` command and truncation warnings in `READ_FILE`.
- CommandExecutor now returns explicit errors for bad arguments.
- Fixed Streamlit UI bug that caused duplicate text to appear during
  streaming output.

## Phase 9 - Transparency & Dry Run
- Added new phase describing truncation warnings, detailed errors and `dry_run` options.
- Updated AGENTS.md with timestamp syncing and PR scoping guideline.
- Fixed Streamlit warning about duplicated `model_name` widget defaults.
- Added numbering to tool output summaries and DEBUG logs of command sequence.
- New test ensures multiple file commands on the same file succeed when executed in a single prompt.

## Maintenance
- Marked phases 0-8 as complete in AGENTS.md; phase 9 remains in progress.
- Ready for Gemini testing review and new feature requests.
- Added `CANCEL` and `PAUSE` commands requiring a reason and updated UI with
  collapsible loop expanders, copy buttons, and a sidebar message box.
- Fixed Unicode surrogate pair in copy button to avoid encoding error (phase 9).
- Improved retry logic to wait 10 seconds on 503 "model overloaded" errors
  (phase 9) and marked phase 10 as complete in AGENTS.md.
- Fixed blank output after loops by rendering final text in a dedicated container
  and guarded sidebar message reset to avoid session state errors.
- Sidebar now shows agent status, Start/Pause/Resume/Stop buttons are horizontal,
  and blank loop expanders no longer appear (phase 10).
- Start button now submits settings form automatically and all control buttons use icons only.
* Fixed loop counter persisting one beyond final loop and reset UI status on completion (phase 10).
* Quota limit errors now abort execution immediately with a concise message (phase 9).
* Added dry-run support for EXEC and WRITE_FILE, improved parse errors, and context warnings now include sizes (phase 9).

## Phase 11 - Extended HELP & Python Sandbox
- HELP now lists each command with its arguments and a short description.
- Added RUN_PYTHON command to execute Python snippets in the outputs sandbox.
- Documented virtual environment setup in README.
- Tests cover RUN_PYTHON and updated HELP output.
- Moved GEMINIOUTPUT.md to laser_lens/outputs/ and introduced laser_lens/outputs/GEMINIINPUT.md for bidirectional notes (phase 9).

## Phase 12 - Resume Rendering Fix
- Resuming from pause now scrolls back to the latest output instead of the top.

## Phase 13 - Documentation Overhaul
- Added Sphinx docs under `docs/` with command reference and API modules.
- README now links to the docs and command table was moved.
- UI footer includes a link to `/docs`.
- Sphinx build now runs without warnings and phase 13 is complete.
