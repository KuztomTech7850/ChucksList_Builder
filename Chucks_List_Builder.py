"""
Chucks_List_Builder.py
Role: Single orchestration entrypoint for the Chuck's List publishing pipeline.
Called by operator as: py Chucks_List_Builder.py --issue-date YYYY-MM-DD

Changes in this revision:
  - subprocess output streamed live line-by-line (no buffered black-box)
  - show-stopper errors appended to logs/preprocess_errors.jsonl for trend tracking
  - builder communicates unresolved WARN/ERROR items inline with operator guidance
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent
LOGS_DIR = PROJ_DIR / "logs"
ERROR_LOG = LOGS_DIR / "preprocess_errors.jsonl"

PIPELINE_STAGES = {
    "bulletin": [
        {"name": "Bulletin Preprocess", "script": PROJ_DIR / "bulletins" / "preprocess_bulletin_text.py"},
        {"name": "Bulletin Compile",    "script": PROJ_DIR / "bulletins" / "compile_bulletin.py"},
    ],
    "events": [
        {"name": "Events Preprocess", "script": PROJ_DIR / "events" / "preprocess_events_text.py"},
        {"name": "Events Compile",    "script": PROJ_DIR / "events" / "compile_events.py"},
    ],
}

OUTPUT_FILES = {
    "bulletin": PROJ_DIR / "bulletins" / "chucks_bulletin_final_output.html",
    "events":   PROJ_DIR / "events"    / "chucks_events_final_output.html",
}


def setup_logging(log_to_file: bool, issue_date: str) -> logging.Logger:
    logger = logging.getLogger("chucks_builder")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    if log_to_file:
        LOGS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_file = LOGS_DIR / f"build_{ts}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.info(f"Log file: {log_file}")
    return logger


def validate_issue_date(issue_date_str: str) -> date:
    try:
        return date.fromisoformat(issue_date_str)
    except ValueError:
        print(
            f"ERROR: --issue-date '{issue_date_str}' is not a valid date.\n"
            f"  Expected format: YYYY-MM-DD (e.g., 2026-05-31)",
            file=sys.stderr,
        )
        sys.exit(1)


def log_blocking_errors(
    pipeline: str, stage_name: str, issue_date: str, stderr_lines: list[str]
) -> None:
    """
    Append show-stopper error lines to logs/preprocess_errors.jsonl.
    Each line is one JSON object for easy trend analysis.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().isoformat(timespec="seconds")
    error_lines = [
        line.strip() for line in stderr_lines
        if "[ERROR]" in line or line.startswith("ERROR:")
    ]
    if not error_lines:
        return
    entry = {
        "timestamp": ts,
        "issue_date": issue_date,
        "pipeline": pipeline,
        "stage": stage_name,
        "errors": error_lines,
    }
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # never let logging crash the build


def run_stage(
    stage: dict, pipeline: str, issue_date: str, logger: logging.Logger
) -> tuple[int, list[str]]:
    """
    Run one pipeline stage, streaming stdout/stderr live as each line arrives.
    Returns (returncode, stderr_lines).
    """
    script = stage["script"]
    name   = stage["name"]

    if not script.exists():
        msg = f"ERROR: Script not found: {script}"
        logger.error(msg)
        return 1, [msg]

    cmd = [sys.executable, str(script), "--issue-date", issue_date]
    logger.info(f"  Running: {' '.join(str(c) for c in cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJ_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        msg = f"ERROR: Failed to launch {script.name}: {exc}"
        logger.error(msg)
        return 1, [msg]

    stderr_lines: list[str] = []

    # Stream stdout live
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            logger.info(f"    {line}")

    # Stream stderr live, classifying by tag
    for line in proc.stderr:
        line = line.rstrip()
        if not line:
            continue
        stderr_lines.append(line)
        if "[WARN]" in line:
            logger.warning(f"    {line}")
        elif "[AUTO-FIX]" in line:
            logger.info(f"    {line}")
        else:
            logger.error(f"    {line}")

    proc.wait()
    return proc.returncode, stderr_lines


def open_in_vscode(paths: list, logger: logging.Logger) -> None:
    """Non-fatal convenience open. shell=True needed on Windows for 'code' alias."""
    try:
        for p in paths:
            if p.exists():
                subprocess.Popen(f'code "{p}"', shell=True)
                logger.info(f"  Opened in VS Code: {p.name}")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chuck's List publishing pipeline builder.",
        epilog=(
            "Examples:\n"
            "  py Chucks_List_Builder.py --issue-date 2026-05-31\n"
            "  py Chucks_List_Builder.py --issue-date 2026-05-31 --issue-type bulletin\n"
            "  py Chucks_List_Builder.py --issue-date 2026-05-31 --log-to-file\n"
        ),
    )
    parser.add_argument("--issue-date", required=True, metavar="YYYY-MM-DD",
                        help="Publication date for this issue")
    parser.add_argument("--issue-type", choices=["bulletin", "events", "both"],
                        default="both", help="Which pipeline(s) to run (default: both)")
    parser.add_argument("--log-to-file", action="store_true",
                        help="Write build log to logs/build_YYYY-MM-DD_HHMMSS.log")
    parser.add_argument("--no-open-vscode", action="store_true",
                        help="Do not open output files in VS Code after build")
    args = parser.parse_args()

    validate_issue_date(args.issue_date)
    logger = setup_logging(args.log_to_file, args.issue_date)

    logger.info("=" * 60)
    logger.info(f"Chuck's List Builder -- issue date: {args.issue_date}")
    logger.info(f"Pipeline: {args.issue_type}  |  Project root: {PROJ_DIR}")
    logger.info("=" * 60)

    pipelines = []
    if args.issue_type in ("bulletin", "both"):
        pipelines.append("bulletin")
    if args.issue_type in ("events", "both"):
        pipelines.append("events")

    failed_stages: list[str] = []
    passed_stages: list[str] = []

    for pipeline in pipelines:
        logger.info(f"\n-- {pipeline.upper()} PIPELINE --")
        for stage in PIPELINE_STAGES[pipeline]:
            logger.info(f"\n  Stage: {stage['name']}")
            rc, stderr_lines = run_stage(stage, pipeline, args.issue_date, logger)
            if rc != 0:
                logger.error(
                    f"  FAILED: {stage['name']} exited with code {rc}.\n"
                    f"  Stopping {pipeline} pipeline. Fix errors above and re-run."
                )
                log_blocking_errors(pipeline, stage["name"], args.issue_date, stderr_lines)
                failed_stages.append(stage["name"])
                break
            else:
                passed_stages.append(stage["name"])

    logger.info("\n" + "=" * 60)
    logger.info("BUILD SUMMARY")
    logger.info("=" * 60)
    for s in passed_stages:
        logger.info(f"  [OK]   {s}")
    for s in failed_stages:
        logger.error(f"  [FAIL] {s}")

    if not failed_stages:
        logger.info("\nAll stages passed.")
        if not args.no_open_vscode:
            outputs = [OUTPUT_FILES[p] for p in pipelines if OUTPUT_FILES[p].exists()]
            open_in_vscode(outputs, logger)
        logger.info("\nNext steps:")
        for p in pipelines:
            logger.info(f"  Upload {OUTPUT_FILES[p].name} to Zoho Campaigns.")
        return 0
    else:
        logger.error(
            f"\n{len(failed_stages)} stage(s) failed. "
            f"Do not upload partial output to Zoho."
        )
        if ERROR_LOG.exists():
            logger.error(f"  Error log: {ERROR_LOG}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
