# Development Journal

This document records notes, lessons learned, and pain points discovered while working on the code base. Future contributors can review these entries to understand previous decisions and avoid repeating mistakes.

## Entries

- *Initial entry:* set up journal for future PRs.
- Added WORD_COUNT command as part of optional enhancements.
- Implemented truncation of oversize context files.
- Began phase 7 with OS awareness, adding HELP and READ_LINES commands.
- Reviewed test coverage and added edge case tests for command parsing,
  context uploads and output saving. Enhanced READ_LINES to validate
  numeric ranges.
- Added tests for RL alias and additional READ_LINES/EXEC edge cases.
  Removed lingering state.json from version control.
- Verified batch prompt with multiple file commands and added numbering for command logs.
- Moved Start button into settings form and converted control buttons to icons.
- Implemented RUN_PYTHON command and expanded HELP output. Updated docs and tests accordingly.
- Began phase 13 with Sphinx docs and README cleanup.
\n- Completed Phase 14 by adding single-quote support to EXEC. Updated docs and tests.
- Started phase 15 to display pause/cancel reasons and ensure inline pause messages reach the agent.
- Added a thinking mode toggle to suppress OS instructions in prompts.
- Styled sidebar control buttons with larger square icons during phase 17.
- Fixed broken copy button in stream output by using components.html for script.
- Implemented base64 support for WRITE_FILE and added tests.
