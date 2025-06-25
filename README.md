# Laser Lens

Laser Lens is a recursive research agent powered by Google's Gemini models.
It provides both a CLI and Streamlit UI for interacting with the agent.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
```

### Python Sandbox

To run `RUN_PYTHON` commands create a virtual environment and install
the requirements:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python -m laser_lens.cli_main --topic "Your research topic"
```
The CLI now interprets command markers and prints their results inline,
matching the formatting shown in the Streamlit UI.

When passing a command with embedded double quotes to ``EXEC`` use single quotes
around the entire ``cmd`` value to avoid quoting issues on Windows.

### Streamlit UI

```bash
streamlit run laser_lens/ui_main.py
```

During each loop the UI highlights commands as informational blocks and shows
their results in separate code sections. The view automatically scrolls to the
newest output and offers a download button for the final Markdown. When resuming
from a pause the page jumps back to the latest output instead of the top. The sidebar
displays the current agent status. The Start button now lives inside the
settings form so any changes are applied automatically, while the
Pause/Resume/Stop controls appear in a single row using icon-only buttons.
Both the UI and CLI record metadata about each run in `outputs/session.json`.
Agents can share notes via `outputs/GEMINIOUTPUT.md` and respond using `outputs/GEMINIINPUT.md`.

When paused—via the sidebar button or a `PAUSE` command—the sidebar displays a
message box so you can send short notes to the agent. The agent must include a
`reason` whenever issuing `PAUSE` or `CANCEL`.

Large uploads are truncated automatically if they would exceed the agent's
context window. The first and last portions are kept with a `[truncated]`
marker so oversized files still contribute useful context.
The complete content is saved to `outputs/full_<name>` for later retrieval.
When `READ_FILE` truncates output to the first 10 lines it will prefix a
`WARNING:` message showing the original line count.
Command outputs are numbered in prompts and logs so multi-command errors are easier to trace.
Severe API errors appear as concise messages. If a quota limit is hit the agent stops immediately without retrying.


## Documentation

The list of available commands and API reference is maintained in the
[project documentation](docs/index.html).
