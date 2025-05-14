
"""Arbitrary transform handler."""
from pathlib import Path
from gemini_adapter import GeminiAdapter

TASK_TYPE = 'gemini_transform'
adapter = GeminiAdapter()

def handle(input_path: Path, step_cfg: dict, workspace_dir: Path):
    try:
        text = input_path.read_text()
        prompt = step_cfg['parameters'].get('prompt_template','Transform this text:\n') + text
        response = adapter.call(prompt, model=step_cfg['parameters'].get('model','gemini-pro'))
        if step_cfg['output_config'].get('overwrite', False):
            input_path.write_text(response)
            return True, None, None
        else:
            output_path = input_path.with_name(input_path.stem + '_transformed' + input_path.suffix)
            output_path.write_text(response)
            return True, output_path, None
    except Exception as e:
        return False, None, str(e)
