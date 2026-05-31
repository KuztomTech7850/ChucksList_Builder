"""
events/preprocess_events_text.py
Role: Read raw Events.csv, validate, filter by issue_date, write events_data.csv
Pipeline stage: PREPROCESS
Called by: Chucks_List_Builder.py via subprocess

CSV column contract (actual Events.csv headers):
  Received, Starts, Expires, Section, Title, Text, Image, notes

Date formats accepted: YYYY-MM-DD and MM/DD/YY
Inclusion rule: Starts <= issue_date <= Expires

Preprocess responsibilities:
  - normalize headers through canonical alias map
  - normalize event section labels
  - preserve paragraph breaks, reduce junk whitespace
  - auto-fix safe link issues (mailto:, https://www.)
  - BLOCK on bare URLs (Zoho click-tracking requires markdown links)
  - WARN on bare emails (compiler can safely linkify, but markdown preferred)
  - stop on unresolved blocking errors
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR   = SCRIPT_DIR.parent
INPUT_CSV  = PROJ_DIR / "Events.csv"
OUTPUT_CSV = SCRIPT_DIR / "events_data.csv"

OUT_COLS = ["Title", "Body", "Starts", "Ends", "Section", "Image"]

SECTION_ORDER = [
    "Single Events",
    "Multiple Events",
    "Recurring Events",
]

HEADER_ALIASES = {
    "received":    "Received",
    "starts":      "Starts",
    "start":       "Starts",
    "start date":  "Starts",
    "expires":     "Expires",
    "ends":        "Expires",
    "end":         "Expires",
    "end date":    "Expires",
    "section":     "Section",
    "category":    "Section",
    "title":       "Title",
    "name":        "Title",
    "text":        "Text",
    "body":        "Text",
    "description": "Text",
    "image":       "Image",
    "image file":  "Image",
    "notes":       "notes",
}

SECTION_ALIASES = {
    "single":           "Single Events",
    "single event":     "Single Events",
    "single events":    "Single Events",
    "multiple":         "Multiple Events",
    "multiple event":   "Multiple Events",
    "multiple events":  "Multiple Events",
    "recurring":        "Recurring Events",
    "recurring event":  "Recurring Events",
    "recurring events": "Recurring Events",
    "weekly":           "Recurring Events",
    "monthly":          "Recurring Events",
}

REQUIRED_CANONICAL_COLS = ["Starts", "Expires", "Title", "Text"]

DATE_RE_ISO   = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")

EMAIL_RE        = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
INLINE_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL_RE          = re.compile(r"https?://[^\s<>\"]+")
WWW_TARGET_RE   = re.compile(r"^www\.[^\s)]+$", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")
TRAILING_PUNCTUATION = ".,;:!?)}]"

SMART_CHAR_MAP = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201C": '"',
    "\u201D": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u00A0": " ",
})


@dataclass
class Issue:
    level: str   # AUTO-FIX | WARN | ERROR
    message: str


def emit(issue: Issue) -> None:
    print(f"  [{issue.level}] {issue.message}", file=sys.stderr)


def parse_date(val: str, row_num: int, field: str) -> date | None:
    raw = (val or "").strip()
    if not raw:
        emit(Issue("WARN",
            f"Row {row_num}: field '{field}' is empty. "
            "Fix: enter a date in YYYY-MM-DD or MM/DD/YY. Item skipped."))
        return None
    if DATE_RE_ISO.match(raw):
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            emit(Issue("WARN",
                f"Row {row_num}: field '{field}' has invalid value '{raw}'. "
                f"Fix: use a real YYYY-MM-DD date. Error: {exc}. Item skipped."))
            return None
    m = DATE_RE_SHORT.match(raw)
    if m:
        try:
            return date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError as exc:
            emit(Issue("WARN",
                f"Row {row_num}: field '{field}' has invalid value '{raw}'. "
                f"Fix: use a real MM/DD/YY date. Error: {exc}. Item skipped."))
            return None
    emit(Issue("WARN",
        f"Row {row_num}: field '{field}' has unrecognized date '{raw}'. "
        "Fix: use YYYY-MM-DD or MM/DD/YY. Item skipped."))
    return None


def normalize_headers(fieldnames: list[str]) -> tuple[dict[str, str], list[str]]:
    canonical_to_raw: dict[str, str] = {}
    unknown: list[str] = []
    for raw in fieldnames:
        key = (raw or "").strip().lower()
        canonical = HEADER_ALIASES.get(key)
        if canonical:
            if canonical not in canonical_to_raw:
                canonical_to_raw[canonical] = raw
        else:
            unknown.append(raw)
    return canonical_to_raw, unknown


def get_value(row: dict[str, str], header_map: dict[str, str], canonical: str) -> str:
    raw_key = header_map.get(canonical)
    if not raw_key:
        return ""
    return (row.get(raw_key) or "").strip()


def normalize_section(raw_section: str, row_num: int, title: str) -> tuple[str | None, list[Issue]]:
    issues: list[Issue] = []
    raw = (raw_section or "").strip()
    if not raw:
        issues.append(Issue("WARN",
            f"Row {row_num}: field 'Section' is empty for '{title}'. "
            "Defaulting to 'Single Events'."))
        return "Single Events", issues
    lowered = raw.lower()
    canonical = SECTION_ALIASES.get(lowered, raw)
    if canonical not in SECTION_ORDER:
        issues.append(Issue("ERROR",
            f"Row {row_num}: field 'Section' has unknown value '{raw}' for '{title}'. "
            f"Fix: use one of: {', '.join(SECTION_ORDER)}. Item skipped."))
        return None, issues
    if canonical != raw:
        issues.append(Issue("AUTO-FIX",
            f"Row {row_num}: field 'Section' normalized from '{raw}' to '{canonical}' for '{title}'."))
    return canonical, issues


def clean_body(text: str) -> str:
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    body = body.translate(SMART_CHAR_MAP)
    lines = body.split("\n")
    cleaned = [re.sub(r"[ \t]+", " ", line).rstrip() for line in lines]
    body = "\n".join(cleaned)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def split_trailing_punctuation(token: str) -> tuple[str, str]:
    clean = token.rstrip(TRAILING_PUNCTUATION)
    return clean, token[len(clean):]


def looks_like_email_target(target: str) -> bool:
    return bool(EMAIL_RE.fullmatch(target.strip()))


def looks_like_www_target(target: str) -> bool:
    return bool(WWW_TARGET_RE.fullmatch(target.strip()))


def auto_fix_markdown_links(body: str, row_num: int, title: str) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []

    def repl(match: re.Match[str]) -> str:
        label  = match.group(1).strip()
        target = match.group(2).strip()
        fixed  = target
        if looks_like_email_target(target):
            fixed = f"mailto:{target}"
            issues.append(Issue("AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target "
                f"'{target}' to '{fixed}'."))
        elif looks_like_www_target(target):
            fixed = f"https://{target}"
            issues.append(Issue("AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target "
                f"'{target}' to '{fixed}'."))
        return f"[{label}]({fixed})"

    return MARKDOWN_LINK_RE.sub(repl, body), issues


def check_bracket_balance(body: str, row_num: int, title: str) -> list[Issue]:
    issues: list[Issue] = []
    if body.count("[") != body.count("]"):
        issues.append(Issue("ERROR",
            f"Row {row_num}: field 'Text' for '{title}' has unbalanced square brackets. "
            "Fix: repair markdown link text like [label](target)."))
    if body.count("(") != body.count(")"):
        issues.append(Issue("ERROR",
            f"Row {row_num}: field 'Text' for '{title}' has unbalanced parentheses. "
            "Fix: repair markdown link targets like [label](target)."))
    return issues


def analyze_links(body: str, row_num: int, title: str) -> list[Issue]:
    issues: list[Issue] = []
    lower = body.lower()

    if "href=" in lower or "<a " in lower:
        issues.append(Issue("ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains raw HTML links. "
            "Fix: use plain text or markdown links only."))

    issues.extend(check_bracket_balance(body, row_num, title))

    # Validate each markdown link's label and target
    for label, target in MARKDOWN_LINK_RE.findall(body):
        label  = label.strip()
        target = target.strip()
        if URL_RE.fullmatch(label):
            issues.append(Issue("ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw URL as markdown "
                f"label '[{label}]({target})'. Fix: replace the label with descriptive text."))
        if INLINE_EMAIL_RE.fullmatch(label):
            issues.append(Issue("ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw email as markdown "
                f"label '[{label}]({target})'. Fix: replace the label with descriptive text."))
        if not (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("mailto:")
            or looks_like_email_target(target)
            or looks_like_www_target(target)
        ):
            issues.append(Issue("ERROR",
                f"Row {row_num}: field 'Text' for '{title}' has markdown target '{target}' "
                "without a usable scheme. Fix: use https://, http://, mailto:, or a plain email."))

    # Mask valid markdown before scanning for bare URLs/emails
    masked = MARKDOWN_LINK_RE.sub("[LINK]", body)

    # Bare URLs are blocking — Zoho click-tracking requires markdown links
    for match in URL_RE.finditer(masked):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)
        if trailing:
            issues.append(Issue("ERROR",
                f"Row {row_num}: field 'Text' for '{title}' contains URL '{token}' with "
                f"trailing punctuation. Fix: move '{trailing}' outside the URL so the link is '{clean}'."))
        issues.append(Issue("ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains bare URL '{clean}'. "
            "Fix: convert to markdown, e.g. [More details](https://example.com)."))

    # Bare emails are non-blocking — compiler can linkify, but markdown is preferred
    for match in INLINE_EMAIL_RE.finditer(masked):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)
        if trailing:
            issues.append(Issue("WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains email '{token}' with "
                f"trailing punctuation. Fix: move '{trailing}' outside the address."))
        else:
            issues.append(Issue("WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains bare email '{clean}'. "
                "Review: compiler will linkify, but [Name](mailto:email) is preferred."))

    return issues


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
            header_map, unknown_headers = normalize_headers(reader.fieldnames)
            missing = [col for col in REQUIRED_CANONICAL_COLS if col not in header_map]
            if missing:
                print(
                    f"ERROR: Events.csv missing required columns: {', '.join(missing)}\n"
                    f"  Found: {', '.join(reader.fieldnames)}\n"
                    "  Fix: Re-export from Chucks-list-MASTER.ods.",
                    file=sys.stderr,
                )
                return 1
            for unk in unknown_headers:
                emit(Issue("WARN",
                    f"Header '{unk}' is not mapped to a canonical events field. "
                    "Confirm it is intentionally unused or add it to HEADER_ALIASES."))
            all_rows = list(reader)
    except UnicodeDecodeError:
        print("ERROR: Events.csv is not UTF-8. Re-export with UTF-8 encoding.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR reading Events.csv: {exc}", file=sys.stderr)
        return 1

    passing: list[dict[str, str]] = []
    skipped = 0
    excluded_by_date = 0
    total_autofix = 0
    total_warn = 0
    total_error = 0
    blocking_errors_found = False

    for i, row in enumerate(all_rows, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue

        row_issues: list[Issue] = []

        title       = get_value(row, header_map, "Title")
        section_raw = get_value(row, header_map, "Section")
        body_raw    = get_value(row, header_map, "Text")
        image       = get_value(row, header_map, "Image")
        starts_str  = get_value(row, header_map, "Starts")
        expires_str = get_value(row, header_map, "Expires")

        if not title:
            row_issues.append(Issue("ERROR",
                f"Row {i}: field 'Title' is empty. Fix: enter a title. Item skipped."))
            for issue in row_issues:
                emit(issue)
            total_error += 1
            skipped += 1
            blocking_errors_found = True
            continue

        starts  = parse_date(starts_str,  i, "Starts")
        expires = parse_date(expires_str, i, "Expires")
        if starts is None or expires is None:
            skipped += 1
            continue

        if starts > expires:
            row_issues.append(Issue("ERROR",
                f"Row {i}: date range invalid for '{title}'. "
                f"Starts='{starts_str}' is after Expires='{expires_str}'. "
                "Fix: correct the dates in Chucks-list-MASTER.ods. Item skipped."))
            for issue in row_issues:
                emit(issue)
            total_error += 1
            skipped += 1
            blocking_errors_found = True
            continue

        if not (starts <= issue_date <= expires):
            if issue_date < starts:
                emit(Issue("WARN",
                    f"Row {i}: '{title}' excluded — issue date '{issue_date_str}' is before "
                    f"Starts '{starts_str}'."))
            else:
                emit(Issue("WARN",
                    f"Row {i}: '{title}' excluded — issue date '{issue_date_str}' is after "
                    f"Expires '{expires_str}'."))
            excluded_by_date += 1
            continue

        section, section_issues = normalize_section(section_raw, i, title)
        row_issues.extend(section_issues)
        if section is None:
            for issue in row_issues:
                emit(issue)
            total_autofix += sum(1 for x in row_issues if x.level == "AUTO-FIX")
            total_warn    += sum(1 for x in row_issues if x.level == "WARN")
            total_error   += sum(1 for x in row_issues if x.level == "ERROR")
            skipped += 1
            blocking_errors_found = True
            continue

        body = clean_body(body_raw)
        if not body:
            row_issues.append(Issue("WARN",
                f"Row {i}: field 'Text' is empty for '{title}'. "
                "Fix: add event text. Item kept, but output may look empty."))

        body, autofix_issues = auto_fix_markdown_links(body, i, title)
        row_issues.extend(autofix_issues)

        link_issues = analyze_links(body, i, title)
        row_issues.extend(link_issues)

        if image and " " in image and not image.startswith(("http://", "https://")):
            row_issues.append(Issue("WARN",
                f"Row {i}: field 'Image' for '{title}' has value '{image}' containing spaces. "
                "Fix: use a clean filename with no spaces."))

        for issue in row_issues:
            emit(issue)

        total_autofix += sum(1 for x in row_issues if x.level == "AUTO-FIX")
        total_warn    += sum(1 for x in row_issues if x.level == "WARN")
        row_error_count = sum(1 for x in row_issues if x.level == "ERROR")
        total_error += row_error_count

        if row_error_count:
            skipped += 1
            blocking_errors_found = True
            continue

        passing.append({
            "Title":   title,
            "Body":    body,
            "Starts":  starts_str,
            "Ends":    expires_str,
            "Section": section,
            "Image":   image,
        })

    if blocking_errors_found:
        print(
            f"ERROR: Events preprocess stopped due to unresolved content errors. "
            f"auto-fix={total_autofix}, warnings={total_warn}, errors={total_error}, "
            f"skipped={skipped}, excluded_by_date={excluded_by_date}.",
            file=sys.stderr,
        )
        print(
            "Fix the ERROR items in Events.csv / Chucks-list-MASTER.ods and re-run preprocess.",
            file=sys.stderr,
        )
        return 1

    try:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=OUT_COLS, extrasaction="ignore", quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(passing)
    except Exception as exc:
        print(f"ERROR writing {OUTPUT_CSV}: {exc}", file=sys.stderr)
        return 1

    print(
        f"  [OK] Events preprocess: {len(passing)} items -> {OUTPUT_CSV} "
        f"(auto-fix={total_autofix}, warnings={total_warn}, skipped={skipped}, "
        f"excluded_by_date={excluded_by_date}, issue_date={issue_date_str})"
    )
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Preprocess Chuck's List events CSV.")
    p.add_argument("--issue-date", required=True, help="Issue date YYYY-MM-DD")
    args = p.parse_args()
    sys.exit(preprocess_events(args.issue_date))
