import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laser_lens"))
sys.path.insert(0, ROOT)

from command_executor import CommandExecutor  # noqa: E402
from error_logger import ErrorLogger  # noqa: E402
from config import Config  # noqa: E402
from command_registration import register_core_commands  # noqa: E402
from output_manager import OutputManager  # noqa: E402


def test_parse_and_execute_basic(tmp_path, monkeypatch):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)

    def foo(args):
        return args.get("val", "")

    ce.register_command("FOO", foo)
    results = ce.parse_and_execute("do [[COMMAND: FOO val=\"x\"]]")
    assert results == [("FOO", "x")]


def test_unknown_and_invalid_commands(tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)

    results = ce.parse_and_execute("[[COMMAND: MISSING]]")
    assert results == []

    results = ce.parse_and_execute("[[COMMAND: BAD badarg]]")
    assert results and "badarg" in results[0][1]


def test_alias_ls(monkeypatch, tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    om = OutputManager(cfg, logger)
    ce = CommandExecutor(logger)
    monkeypatch.setattr('handlers._cfg', cfg)
    monkeypatch.setattr('handlers._output_mgr', om)
    register_core_commands(ce)

    om.save_output('sample.txt', 'hi')
    results = ce.parse_and_execute('[[COMMAND: LS]]')
    assert results
    cmd, output = results[0]
    assert cmd == 'LS'
    assert 'sample.txt' in output


def test_single_quote_args(tmp_path):
    cfg = Config(safe_output_dir=str(tmp_path))
    logger = ErrorLogger(cfg)
    ce = CommandExecutor(logger)

    def foo(args):
        return args.get("val")

    ce.register_command("FOO", foo)
    results = ce.parse_and_execute("[[COMMAND: FOO val='bar baz']]")
    assert results == [("FOO", "bar baz")]
