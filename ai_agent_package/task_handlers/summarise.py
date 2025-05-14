
"""Summarise handler."""
from pathlib import Path
from gemini_adapter import GeminiAdapter

TASK_TYPE = 'gemini_summarise'

adapter = GeminiAdapter()

def handle(input_path: Path, step_cfg: dict, workspace_dir: Path):
    try:
        text = input_path.read_text()
        prompt = f"Summarise this text in {step_cfg['parameters'].get('summary_length','short')} form:\n" + text
        response = adapter.call(prompt, model=step_cfg['parameters'].get('model','gemini-pro'))
        suffix = step_cfg['output_config'].get('filename_suffix','_summary')
        output_path = input_path.with_name(input_path.stem + suffix + input_path.suffix)
        output_path.write_text(response)
        return True, output_path, None
    except Exception as e:
        return False, None, str(e)
