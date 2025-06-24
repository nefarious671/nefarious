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
- Fixed Streamlit UI bug that caused duplicate text to appear during
  streaming output.

## Phase 9 - Transparency & Dry Run
- Added new phase describing truncation warnings, detailed errors and `dry_run` options.
- Updated AGENTS.md with timestamp syncing and PR scoping guideline.
- Fixed Streamlit warning about duplicated `model_name` widget defaults.
