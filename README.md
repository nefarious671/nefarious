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

## Available Commands

| Command        | Description                               |
| -------------- | ----------------------------------------- |
| WRITE_FILE     | Save content to the outputs directory.    |
| READ_FILE      | Read a file from outputs.                 |
| LIST_OUTPUTS   | List files under outputs/.                |
| DELETE_FILE    | Delete a file from outputs/.              |
| EXEC           | Execute a sandboxed shell command.        |
| WORD_COUNT     | Count lines and words in a file.          |
| LS             | Alias for `LIST_OUTPUTS`.                 |
| CAT            | Alias for `READ_FILE`.                    |
| RM             | Alias for `DELETE_FILE`.                  |
| WC             | Alias for `WORD_COUNT`.                   |
| *(plugins)*    | Additional commands registered via entry points. |

