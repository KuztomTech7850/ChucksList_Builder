"""
bulletins/preprocess_bulletin_text.py
Role: Read raw Bulletins.csv, validate, filter by issue_date, write bulletins_data.csv
Pipeline stage: PREPROCESS
Called by: Chucks_List_Builder.py via subprocess

CSV column contract (actual Bulletins.csv headers):
  Received, Expires, Section, Title, Text, Image, notes

Date formats accepted: YYYY-MM-DD and MM/DD/YY
Inclusion rule: Received <= issue_date <= Expires
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR   = SCRIPT_DIR.parent
INPUT_CSV  = PROJ_DIR / "Bulletins.csv"
OUTPUT_CSV = SCRIPT_DIR / "bulletins_data.csv"

REQUIRED_COLS = ["Received", "Expires", "Section", "Title", "Text"]
OUT_COLS      = ["Title", "Body", "Section", "Received", "Expires", "Image"]

SECTION_ORDER = [
    "Urgent Bulletins",
    "Housing Opportunities",
    "Swap Market",
    "Local Services & Help",
    "Community Announcements",
]

DATE_RE_ISO   = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")  # MM/DD/YY


def parse_date(val: str, row_num: int, field: str) -> date | None:
    """Parse YYYY-MM-DD or MM/DD/YY. Prints actionable error on failure."""
    val = val.strip()
    if not val:
        print(
            f"  [WARN] Row {row_num}: '{field}' is empty. "
            f"Expected MM/DD/YY or YYYY-MM-DD. Item skipped.",
            file=sys.stderr,
        )
        return None
    if DATE_RE_ISO.match(val):
        try:
            return date.fromisoformat(val)
        except ValueError as e:
            print(f"  [WARN] Row {row_num}: '{field}' value '{val}' invalid: {e}. Skipped.", file=sys.stderr)
            return None
    m = DATE_RE_SHORT.match(val)
    if m:
        try:
            return date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError as e:
            print(f"  [WARN] Row {row_num}: '{field}' value '{val}' invalid: {e}. Skipped.", file=sys.stderr)
            return None
    print(
        f"  [WARN] Row {row_num}: '{field}' unrecognized date '{val}'. "
        f"Expected MM/DD/YY or YYYY-MM-DD. Item skipped.",
        file=sys.stderr,
    )
    return None


def preprocess_bulletins(issue_date_str: str) -> int:
    try:
        issue_date = date.fromisoformat(issue_date_str)
    except ValueError:
        print(f"ERROR: --issue-date '{issue_date_str}' must be YYYY-MM-DD.", file=sys.stderr)
        return 1

    if not INPUT_CSV.exists():
        print(
            f"ERROR: Not found: {INPUT_CSV}\n"
            f"  Fix: Export Bulletins sheet from Chucks-list-MASTER.ods as CSV to {INPUT_CSV}",
            file=sys.stderr,
        )
        return 1

    try:
        with open(INPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("ERROR: Bulletins.csv has no header row.", file=sys.stderr)
                return 1
            missing = set(REQUIRED_COLS) - set(reader.fieldnames)
            if missing:
                print(
                    f"ERROR: Bulletins.csv missing columns: {', '.join(sorted(missing))}\n"
                    f"  Found: {', '.join(sorted(reader.fieldnames))}\n"
                    f"  Fix: Re-export from Chucks-list-MASTER.ods.",
                    file=sys.stderr,
                )
                return 1
            all_rows = list(reader)
    except UnicodeDecodeError:
        print("ERROR: Bulletins.csv is not UTF-8. Re-export with UTF-8 encoding.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR reading Bulletins.csv: {e}", file=sys.stderr)
        return 1

    passing, skipped = [], 0

    for i, row in enumerate(all_rows, start=2):
        title    = (row.get("Title") or "").strip()
        section  = (row.get("Section") or "").strip()
        body     = (row.get("Text") or "").replace("\r\n", "\n").replace("\r", "\n")
        image    = (row.get("Image") or "").strip()
        received_str = (row.get("Received") or "").strip()
        expires_str  = (row.get("Expires") or "").strip()

        if not any(v.strip() for v in row.values()):
            continue  # blank row

        if not title:
            print(f"  [WARN] Row {i}: empty Title in section '{section}'. Skipped.", file=sys.stderr)
            skipped += 1
            continue

        received = parse_date(received_str, i, "Received")
        expires  = parse_date(expires_str,  i, "Expires")
        if received is None or expires is None:
            skipped += 1
            continue

        if not (received <= issue_date <= expires):
            continue  # normal date exclusion

        if section and section not in SECTION_ORDER:
            print(
                f"  [WARN] Row {i}: '{title}' has unknown Section '{section}'.\n"
                f"  Valid: {', '.join(SECTION_ORDER)}\n"
                f"  Fix: Correct Section in Chucks-list-MASTER.ods.",
                file=sys.stderr,
            )
            skipped += 1
            continue

        if "href=" in body.lower() or "<a " in body.lower():
            print(
                f"  [WARN] Row {i}: '{title}' Body contains raw HTML. "
                f"Use plain-text URLs — the compile stage will linkify them.",
                file=sys.stderr,
            )

        passing.append({
            "Title":    title,
            "Body":     body,
            "Section":  section,
            "Received": received_str,
            "Expires":  expires_str,
            "Image":    image,
        })

    try:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(passing)
    except Exception as e:
        print(f"ERROR writing {OUTPUT_CSV}: {e}", file=sys.stderr)
        return 1

    print(
        f"  [OK] Bulletins preprocess: {len(passing)} items -> {OUTPUT_CSV} "
        f"({skipped} skipped, issue_date={issue_date_str})"
    )
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--issue-date", required=True)
    args = p.parse_args()
    sys.exit(preprocess_bulletins(args.issue_date))