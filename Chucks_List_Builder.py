# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


"""
File: Chucks_List_Builder.py
Role: Top-level production orchestrator

Purpose:
- Run Chuck's List local production pipeline from a single command
- Validate inputs and required files
- Execute preprocess + compile stages in correct order
- Report clean success/failure status
- Optionally write logs to ./logs/

Supported options:
    --issue-date YYYY-MM-DD
    --issue-type bulletin | events | both
    --log-to-file
    --no-open-vscode   (reserved for future behavior)
"""


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
BULLETINS_DIR = BASE_DIR / "bulletins"
EVENTS_DIR = BASE_DIR / "events"
LOGS_DIR = BASE_DIR / "logs"

BULLETINS_CSV = BASE_DIR / "Bulletins.csv"
EVENTS_CSV = BASE_DIR / "Events.csv"

PYTHON_EXE = sys.executable


# ============================================================
# ARGUMENTS
# ============================================================

def parse_issue_date_arg(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid --issue-date '{value}'. Use YYYY-MM-DD."
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chuck's List unified builder for bulletin and events pipelines."
    )

    parser.add_argument(
        "--issue-date",
        type=parse_issue_date_arg,
        required=True,
        help="Issue date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--issue-type",
        choices=["bulletin", "events", "both"],
        default="both",
        help="Which pipeline(s) to run. Default: both.",
    )

    parser.add_argument(
        "--log-to-file",
        action="store_true",
        help="Also write a log file under ./logs/.",
    )

    parser.add_argument(
        "--no-open-vscode",
        action="store_true",
        help="Reserved for future behavior; currently ignored.",
    )

    return parser.parse_args()


# ============================================================
# LOGGING
# ============================================================

