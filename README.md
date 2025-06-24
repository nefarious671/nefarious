# Laser Lens

Laser Lens is a recursive research agent powered by Google's Gemini models.
It provides both a CLI and Streamlit UI for interacting with the agent.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
```

## Usage

### CLI

```bash
python -m laser_lens.cli_main --topic "Your research topic"
```
The CLI now interprets command markers and prints their results inline,
matching the formatting shown in the Streamlit UI.

### Streamlit UI

```bash
streamlit run laser_lens/ui_main.py
```

During each loop the UI highlights commands as informational blocks and shows
their results in separate code sections. The view automatically scrolls to the
newest output and offers a download button for the final Markdown. Both the UI
and CLI record metadata about each run in `outputs/session.json`.

Large uploads are truncated automatically if they would exceed the agent's
context window. The first and last portions are kept with a `[truncated]`
marker so oversized files still contribute useful context.
The complete content is saved to `outputs/full_<name>` for later retrieval.
When `READ_FILE` truncates output to the first 10 lines it will prefix a
`WARNING:` message showing the original line count.
Command outputs are numbered in prompts and logs so multi-command errors are easier to trace.

## Available Commands

| Command        | Description                               |
| -------------- | ----------------------------------------- |
| WRITE_FILE     | Save content to the outputs directory.    |
| APPEND_FILE    | Append text to an existing file.          |
| READ_FILE      | Read a file from outputs.                 |
| READ_LINES     | Read specific line range from a file.     |
| LIST_OUTPUTS   | List files under outputs/.                |
| DELETE_FILE    | Delete a file from outputs/.              |
| EXEC           | Execute a sandboxed shell command.        |
| WORD_COUNT     | Count lines and words in a file.          |
| LS             | Alias for `LIST_OUTPUTS`.                 |
| CAT            | Alias for `READ_FILE`.                    |
| RM             | Alias for `DELETE_FILE`.                  |
| WC             | Alias for `WORD_COUNT`.                   |
| RL             | Alias for `READ_LINES`.                   |
| HELP           | Show OS info and command list.            |
| CANCEL         | Stop recursion with a reason.             |
| PAUSE          | Pause recursion with a reason.            |
| *(plugins)*    | Additional commands registered via entry points. |

`READ_LINES` requires numeric `start` and `end` parameters. If the values are
non-numeric or the range is invalid the command returns an error message.

