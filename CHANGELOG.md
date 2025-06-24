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
