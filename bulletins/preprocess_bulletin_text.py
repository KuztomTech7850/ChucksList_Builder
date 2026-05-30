# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import cast, Any

try:
    import pandas as pd
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pandas\n"
        "Install with: py -m pip install pandas odfpy"
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
COMPILER_DIR = SCRIPT_DIR.parent
BASE_DIR = COMPILER_DIR.parent

BULLETINS_OUTPUT_PATH = COMPILER_DIR / "bulletins" / "bulletins_data.csv"

BULLETIN_SHEET_CANDIDATES = ["Bulletin", "Bulletins", "bulletin", "bulletins"]
BULLETINS_OUTPUT_FIELDS = ["section", "title", "text", "image"]

HEADER_ALIASES = {
    "received": "received",
    "received date": "received",
    "starts": "starts",
    "start": "starts",
    "start date": "starts",
    "ends": "ends",
    "end": "ends",
    "end date": "ends",
    "expires": "ends",
    "expiration": "ends",
    "section": "section",
    "category": "section",
    "catergory": "section",
    "group": "section",
    "type": "section",
    "title": "title",
    "subject": "title",
    "headline": "title",
    "post title": "title",
    "text": "text",
    "body": "text",
    "description": "text",
    "content": "text",
    "details": "text",
    "image": "image",
    "image path": "image",
    "imagepath": "image",
    "img": "image",
    "photo": "image",
    "notes": "notes",
}

COMMON_TEXT_REPAIRS = {
    "\u00a0": " ",
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


def find_first_existing(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


WORKBOOK_PATH = find_first_existing([
    BASE_DIR / "Chucks-list-MASTER.ods",
    COMPILER_DIR / "Chucks-list-MASTER.ods",
    SCRIPT_DIR / "Chucks-list-MASTER.ods",
])

BULLETINS_CSV_PATH = find_first_existing([
    BASE_DIR / "Bulletins.csv",
    BASE_DIR / "bulletins.csv",
    COMPILER_DIR / "Bulletins.csv",
    COMPILER_DIR / "bulletins.csv",
    SCRIPT_DIR / "Bulletins.csv",
    SCRIPT_DIR / "bulletins.csv",
])


def parse_date(value) -> date | None:
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
    parsed = parse_date(value)
    if parsed is None:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use MM/DD/YY, MM/DD/YYYY, or YYYY-MM-DD."
        )
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess Chuck's List Bulletins into bulletins_data.csv."
    )
    parser.add_argument(
        "--issue-date",
        type=valid_issue_date,
        default=date.today(),
        help="Primary filter date.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print included/excluded rows with parsed dates.",
    )
    return parser.parse_args()


def normalize_header(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().lower().split())
    return HEADER_ALIASES.get(cleaned, cleaned)


def normalize_unicode_text(text: str) -> str:
    for bad, good in COMMON_TEXT_REPAIRS.items():
        text = text.replace(bad, good)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def clean_cell_text(value) -> str:
    if value is None:
        return ""

    text = str(value)
    if text.lower() == "nan":
        return ""

    text = normalize_unicode_text(text)

    lines = [line.rstrip() for line in text.split("\n")]
    out_lines = []
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
    value = clean_cell_text(value).replace("\\", "/")
    if not value:
        return ""

    if value.lower().startswith(("http://", "https://", "cid:", "data:")):
        return value

    parts = [part.strip() for part in value.split("&")]
    normalized = []

    for part in parts:
        if not part:
            continue
        if part.lower().startswith(("http://", "https://", "cid:", "data:", "images/")):
            normalized.append(part)
        else:
            normalized.append(f"Images/{part.split('/')[-1]}")

    return " & ".join(normalized)


def score_sheet_columns(columns: set[str], required: set[str]) -> int:
    return sum(1 for col in required if col in columns)


def find_sheet_name(xls: "pd.ExcelFile", candidates: list[str], required: set[str]) -> str:
    lower_map = {str(name).lower(): name for name in xls.sheet_names}

    for candidate in candidates:
        match = lower_map.get(str(candidate).lower())
        if match:
            return str(match)

    best_name: str | None = None
    best_score = -1

    for sheet_name in xls.sheet_names:
        preview = pd.read_excel(xls, sheet_name=sheet_name, engine="odf")
        normalized = {normalize_header(str(col)) for col in preview.columns}
        score = score_sheet_columns(normalized, required)
        if score > best_score:
            best_score = score
            best_name = str(sheet_name)

    if best_name is None:
        raise ValueError("Unable to identify Bulletin worksheet.")

    return best_name


def read_csv_stable(path: Path) -> "pd.DataFrame":
    attempts = [
        {"sep": ",", "engine": "python"},
        {"sep": "\t", "engine": "python"},
        {"sep": ";", "engine": "python"},
        {"sep": "|", "engine": "python"},
    ]

    last_error = None

    for opts in attempts:
        try:
            df = pd.read_csv(
                path,
                sep=opts["sep"],
                engine=cast(Any, opts["engine"]),
                encoding="utf-8-sig",
                dtype=str,
                keep_default_na=False,
            )

            normalized_cols = [normalize_header(col) for col in df.columns]
            score = sum(
                1
                for col in normalized_cols
                if col in {"received", "starts", "ends", "section", "title", "text", "image", "notes"}
            )

            if score >= 3:
                return df
        except Exception as exc:
            last_error = exc

    raise ValueError(f"Unable to parse bulletin CSV reliably: {path}\nLast error: {last_error}")


