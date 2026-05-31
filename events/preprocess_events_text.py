"""
events/preprocess_events_text.py
Role: Read raw Events.csv, validate, filter by issue_date, write events_data.csv
Pipeline stage: PREPROCESS
Called by: Chucks_List_Builder.py via subprocess

CSV column contract (actual Events.csv headers):
  Received, Starts, Expires, Section, Title, Text, Image, notes

Date formats accepted: YYYY-MM-DD and MM/DD/YY
Inclusion rule: Starts <= issue_date <= Expires

CHANGELOG
  2026-05-31  Bug 2 fix: add quoting=csv.QUOTE_ALL to DictWriter so that
              multi-line cells and cells containing []() markdown link syntax
              survive the CSV round-trip intact (was written unquoted, which
              could corrupt bracket/paren characters in the Body field and
              cause compile_events.py MARKDOWN_LINK_RE to miss the match).
              Improved skip messages: each skip now logs row, field, value,
              and fix instruction to match bulletin preprocess standard.
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR   = SCRIPT_DIR.parent
INPUT_CSV  = PROJ_DIR / "Events.csv"
OUTPUT_CSV = SCRIPT_DIR / "events_data.csv"

REQUIRED_COLS = ["Received", "Starts", "Expires", "Title", "Text"]
OUT_COLS      = ["Title", "Body", "Starts", "Ends", "Section", "Image"]

DATE_RE_ISO   = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")


def parse_date(val: str, row_num: int, field: str) -> "date | None":
    val = val.strip()
    if not val:
        print(
            f"  [WARN] Row {row_num}: '{field}' is empty — date is required.\n"
            f"  Fix: Open Chucks-list-MASTER.ods, locate row {row_num}, fill in '{field}'.",
            file=sys.stderr,
        )
        return None
    if DATE_RE_ISO.match(val):
        try:
            return date.fromisoformat(val)
        except ValueError as e:
            print(
                f"  [WARN] Row {row_num}: '{field}' value '{val}' is not a valid date: {e}\n"
                f"  Fix: Correct to YYYY-MM-DD format in Chucks-list-MASTER.ods.",
                file=sys.stderr,
            )
            return None
    m = DATE_RE_SHORT.match(val)
    if m:
        try:
            return date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError as e:
            print(
                f"  [WARN] Row {row_num}: '{field}' value '{val}' is not a valid date: {e}\n"
                f"  Fix: Correct the month/day/year in Chucks-list-MASTER.ods.",
                file=sys.stderr,
            )
            return None
    print(
        f"  [WARN] Row {row_num}: '{field}' value '{val}' is not a recognized date format.\n"
        f"  Expected MM/DD/YY or YYYY-MM-DD.\n"
        f"  Fix: Re-enter '{field}' in Chucks-list-MASTER.ods row {row_num}.",
        file=sys.stderr,
    )
    return None


def preprocess_events(issue_date_str: str) -> int:
    try:
        issue_date = date.fromisoformat(issue_date_str)
    except ValueError:
        print(f"ERROR: --issue-date '{issue_date_str}' must be YYYY-MM-DD.", file=sys.stderr)
        return 1

    if not INPUT_CSV.exists():
        print(
            f"ERROR: Not found: {INPUT_CSV}\n"
            f"  Fix: Export Events sheet from Chucks-list-MASTER.ods as CSV to {INPUT_CSV}",
            file=sys.stderr,
        )
        return 1

    try:
        with open(INPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("ERROR: Events.csv has no header row.", file=sys.stderr)
                return 1
            missing = set(REQUIRED_COLS) - set(reader.fieldnames)
            if missing:
                print(
                    f"ERROR: Events.csv missing columns: {', '.join(sorted(missing))}\n"
                    f"  Found: {', '.join(sorted(reader.fieldnames))}\n"
                    f"  Fix: Re-export from Chucks-list-MASTER.ods.",
                    file=sys.stderr,
                )
                return 1
            all_rows = list(reader)
    except UnicodeDecodeError:
        print("ERROR: Events.csv is not UTF-8. Re-export with UTF-8 encoding.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR reading Events.csv: {e}", file=sys.stderr)
        return 1

    passing, skipped = [], 0

    for i, row in enumerate(all_rows, start=2):
        title       = (row.get("Title") or "").strip()
        section     = (row.get("Section") or "").strip()
        # Normalize line endings; preserve markdown link syntax verbatim
        body        = (row.get("Text") or "").replace("\r\n", "\n").replace("\r", "\n")
        image       = (row.get("Image") or "").strip()
        starts_str  = (row.get("Starts") or "").strip()
        expires_str = (row.get("Expires") or "").strip()

        if not any(v.strip() for v in row.values()):
            continue

        if not title:
            print(
                f"  [WARN] Row {i}: Title is empty — item cannot be published.\n"
                f"  Fix: Add a Title in Chucks-list-MASTER.ods row {i}.",
                file=sys.stderr,
            )
            skipped += 1
            continue

        starts  = parse_date(starts_str,  i, "Starts")
        expires = parse_date(expires_str, i, "Expires")
        if starts is None or expires is None:
            skipped += 1
            continue

        if starts > expires:
            print(
                f"  [WARN] Row {i}: '{title}' — Starts ({starts_str}) is after "
                f"Expires ({expires_str}).\n"
                f"  Fix: Correct Starts or Expires in Chucks-list-MASTER.ods row {i}.",
                file=sys.stderr,
            )

        if not (starts <= issue_date <= expires):
            continue  # normal date exclusion — not an error

        if "href=" in body.lower() or "<a " in body.lower():
            print(
                f"  [WARN] Row {i}: '{title}' Body contains raw HTML anchor tags.\n"
                f"  Fix: Replace <a href=\"..\"> with markdown: [label](https://url) "
                f"in Chucks-list-MASTER.ods row {i}.",
                file=sys.stderr,
            )

        passing.append({
            "Title":   title,
            "Body":    body,
            "Starts":  starts_str,
            "Ends":    expires_str,
            "Section": section,
            "Image":   image,
        })

    try:
        # QUOTE_ALL ensures multi-line Body cells and cells containing markdown
        # link syntax  [label](url)  are always double-quoted in the CSV.
        # Without this, cells containing parentheses or brackets could be
        # written unquoted and mis-parsed on read-back, causing MARKDOWN_LINK_RE
        # in compile_events.py to miss matches and render links as raw text.
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=OUT_COLS,
                extrasaction="ignore",
                quoting=csv.QUOTE_ALL,   # <-- Bug 2 fix
            )
            writer.writeheader()
            writer.writerows(passing)
    except Exception as e:
        print(f"ERROR writing {OUTPUT_CSV}: {e}", file=sys.stderr)
        return 1

    print(
        f"  [OK] Events preprocess: {len(passing)} items -> {OUTPUT_CSV} "
        f"({skipped} skipped, issue_date={issue_date_str})"
    )
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--issue-date", required=True)
    args = p.parse_args()
    sys.exit(preprocess_events(args.issue_date))