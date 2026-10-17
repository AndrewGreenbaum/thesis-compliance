"""Run the CLI once and preserve failures in GitHub Actions."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_check(env=None, runner=subprocess.run):
    env = os.environ if env is None else env
    strict = env.get("THESIS_STRICT", "false").lower() == "true"
    output_format = env.get("THESIS_FORMAT", "console")
    if output_format not in {"console", "brief", "json"}:
        print("Unknown report format", file=sys.stderr)
        return 3
    args = [
        "thesis-check",
        "check",
        env["THESIS_PDF"],
        "--spec",
        env.get("THESIS_SPEC", "rackham"),
        "--format",
        "json",
    ]
    if env.get("THESIS_PAGES"):
        args += ["--pages", env["THESIS_PAGES"]]
    if strict:
        args += ["--strict"]
    try:
        completed = runner(args, capture_output=True, text=True, check=False)
    except OSError as error:
        completed = subprocess.CompletedProcess(args, 3, "", str(error))
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    try:
        report = json.loads(completed.stdout)
        errors, warnings = report["error_count"], report["warning_count"]
        if type(errors) is not int or type(warnings) is not int or min(errors, warnings) < 0:
            raise ValueError("Invalid report counts")
        passed = report.get("passed") is True and errors == 0 and not (strict and warnings)
    except (ValueError, KeyError, TypeError):
        print("The checker did not produce a valid JSON report.", file=sys.stderr)
        report = {"passed": False, "error_count": 0, "warning_count": 0, "tool_error": True}
        errors, warnings, passed = 0, 0, False
    passed = passed and completed.returncode == 0
    report["passed"] = passed
    report_path = Path(
        env.get("THESIS_REPORT", str(Path(env.get("RUNNER_TEMP", ".")) / "thesis-results.json"))
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if env.get("GITHUB_OUTPUT"):
        with open(env["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"errors={errors}\nwarnings={warnings}\npassed={str(passed).lower()}\n")
    if output_format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Thesis check: {'passed' if passed else 'failed'}; "
            f"{errors} errors, {warnings} warnings"
        )
        if output_format == "console":
            for violation in report.get("violations", []):
                print(f"Page {violation.get('page', '?')}: {violation.get('message', '')}")
    if completed.returncode:
        return completed.returncode if completed.returncode > 0 else 3
    if report.get("tool_error"):
        return 3
    return 0 if passed else (2 if strict and warnings and not errors else 1)


if __name__ == "__main__":
    sys.exit(run_check())
