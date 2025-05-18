# agent.py
"""AI Agent main loop (enhanced with self-upgrade awareness)"""
import time
import uuid
import shutil
from pathlib import Path
import sqlite3
import yaml
import datetime

from database import get_connection

POLL_INTERVAL = 5  # seconds

class Agent:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.config = yaml.safe_load((workspace / 'agent_config.yaml').read_text())
        self.db_path = workspace / self.config.get('database_path', 'state.db')
        self.conn = get_connection(self.db_path)
        self.workflow = yaml.safe_load((workspace / 'workflow.yaml').read_text())
        self.request_log_path = self.workspace / 'requests' / 'handler_requests.md'
        self.request_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_handlers = self._load_handlers()

    def _load_handlers(self):
        import importlib
        handlers = {}
        handlers_pkg = 'task_handlers'
        for mod_name in ('summarise', 'transform', 'filesystem_move'):
            try:
                module = importlib.import_module(f"{handlers_pkg}.{mod_name}")
                handlers[module.TASK_TYPE] = module.handle
            except Exception as e:
                self._log_handler_request(mod_name, str(e))
        return handlers

    def _log_handler_request(self, task_type, reason):
        timestamp = datetime.datetime.utcnow().isoformat()
        with self.request_log_path.open("a") as log:
            log.write(f"### {timestamp} – Missing or failed handler load\n")
            log.write(f"- Task Type: `{task_type}`\n")
            log.write(f"- Reason: {reason}\n")
            log.write(f"- Suggested Action: Develop handler module `task_handlers/{task_type}.py` implementing `TASK_TYPE` and `handle()`\n\n")

    def _insert_instance(self, src_file: Path, inst_dir: Path):
        instance_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute(
                """INSERT INTO instances
                (instance_id, original_instance_path, status, step_index,
                 input_path, created_at, updated_at)
                VALUES (?, ?, 'pending', 0, ?, ?, ?)""",
                (
                    instance_id,
                    str(inst_dir.relative_to(self.workspace)),
                    str((inst_dir / src_file.name).relative_to(self.workspace)),
                    now,
                    now,
                ),
            )
        return instance_id

    def ingest_new_files(self):
        input_dir = self.workspace / 'input'
        processing_root = self.workspace / 'processing'
        for file in input_dir.iterdir():
            if file.is_file():
                ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                inst_dir = processing_root / f"{file.stem}_{ts}"
                inst_dir.mkdir(parents=True, exist_ok=True)
                target = inst_dir / file.name
                shutil.move(str(file), target)
                self._insert_instance(file, inst_dir)

    def run(self):
        while True:
            self.ingest_new_files()
            self.process_pending()
            time.sleep(self.config.get('polling_interval_seconds', POLL_INTERVAL))

    def process_pending(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM instances WHERE status = 'pending' ORDER BY created_at")
        rows = cur.fetchall()
        for row in rows:
            self._process_instance(row)

    def _process_instance(self, row):
        instance_id = row['instance_id']
        step_index = row['step_index']
        if step_index >= len(self.workflow):
            return
        step_cfg = self.workflow[step_index]
        handler = self.task_handlers.get(step_cfg['task_type'])
        if handler is None:
            self._log_handler_request(step_cfg['task_type'], "No handler registered for this task type")
            self._mark_error(instance_id, f"No handler for {step_cfg['task_type']}")
            return
        input_path = self.workspace / row['input_path']
        success, output_path, error_message = handler(input_path, step_cfg, self.workspace)
        if success:
            with self.conn:
                next_index = step_index + 1
                status = 'done' if next_index >= len(self.workflow) else 'pending'
                self.conn.execute(
                    "UPDATE instances SET step_index = ?, status = ?, updated_at = ?, output_path = ? WHERE instance_id = ?",
                    (
                        next_index,
                        status,
                        datetime.datetime.utcnow().isoformat(),
                        str(output_path.relative_to(self.workspace)) if output_path else row['output_path'],
                        instance_id,
                    ),
                )
        else:
            self._mark_error(instance_id, error_message)

    def _mark_error(self, instance_id, msg):
        with self.conn:
            self.conn.execute(
                "UPDATE instances SET status='error', error_message=?, updated_at=? WHERE instance_id=?",
                (msg, datetime.datetime.utcnow().isoformat(), instance_id),
            )
        print(f"Instance {instance_id} errored: {msg}")

if __name__ == '__main__':
    workspace = Path(__file__).parent / 'workspace'
    agent = Agent(workspace)
    agent.run()