def read_source_dataframe() -> tuple["pd.DataFrame", str]:
    if BULLETINS_CSV_PATH and BULLETINS_CSV_PATH.exists():
        print(f"Reading from CSV: {BULLETINS_CSV_PATH}")
        df = read_csv_stable(BULLETINS_CSV_PATH)
        print(f"Columns detected: {list(df.columns)}")
        return df, "csv"

    if WORKBOOK_PATH and WORKBOOK_PATH.exists():
        print(f"Reading workbook: {WORKBOOK_PATH}")
        xls = pd.ExcelFile(WORKBOOK_PATH, engine="odf")
        print(f"Workbook sheets found: {xls.sheet_names}")
        bulletin_sheet = find_sheet_name(
            xls,
            BULLETIN_SHEET_CANDIDATES,
            required={"section", "title", "text"},
        )
        print(f"Bulletin sheet selected: {bulletin_sheet}")
        df = pd.read_excel(xls, sheet_name=bulletin_sheet, engine="odf", dtype=str)
        print(f"Columns detected: {list(df.columns)}")
        return df, "ods"

    raise FileNotFoundError(
        "Neither source file was found.\n"
        f"Checked bulletin CSV candidates in: {BASE_DIR}, {COMPILER_DIR}, {SCRIPT_DIR}\n"
        f"Checked workbook candidates in: {BASE_DIR}, {COMPILER_DIR}, {SCRIPT_DIR}"
    )


def load_sheet_records() -> list[dict]:
    df, source_type = read_source_dataframe()
    df.columns = [normalize_header(col) for col in df.columns]
    print(f"Normalized columns: {list(df.columns)}")

    records = []
    for rownum, (_, row) in enumerate(df.iterrows(), start=2):
        record = {
            "_rownum": rownum,
            "_source_type": source_type,
        }
        for column in df.columns:
            value = row.get(column, "")
            if column in {"received", "starts", "ends"}:
                record[column] = parse_date(value)
                record[f"_{column}_raw"] = "" if value is None else str(value)
            else:
                record[column] = clean_cell_text(value)
        records.append(record)

    return records


def bulletin_matches_issue(row: dict, issue_date: date) -> tuple[bool, str]:
    starts = row.get("starts")
    received = row.get("received")
    ends = row.get("ends")

    if starts is not None:
        if starts <= issue_date:
            return True, f"starts <= issue date ({starts.isoformat()})"
        return False, f"starts after issue date ({starts.isoformat()})"

    if received is not None:
        if received <= issue_date:
            return True, f"received <= issue date ({received.isoformat()})"
        return False, f"received after issue date ({received.isoformat()})"

    if ends is not None:
        if ends >= issue_date:
            return True, f"ends >= issue date ({ends.isoformat()})"
        return False, f"expired before issue date ({ends.isoformat()})"

    return False, "missing starts, received, and ends"


def build_bulletin_rows(records: list[dict], issue_date: date, debug: bool = False) -> list[dict]:
    output = []
    included = []
    excluded = []

    for row in records:
        section = clean_cell_text(row.get("section", ""))
        title = clean_cell_text(row.get("title", ""))
        text = clean_cell_text(row.get("text", ""))
        image = normalize_image(row.get("image", ""))

        matches, reason = bulletin_matches_issue(row, issue_date)

        received = row.get("received")
        starts = row.get("starts")
        ends = row.get("ends")

        debug_row = {
            "row": row.get("_rownum"),
            "received": received.isoformat() if received else "",
            "starts": starts.isoformat() if starts else "",
            "ends": ends.isoformat() if ends else "",
            "section": section,
            "title": title,
            "reason": reason,
        }

        if not matches:
            excluded.append(debug_row)
            continue

        if not title and not text and not image:
            debug_row["reason"] = "included by date but empty content"
            excluded.append(debug_row)
            continue

        output.append({
            "section": section or "Community Announcements",
            "title": title or "Untitled Bulletin",
            "text": text,
            "image": image,
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
                f"{row['section']:<28} | {row['title'][:50]} | {row['reason']}"
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


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_tsv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
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


def preprocess_bulletins(issue_date: date, debug: bool = False) -> int:
    bulletin_records = load_sheet_records()
    print(f"Bulletin records loaded: {len(bulletin_records)}")

    bulletin_rows = build_bulletin_rows(bulletin_records, issue_date, debug=debug)
    print(f"Bulletin rows selected: {len(bulletin_rows)}")

    write_tsv(BULLETINS_OUTPUT_PATH, bulletin_rows, BULLETINS_OUTPUT_FIELDS)
    print(f"Wrote bulletins file: {BULLETINS_OUTPUT_PATH}")

    return len(bulletin_rows)


def main() -> int:
    args = parse_args()

    print(f"SCRIPT_DIR: {SCRIPT_DIR}")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"COMPILER_DIR: {COMPILER_DIR}")
    print(f"WORKBOOK_PATH: {WORKBOOK_PATH}")
    print(f"BULLETINS_CSV_PATH: {BULLETINS_CSV_PATH}")
    print(f"BULLETINS_OUTPUT_PATH: {BULLETINS_OUTPUT_PATH}")
    print(f"ISSUE_DATE: {args.issue_date.isoformat()}")

    bulletin_count = preprocess_bulletins(issue_date=args.issue_date, debug=args.debug)

    print(f"Bulletins written: {bulletin_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Preprocess failed: {exc}", file=sys.stderr)
        raise SystemExit(1)