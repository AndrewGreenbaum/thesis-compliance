import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "run_action", Path(__file__).parents[1] / "scripts" / "run_action.py"
)
action = importlib.util.module_from_spec(spec)
spec.loader.exec_module(action)


@pytest.fixture
def action_env(tmp_path):
    return {
        "THESIS_PDF": "a thesis; $(not-a-command).pdf",
        "THESIS_SPEC": "rackham",
        "THESIS_PAGES": "2-4",
        "THESIS_STRICT": "true",
        "THESIS_REPORT": str(tmp_path / "report.json"),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
    }


def test_cli_receives_subcommand_and_literal_arguments(action_env):
    def runner(args, **kwargs):
        assert args == [
            "thesis-check",
            "check",
            action_env["THESIS_PDF"],
            "--spec",
            "rackham",
            "--format",
            "json",
            "--pages",
            "2-4",
            "--strict",
        ]
        assert kwargs == {"capture_output": True, "text": True, "check": False}
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps(
                {
                    "passed": True,
                    "error_count": 0,
                    "warning_count": 0,
                }
            ),
            "",
        )

    assert action.run_check(action_env, runner) == 0
    assert "passed=true" in Path(action_env["GITHUB_OUTPUT"]).read_text()


@pytest.mark.parametrize(
    "code,stdout",
    [
        (3, "Error: file not found"),
        (0, "not JSON"),
        (0, "{}"),
        (0, '{"passed":true,"error_count":"oops","warning_count":0}'),
        (1, '{"passed":true,"error_count":0,"warning_count":0}'),
        (0, '{"passed":false,"error_count":1,"warning_count":0}'),
        (0, '{"passed":true,"error_count":0,"warning_count":1}'),
    ],
)
def test_tool_errors_and_strict_warnings_never_pass(action_env, code, stdout):
    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(args, code, stdout, "")

    assert action.run_check(action_env, runner) != 0
    assert "passed=false" in Path(action_env["GITHUB_OUTPUT"]).read_text()
    assert json.loads(Path(action_env["THESIS_REPORT"]).read_text())["passed"] is False


def test_runs_real_cli_on_pdf(action_env, valid_thesis_pdf, monkeypatch):
    import os
    import sys

    monkeypatch.setenv("PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    action_env["THESIS_PDF"] = str(valid_thesis_pdf)
    action_env["THESIS_PAGES"] = "1"
    code = action.run_check(action_env)
    report = json.loads(Path(action_env["THESIS_REPORT"]).read_text())
    assert "tool_error" not in report
    assert report["pages_checked"] == 1
    assert code in (0, 1, 2)


def test_missing_executable_still_writes_failure_report(action_env):
    def missing(*args, **kwargs):
        raise FileNotFoundError("thesis-check")

    assert action.run_check(action_env, missing) == 3
    assert json.loads(Path(action_env["THESIS_REPORT"]).read_text())["tool_error"] is True
