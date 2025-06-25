import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)  # noqa: E402

from handlers import EXEC  # noqa: E402


def test_exec_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = EXEC({"cmd": "sleep 20"})
    assert "timed out" in result


def test_exec_success(monkeypatch):
    def fake_run(*args, **kwargs):
        class Res:
            stdout = "ok"
            stderr = ""
        return Res()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = EXEC({"cmd": "echo ok"})
    assert result == "ok"


def test_exec_dry_run(monkeypatch):
    def fail_run(*args, **kwargs):
        raise AssertionError("should not be called")

    monkeypatch.setattr(subprocess, "run", fail_run)
    result = EXEC({"cmd": "echo hi", "dry_run": "true"})
    assert "DRY RUN" in result

def test_exec_single_quotes(monkeypatch, tmp_path):
    """EXEC should handle single-quoted cmd values containing double quotes."""
    from command_executor import CommandExecutor
    from error_logger import ErrorLogger
    from config import Config
    from output_manager import OutputManager
    from command_registration import register_core_commands

    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    ce = CommandExecutor(logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    register_core_commands(ce)

    captured = {}
    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        class Res:
            stdout = 'hi'
            stderr = ''
        return Res()

    monkeypatch.setattr(subprocess, 'run', fake_run)
    text = "[[COMMAND: EXEC cmd='echo \"hi\"']]"
    results = ce.parse_and_execute(text)
    assert results == [("EXEC", "hi")]
    assert captured['cmd'] == 'echo "hi"'
