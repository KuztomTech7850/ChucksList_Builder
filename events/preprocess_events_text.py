# -*- coding: utf-8 -*-
from __future__ import annotations

"""
filename: preprocess_events_text.py
role: Events preprocess
pipeline: Events-only

Reads Events.csv as a proper CSV table, normalizes and filters rows based on
issue date, and writes events_data.csv as comma-separated values.

Input columns (case-insensitive, flexible):
    Received, Starts, Expires, Section, Title, Text, Image, notes

Output columns (intermediate):
    section, title, text, image, starts, ends

The compiler is responsible for grouping (Single / Multiple / Recurring)
and final layout.
"""

import argparse
import csv
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------- Paths and constants ----------

SCRIPT_DIR = Path(__file__).resolve().parent
COMPILER_DIR = SCRIPT_DIR.parent
BASE_DIR = COMPILER_DIR.parent

EVENTS_OUTPUT_PATH = COMPILER_DIR / "events" / "events_data.csv"
EVENTS_OUTPUT_FIELDS = ["section", "title", "text", "image", "starts", "ends"]

# Common text repairs (Windows-1252 / mojibake cleanup)
COMMON_TEXT_REPAIRS = {
    "\u00a0": " ",  # non-breaking space
    "Â ": " ",
    "Â": "",
    "â€”": "—",
    "â€“": "–",
    "â€˜": "‘",
    "â€™": "’",
    "â€œ": "“",
    "â€\x9d": "”",
    "â€¦": "…",
}

# Header normalization map
HEADER_ALIASES = {
    # Dates
    "received": "received",
    "received date": "received",

    "starts": "starts",
    "start": "starts",
    "start date": "starts",

    "expires": "ends",   # Expires becomes ends
    "expiration": "ends",
    "ends": "ends",
    "end": "ends",
    "end date": "ends",

    # Section/category
    "section": "section",
    "category": "section",
    "catergory": "section",
    "group": "section",
    "type": "section",

    # Title
    "title": "title",
    "subject": "title",
    "headline": "title",
    "event title": "title",

    # Text/body
    "text": "text",
    "body": "text",
    "description": "text",
    "content": "text",
    "details": "text",

    # Image
    "image": "image",
    "image path": "image",
    "imagepath": "image",
    "img": "image",
    "photo": "image",

    # Notes
    "notes": "notes",
}

# Locate Events.csv in expected locations
EVENTS_CSV_PATH: Path | None = None
for candidate in [
    BASE_DIR / "Events.csv",
    BASE_DIR / "events.csv",
    COMPILER_DIR / "Events.csv",
    COMPILER_DIR / "events.csv",
    SCRIPT_DIR / "Events.csv",
    SCRIPT_DIR / "events.csv",
]:
    if candidate.exists():
        EVENTS_CSV_PATH = candidate
        break


# ---------- Date parsing and CLI ----------

