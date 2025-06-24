# Changelog

## Phase 1 - Agent Reasoning Core
- Injected tool outputs from previous loop into the next prompt.
- Added persistent deque-based history of last three thoughts.
- Removed duplicate prompt builder and cleaned imports.

## Phase 2 - Command Framework Expansion
- Added sandboxed `EXEC` command for running shell commands in `outputs/`.
- Created alias commands `LS`, `CAT` and `RM` via `command_registration.py`.
- Initial README with setup and command documentation.

