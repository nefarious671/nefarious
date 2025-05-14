
"""Filesystem move handler."""
from pathlib import Path
import shutil

TASK_TYPE = 'filesystem_move'

def handle(input_path: Path, step_cfg: dict, workspace_dir: Path):
    try:
        target_dir = workspace_dir / step_cfg['parameters']['target_subdir']
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / input_path.name
        shutil.copy2(input_path, target)
        return True, target, None
    except Exception as e:
        return False, None, str(e)