class BuildLogger:
    def __init__(self, log_to_file: bool, issue_date: date, issue_type: str):
        self.log_to_file = log_to_file
        self.issue_date = issue_date
        self.issue_type = issue_type
        self.log_path: Path | None = None
        self._handle = None

        if self.log_to_file:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.log_path = LOGS_DIR / f"build-{issue_type}-{issue_date.isoformat()}-{timestamp}.log"
            self._handle = open(self.log_path, "w", encoding="utf-8", newline="")

    def close(self) -> None:
        if self._handle:
            self._handle.close()
            self._handle = None

    def _write(self, level: str, message: str) -> None:
        line = f"[{level}] {message}"
        print(line)
        if self._handle:
            self._handle.write(line + "\n")
            self._handle.flush()

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warn(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def section(self, message: str) -> None:
        divider = "=" * 72
        self._write("INFO", divider)
        self._write("INFO", message)
        self._write("INFO", divider)


# ============================================================
# VALIDATION
# ============================================================

def validate_required_files(issue_type: str, logger: BuildLogger) -> bool:
    ok = True

    if issue_type in {"bulletin", "both"}:
        if BULLETINS_CSV.exists():
            logger.info(f"Found bulletin source: {BULLETINS_CSV}")
        else:
            logger.error(f"Missing required file: {BULLETINS_CSV}")
            ok = False

    if issue_type in {"events", "both"}:
        if EVENTS_CSV.exists():
            logger.info(f"Found events source: {EVENTS_CSV}")
        else:
            logger.error(f"Missing required file: {EVENTS_CSV}")
            ok = False

    return ok


# ============================================================
# SUBPROCESS RUNNER
# ============================================================

def run_script(
    script_path: Path,
    issue_date: date,
    working_dir: Path,
    logger: BuildLogger,
) -> bool:
    cmd = [
        PYTHON_EXE,
        str(script_path),
        "--issue-date",
        issue_date.isoformat(),
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"Working directory: {working_dir}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        logger.error(f"Failed to launch {script_path.name}: {exc}")
        return False

    if result.stdout:
        for line in result.stdout.splitlines():
            logger.info(f"{script_path.name} | {line}")

    if result.stderr:
        for line in result.stderr.splitlines():
            logger.error(f"{script_path.name} | {line}")

    if result.returncode != 0:
        logger.error(f"{script_path.name} exited with code {result.returncode}")
        return False

    logger.info(f"{script_path.name} completed successfully")
    return True


# ============================================================
# PIPELINE DEFINITIONS
# ============================================================

def bulletin_pipeline(issue_date: date, logger: BuildLogger) -> bool:
    logger.section("BULLETIN PIPELINE")

    preprocess_script = BULLETINS_DIR / "preprocess_bulletin_text.py"
    compile_script = BULLETINS_DIR / "compile_bulletin.py"

    if not preprocess_script.exists():
        logger.error(f"Missing bulletin preprocess script: {preprocess_script}")
        return False

    if not compile_script.exists():
        logger.error(f"Missing bulletin compile script: {compile_script}")
        return False

    if not run_script(preprocess_script, issue_date, BULLETINS_DIR, logger):
        logger.error("Bulletin preprocess stage failed")
        return False

    if not run_script(compile_script, issue_date, BULLETINS_DIR, logger):
        logger.error("Bulletin compile stage failed")
        return False

    logger.info("Bulletin pipeline succeeded")
    return True


def events_pipeline(issue_date: date, logger: BuildLogger) -> bool:
    logger.section("EVENTS PIPELINE")

    preprocess_script = EVENTS_DIR / "preprocess_events_text.py"
    compile_script = EVENTS_DIR / "compile_events.py"

    if not preprocess_script.exists():
        logger.error(f"Missing events preprocess script: {preprocess_script}")
        return False

    if not compile_script.exists():
        logger.error(f"Missing events compile script: {compile_script}")
        return False

    if not run_script(preprocess_script, issue_date, EVENTS_DIR, logger):
        logger.error("Events preprocess stage failed")
        return False

    if not run_script(compile_script, issue_date, EVENTS_DIR, logger):
        logger.error("Events compile stage failed")
        return False

    logger.info("Events pipeline succeeded")
    return True


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    args = parse_args()
    logger = BuildLogger(
        log_to_file=args.log_to_file,
        issue_date=args.issue_date,
        issue_type=args.issue_type,
    )

    try:
        logger.section("CHUCK'S LIST BUILDER START")
        logger.info(f"BASE_DIR: {BASE_DIR}")
        logger.info(f"ISSUE_DATE: {args.issue_date.isoformat()}")
        logger.info(f"ISSUE_TYPE: {args.issue_type}")
        logger.info(f"LOG_TO_FILE: {args.log_to_file}")
        logger.info(f"NO_OPEN_VSCODE: {args.no_open_vscode}")

        if logger.log_path:
            logger.info(f"LOG_PATH: {logger.log_path}")

        if not validate_required_files(args.issue_type, logger):
            logger.error("Required file validation failed")
            return 1

        bulletin_ok = True
        events_ok = True

        if args.issue_type in {"bulletin", "both"}:
            bulletin_ok = bulletin_pipeline(args.issue_date, logger)

        if args.issue_type in {"events", "both"}:
            events_ok = events_pipeline(args.issue_date, logger)

        logger.section("BUILD SUMMARY")
        if args.issue_type in {"bulletin", "both"}:
            logger.info(f"Bulletin pipeline: {'SUCCESS' if bulletin_ok else 'FAILED'}")
        if args.issue_type in {"events", "both"}:
            logger.info(f"Events pipeline: {'SUCCESS' if events_ok else 'FAILED'}")

        all_ok = True
        if args.issue_type == "bulletin":
            all_ok = bulletin_ok
        elif args.issue_type == "events":
            all_ok = events_ok
        elif args.issue_type == "both":
            all_ok = bulletin_ok and events_ok

        if all_ok:
            logger.info("Build completed successfully")
            return 0

        logger.error("Build completed with failures")
        return 1

    finally:
        logger.close()


if __name__ == "__main__":
    raise SystemExit(main())