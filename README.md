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

### Streamlit UI

```bash
streamlit run laser_lens/ui_main.py
```

## Available Commands

| Command        | Description                               |
| -------------- | ----------------------------------------- |
| WRITE_FILE     | Save content to the outputs directory.    |
| READ_FILE      | Read a file from outputs.                 |
| LIST_OUTPUTS   | List files under outputs/.                |
| DELETE_FILE    | Delete a file from outputs/.              |
| EXEC           | Execute a sandboxed shell command.        |
| LS             | Alias for `LIST_OUTPUTS`.                 |
| CAT            | Alias for `READ_FILE`.                    |
| RM             | Alias for `DELETE_FILE`.                  |