def parse_date(value) -> date | None:
    """Parse various date formats into a date object, or return None."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None

    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def valid_issue_date(value: str) -> date:
    """Argparse type for issue date."""
    parsed = parse_date(value)
    if parsed is None:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use MM/DD/YY, MM/DD/YYYY, or YYYY-MM-DD."
        )
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess Chuck's List Events into events_data.csv from Events.csv."
    )
    parser.add_argument(
        "--issue-date",
        type=valid_issue_date,
        default=date.today(),
        help="Include rows relevant to this issue date.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print included/excluded rows with parsed dates.",
    )
    return parser.parse_args()


# ---------- Text normalization ----------

def normalize_unicode_text(text: str) -> str:
    """Normalize mojibake and Unicode artifacts into readable text."""
    for bad, good in COMMON_TEXT_REPAIRS.items():
        text = text.replace(bad, good)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def clean_cell_text(value) -> str:
    """Clean spreadsheet cell text, preserving paragraph structure."""
    if value is None:
        return ""

    text = str(value)
    if text.lower() == "nan":
        return ""

    text = normalize_unicode_text(text)

    lines = [line.rstrip() for line in text.split("\n")]
    out_lines: list[str] = []
    blank_run = 0

    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                out_lines.append("")
        else:
            blank_run = 0
            out_lines.append(line)

    return "\n".join(out_lines).strip()


def normalize_image(value: str) -> str:
    """Normalize image paths to consistent relative references."""
    value = clean_cell_text(value).replace("\\", "/")
    if not value:
        return ""

    # Allow fully-qualified and inline URLs as-is
    if value.lower().startswith(("http://", "https://", "cid:", "data:")):
        return value

    # Support "img1 & img2" style multi-images
    parts = [part.strip() for part in value.split("&")]
    normalized: list[str] = []

    for part in parts:
        if not part:
            continue
        if part.lower().startswith(("http://", "https://", "cid:", "data:", "images/")):
            normalized.append(part)
        else:
            # Normalize to Images/<filename>
            normalized.append(f"Images/{part.split('/')[-1]}")

    return " & ".join(normalized)


# ---------- Header normalization and CSV loading ----------

def normalize_header(value: str) -> str:
    """Normalize column header names into canonical field names."""
    cleaned = " ".join(str(value or "").strip().lower().split())
    return HEADER_ALIASES.get(cleaned, cleaned)


def load_event_records_from_csv() -> list[dict]:
    """Load event records from a true CSV table, normalizing headers and dates."""
    if not EVENTS_CSV_PATH or not EVENTS_CSV_PATH.exists():
        raise FileNotFoundError("Events.csv was not found in expected locations.")

    print(f"Reading events CSV: {EVENTS_CSV_PATH}")

    records: list[dict] = []
    with open(EVENTS_CSV_PATH, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=",")
        original_fields = reader.fieldnames or []
        normalized_fields = [normalize_header(col) for col in original_fields]

        print(f"Original headers: {original_fields}")
        print(f"Normalized headers: {normalized_fields}")

        # Map original header names to normalized names
        header_map = dict(zip(original_fields, normalized_fields))

        for idx, row in enumerate(reader, start=2):  # 1-based + header row
            normalized_row: dict = {
                "_rownum": idx,
            }

            for orig_name, value in row.items():
                norm_name = header_map.get(orig_name, orig_name)
                if norm_name in {"received", "starts", "ends"}:
                    normalized_row[norm_name] = parse_date(value)
                    normalized_row[f"_{norm_name}_raw"] = "" if value is None else str(value)
                else:
                    normalized_row[norm_name] = clean_cell_text(value)

            records.append(normalized_row)

    return records


# ---------- Inclusion logic and output building ----------

def event_matches_issue(row: dict, issue_date: date) -> tuple[bool, str]:
    """
    Determine whether an event row should be included for the given issue date.

    Final simple rule (Events only):

        Include if:
            starts <= issue_date <= ends

        Otherwise exclude.

    We ignore 'received' for Events; Bulletins can use a different rule.
    """
    starts = row.get("starts")
    ends = row.get("ends")

    if starts is None or ends is None:
        return False, "missing starts or ends"

    if starts > issue_date:
        return False, f"starts after issue date ({starts.isoformat()})"

    if ends < issue_date:
        return False, f"expired before issue date ({ends.isoformat()})"

    return True, (
        f"starts <= issue date ({starts.isoformat()} <= {issue_date.isoformat()}) "
        f"and ends >= issue date ({ends.isoformat()})"
    )


def format_date_output(value: date | None) -> str:
    return value.isoformat() if value else ""


def build_event_rows(records: list[dict], issue_date: date, debug: bool = False) -> list[dict]:
    """
    Build normalized event rows ready to write to events_data.csv.

    Applies date filters, content checks, and text/image normalization.
    """
    output: list[dict] = []
    included: list[dict] = []
    excluded: list[dict] = []

    for row in records:
        section = clean_cell_text(row.get("section", ""))
        title = clean_cell_text(row.get("title", ""))
        text = clean_cell_text(row.get("text", ""))
        image = normalize_image(row.get("image", ""))

        matches, reason = event_matches_issue(row, issue_date)

        debug_row = {
            "row": row.get("_rownum"),
            "received": format_date_output(row.get("received")),
            "starts": format_date_output(row.get("starts")),
            "ends": format_date_output(row.get("ends")),
            "section": section,
            "title": title,
            "reason": reason,
        }

        if not matches:
            excluded.append(debug_row)
            continue

        # Require at least some meaningful content
        if not title and not text and not image:
            debug_row["reason"] = "included by date but empty content"
            excluded.append(debug_row)
            continue

        output.append({
            "section": section or "Single Events",
            "title": title or "Untitled Event",
            "text": text,
            "image": image,
            "starts": format_date_output(row.get("starts")),
            "ends": format_date_output(row.get("ends")),
        })
        included.append(debug_row)

    if debug:
        print("\n=== INCLUDED ROWS ===")
        for row in included:
            print(
                f"row {row['row']:>3} | "
                f"received={row['received'] or '-':<10} | "
                f"starts={row['starts'] or '-':<10} | "
                f"ends={row['ends'] or '-':<10} | "
                f"{row['section']:<24} | {row['title'][:50]} | {row['reason']}"
            )

        print("\n=== EXCLUDED ROWS ===")
        for row in excluded:
            print(
                f"row {row['row']:>3} | "
                f"received={row['received'] or '-':<10} | "
                f"starts={row['starts'] or '-':<10} | "
                f"ends={row['ends'] or '-':<10} | "
                f"{row['reason']} | {row['title'][:50]}"
            )

    return output


# ---------- Output writing ----------

def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write events_data.csv as comma-separated values."""
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter=",",
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


# ---------- Main preprocess pipeline ----------

def preprocess_events(issue_date: date, debug: bool = False) -> int:
    event_records = load_event_records_from_csv()
    print(f"Event records loaded: {len(event_records)}")

    event_rows = build_event_rows(event_records, issue_date, debug=debug)
    print(f"Event rows selected: {len(event_rows)}")

    # Sort selected rows chronologically by starts, then ends, then section/title
    def sort_key(r: dict) -> tuple:
        # Parse back from ISO strings for robust ordering
        s = parse_date(r.get("starts"))
        e = parse_date(r.get("ends"))
        return (s or date.min, e or date.min, r.get("section", ""), r.get("title", ""))

    event_rows.sort(key=sort_key)

    write_csv(EVENTS_OUTPUT_PATH, event_rows, EVENTS_OUTPUT_FIELDS)
    print(f"Wrote events file: {EVENTS_OUTPUT_PATH}")

    return len(event_rows)


def main() -> int:
    args = parse_args()

    print(f"SCRIPT_DIR: {SCRIPT_DIR}")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"COMPILER_DIR: {COMPILER_DIR}")
    print(f"EVENTS_CSV_PATH: {EVENTS_CSV_PATH}")
    print(f"EVENTS_OUTPUT_PATH: {EVENTS_OUTPUT_PATH}")
    print(f"ISSUE_DATE: {args.issue_date.isoformat()}")

    event_count = preprocess_events(issue_date=args.issue_date, debug=args.debug)

    print(f"Events written: {event_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Preprocess failed: {exc}", file=sys.stderr)
        raise SystemExit(1)