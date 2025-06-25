# utils.py

import os
import json
import re
import unicodedata
from typing import List, Tuple

PREFS_PATH = os.path.expanduser("~/.laser_lens_prefs.json")
KEYS_PATH = os.path.expanduser("~/.laser_lens_keys.json")


def slugify(text: str) -> str:
    """
    Converts 'My Topic Title!' → 'my_topic_title'
    - Lowercases, removes accents, replaces non-alphanumeric with underscores, collapses duplicates.
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def suggest_filename(topic: str) -> str:
    """
    Builds a filename from topic + timestamp, with '.md' extension.
    """
    from datetime import datetime

    base = slugify(topic)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}.md"


def count_tokens(text: str) -> int:
    """
    Approximate token count by characters for now.
    Future improvement: integrate tiktoken.
    """
    return len(text)


def parse_tmp(raw: str, delim: str) -> Tuple[List[str], str]:
    """
    Splits raw .tmp content by delim into completed segments vs. last incomplete chunk.
    Returns (completed_chunks, last_partial).
    """
    parts = raw.split(delim)
    if len(parts) <= 1:
        return ([], raw)
    # All but last are “completed” (they end with delim)
    completed = [p for p in parts[:-1] if p.strip()]
    last = parts[-1]
    return (completed, last)


def build_markdown(history: list, topic: str) -> str:
    """
    Given history=[{"prompt":…, "response":…, "timestamp":…}, …],
    format into a single Markdown string:
      # Recursive Analysis of <topic>
      ## Loop 1 (timestamp)
      **Prompt:** …
      **Response:** …
      …
    """
    lines = [f"# Recursive Analysis of {topic}\n"]
    for idx, entry in enumerate(history, start=1):
        # lines.append(f"## Loop {idx} ({entry['timestamp']})\n")
        lines.append(f"```\n{entry['response']}\n```\n")
    return "\n".join(lines)


def load_pref_model(models_available: List[str]) -> str:
    """
    Load the last‐used model from prefs file. If not found or not in the current list,
    return the first entry in models_available.
    """
    try:
        if os.path.isfile(PREFS_PATH):
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            last = data.get("last_model", "")
            if last in models_available:
                return last
    except Exception:
        pass

    # Fallback: use the first model in the list
    return models_available[0] if models_available else ""


def save_pref_model(model_name: str) -> None:
    """
    Save the given model_name under the key "last_model" in the prefs file.
    """
    data = {}
    if os.path.isfile(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["last_model"] = model_name
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        # Silently ignore any write error
        pass


def load_pref_key(names: List[str]) -> str:
    """Return the last used key name if available."""
    try:
        if os.path.isfile(PREFS_PATH):
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            last = data.get("last_key", "")
            if last in names:
                return last
    except Exception:
        pass
    return names[0] if names else ""


def save_pref_key(name: str) -> None:
    """Persist the chosen key name for next startup."""
    data = {}
    if os.path.isfile(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["last_key"] = name
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def load_api_keys() -> List[dict]:
    """Load stored API keys from KEYS_PATH."""
    try:
        if os.path.isfile(KEYS_PATH):
            with open(KEYS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_api_key(name: str, key: str, description: str = "") -> None:
    """Add or update an API key entry."""
    keys = load_api_keys()
    for entry in keys:
        if entry.get("name") == name:
            entry["key"] = key
            entry["description"] = description
            break
    else:
        keys.append({"name": name, "key": key, "description": description})
    try:
        with open(KEYS_PATH, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
    except Exception:
        pass


def get_api_key(name: str) -> str:
    """Return the API key value for *name* if present."""
    for entry in load_api_keys():
        if entry.get("name") == name:
            return entry.get("key", "")
    return ""


def delete_api_key(name: str) -> None:
    """Remove the API key entry matching *name* if it exists."""
    keys = [k for k in load_api_keys() if k.get("name") != name]
    try:
        with open(KEYS_PATH, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
    except Exception:
        pass
