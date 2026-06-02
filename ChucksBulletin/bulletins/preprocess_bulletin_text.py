"""
ChucksBulletin/bulletins/preprocess_bulletin_text.py
Role: Read raw Bulletins.csv, validate, filter by issue_date, write bulletins_data.csv
Pipeline stage: PREPROCESS
Called by: Chucks_List_Builder.py via subprocess

CSV column contract (expected / accepted aliases):
  Received, Expires, Section, Title, Text, Image, notes

Accepted date formats:
  - YYYY-MM-DD
  - MM/DD/YY
  - M/D/YYYY

Inclusion rule:
  Received <= issue_date <= Expires

Preprocess responsibilities:
  - normalize headers through one canonical alias map
  - normalize bulletin section labels
  - preserve intentional paragraph breaks while reducing junk whitespace
  - auto-fix safe link issues
  - stop on unresolved blocking content/link errors
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR = SCRIPT_DIR.parent
INPUT_CSV = SCRIPT_DIR / "Bulletins.csv"
OUTPUT_CSV = SCRIPT_DIR / "bulletins_data.csv"

OUT_COLS = ["Title", "Body", "Section", "Received", "Expires", "Image"]

SECTION_ORDER = [
    "Urgent Bulletins",
    "Housing Opportunities",
    "Swap Market",
    "Local Services & Help",
    "Community Announcements",
]

HEADER_ALIASES = {
    "received": "Received",
    "expires": "Expires",
    "section": "Section",
    "title": "Title",
    "text": "Text",
    "body": "Text",
    "description": "Text",
    "image": "Image",
    "image file": "Image",
    "notes": "notes",
}

SECTION_ALIASES = {
    "urgent": "Urgent Bulletins",
    "urgent bulletin": "Urgent Bulletins",
    "urgent bulletins": "Urgent Bulletins",
    "housing": "Housing Opportunities",
    "housing opportunity": "Housing Opportunities",
    "housing opportunities": "Housing Opportunities",
    "swap": "Swap Market",
    "swap market": "Swap Market",
    "services": "Local Services & Help",
    "service": "Local Services & Help",
    "local services": "Local Services & Help",
    "local services & help": "Local Services & Help",
    "community": "Community Announcements",
    "community announcement": "Community Announcements",
    "community announcements": "Community Announcements",
    "announcement": "Community Announcements",
    "announcements": "Community Announcements",
}

DATE_RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
DATE_RE_LONG = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
INLINE_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s<>\"]+")
WWW_TARGET_RE = re.compile(r"^www\.[^\s)]+$", re.IGNORECASE)
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

REQUIRED_CANONICAL_COLS = ["Received", "Expires", "Section", "Title", "Text"]


@dataclass
class Issue:
    level: str   # AUTO-FIX, WARN, ERROR
    message: str


def emit(issue: Issue) -> None:
    print(f"  [{issue.level}] {issue.message}", file=sys.stderr)


from datetime import date

def parse_date(val: str, row_num: int, field: str) -> date | None:
    raw = (val or "").strip()
    if not raw:
        emit(Issue(
            "WARN",
            f"Row {row_num}: field '{field}' is empty. Raw value: '{raw}'. "
            "Fix: enter a date in YYYY-MM-DD or MM/DD/YY. Item skipped."
        ))
        return None

    if DATE_RE_ISO.match(raw):
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' has invalid value '{raw}'. "
                f"Fix: use a real YYYY-MM-DD date. Python error: {exc}. Item skipped."
            ))
            return None

    short_match = DATE_RE_SHORT.match(raw)
    if short_match:
        try:
            return date(
                2000 + int(short_match.group(3)),
                int(short_match.group(1)),
                int(short_match.group(2)),
            )
        except ValueError as exc:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' has invalid value '{raw}'. "
                f"Fix: use a real M/D/YY date. Python error: {exc}. Item skipped."
            ))
            return None

    long_match = DATE_RE_LONG.match(raw)
    if long_match:
        try:
            return date(
                int(long_match.group(3)),
                int(long_match.group(1)),
                int(long_match.group(2)),
            )
        except ValueError as exc:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' has invalid value '{raw}'. "
                f"Fix: use a real M/D/YYYY date. Python error: {exc}. Item skipped."
            ))
            return None

    emit(Issue(
        "WARN",
        f"Row {row_num}: field '{field}' has unrecognized value '{raw}'. "
        "Fix: use YYYY-MM-DD, MM/DD/YY, or MM/DD/YYYY. Item skipped."
    ))
    return None

    emit(Issue(
        "WARN",
        f"Row {row_num}: field '{field}' has unrecognized date '{raw}'. "
        "Fix: use YYYY-MM-DD, MM/DD/YY, or M/D/YYYY. Item skipped."
    ))
    return None


def normalize_headers(fieldnames: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    canonical_to_raw: dict[str, str] = {}
    unknown_headers: list[str] = []

    for raw in fieldnames:
        key = (raw or "").strip().lower()
        canonical = HEADER_ALIASES.get(key)
        if canonical:
            if canonical not in canonical_to_raw:
                canonical_to_raw[canonical] = raw
        else:
            unknown_headers.append(raw)

    return canonical_to_raw, unknown_headers


def get_value(row: dict[str, str], header_map: dict[str, str], canonical: str) -> str:
    raw_key = header_map.get(canonical)
    if not raw_key:
        return ""
    return (row.get(raw_key) or "").strip()


def normalize_section(raw_section: str, row_num: int, title: str) -> tuple[str | None, list[Issue]]:
    issues: list[Issue] = []
    raw = (raw_section or "").strip()
    if not raw:
        issues.append(Issue(
            "WARN",
            f"Row {row_num}: field 'Section' is empty for '{title}'. Raw value: '{raw}'. "
            "Fix: enter a canonical section name. Defaulting to 'Community Announcements'."
        ))
        return "Community Announcements", issues

    lowered = raw.lower()
    canonical = SECTION_ALIASES.get(lowered, raw)

    if canonical not in SECTION_ORDER:
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Section' has unknown value '{raw}' for '{title}'. "
            f"Fix: use one of: {', '.join(SECTION_ORDER)}. Item skipped."
        ))
        return None, issues

    if canonical != raw:
        issues.append(Issue(
            "AUTO-FIX",
            f"Row {row_num}: field 'Section' normalized from '{raw}' to '{canonical}' for '{title}'."
        ))

    return canonical, issues


def clean_body(text: str) -> str:
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    body = body.translate(SMART_CHAR_MAP)

    lines = body.split("\n")
    cleaned_lines: list[str] = []
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line).rstrip()
        cleaned_lines.append(line)

    body = "\n".join(cleaned_lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def split_trailing_punctuation(token: str) -> tuple[str, str]:
    clean = token.rstrip(TRAILING_PUNCTUATION)
    trailing = token[len(clean):]
    return clean, trailing


def looks_like_email_target(target: str) -> bool:
    return bool(EMAIL_RE.fullmatch(target.strip()))


def looks_like_www_target(target: str) -> bool:
    return bool(WWW_TARGET_RE.fullmatch(target.strip()))


def auto_fix_markdown_links(body: str, row_num: int, title: str) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []

    def repl(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        target = match.group(2).strip()
        fixed_target = target

        if looks_like_email_target(target):
            fixed_target = f"mailto:{target}"
            issues.append(Issue(
                "AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target '{target}' "
                f"to '{fixed_target}'."
            ))
        elif looks_like_www_target(target):
            fixed_target = f"https://{target}"
            issues.append(Issue(
                "AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target '{target}' "
                f"to '{fixed_target}'."
            ))

        return f"[{label}]({fixed_target})"

    fixed = MARKDOWN_LINK_RE.sub(repl, body)
    return fixed, issues


def check_bracket_balance(body: str, row_num: int, title: str) -> list[Issue]:
    issues: list[Issue] = []

    if body.count("[") != body.count("]"):
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' has unbalanced square brackets. "
            "Fix: repair markdown link text like [label](target)."
        ))

    if body.count("(") != body.count(")"):
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' has unbalanced parentheses. "
            "Fix: repair markdown link targets like [label](target)."
        ))

    return issues


def analyze_links(body: str, row_num: int, title: str) -> list[Issue]:
    issues: list[Issue] = []
    lower = body.lower()

    if "href=" in lower or "<a " in lower:
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains raw HTML links. "
            "Fix: use plain text or markdown links only; compile will generate final anchors."
        ))

    issues.extend(check_bracket_balance(body, row_num, title))

    markdown_links = MARKDOWN_LINK_RE.findall(body)
    for label, target in markdown_links:
        label = label.strip()
        target = target.strip()

        if URL_RE.fullmatch(label):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw URL as markdown label '[{label}]({target})'. "
                "Fix: replace the visible label with descriptive text, e.g. [More details](https://example.com)."
            ))

        if INLINE_EMAIL_RE.fullmatch(label):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw email as markdown label '[{label}]({target})'. "
                "Fix: replace the visible label with descriptive text, e.g. [Email organizer](mailto:name@example.com)."
            ))

        if not (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("mailto:")
            or looks_like_email_target(target)
            or looks_like_www_target(target)
        ):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' has markdown target '{target}' without a usable scheme or email format. "
                "Fix: use https://example.com, http://example.com, mailto:name@example.com, or a plain email address."
            ))

    masked_body = MARKDOWN_LINK_RE.sub("[LINK]", body)

    for match in URL_RE.finditer(masked_body):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)

        if trailing:
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' contains URL '{token}' with trailing punctuation. "
                f"Fix: move '{trailing}' outside the URL so the link is '{clean}'."
            ))

        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains bare URL '{clean}'. "
            "Fix: convert it to markdown with descriptive text, e.g. [More details](https://example.com)."
        ))

    for match in INLINE_EMAIL_RE.finditer(masked_body):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)

        if trailing:
            issues.append(Issue(
                "WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains email '{token}' with trailing punctuation. "
                f"Fix: move '{trailing}' outside the address so the email is '{clean}'."
            ))
        else:
            issues.append(Issue(
                "WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains bare email '{clean}'. "
                "Review: compiler can safely linkify this, but markdown with descriptive text is preferred."
            ))

    return issues


def preprocess_bulletins(issue_date_str: str) -> int:
    try:
        issue_date = date.fromisoformat(issue_date_str)
    except ValueError:
        print(
            f"ERROR: --issue-date '{issue_date_str}' must be YYYY-MM-DD.",
            file=sys.stderr,
        )
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

            header_map, unknown_headers = normalize_headers(reader.fieldnames)
            missing = [col for col in REQUIRED_CANONICAL_COLS if col not in header_map]
            if missing:
                print(
                    f"ERROR: Bulletins.csv missing required columns: {', '.join(missing)}\n"
                    f"  Found: {', '.join(reader.fieldnames)}\n"
                    "  Fix: Re-export from Chucks-list-MASTER.ods with the expected bulletin columns.",
                    file=sys.stderr,
                )
                return 1

            for unknown in unknown_headers:
                emit(Issue(
                    "WARN",
                    f"Header '{unknown}' is not mapped to a canonical bulletin field. "
                    "Fix: confirm it is intentionally unused or add it to HEADER_ALIASES if needed."
                ))

            all_rows = list(reader)

    except UnicodeDecodeError:
        print("ERROR: Bulletins.csv is not UTF-8. Re-export with UTF-8 encoding.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR reading Bulletins.csv: {exc}", file=sys.stderr)
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

        title = get_value(row, header_map, "Title")
        section_raw = get_value(row, header_map, "Section")
        body_raw = get_value(row, header_map, "Text")
        image = get_value(row, header_map, "Image")
        received_str = get_value(row, header_map, "Received")
        expires_str = get_value(row, header_map, "Expires")

        if not title:
            row_issues.append(Issue(
                "ERROR",
                f"Row {i}: field 'Title' is empty. Raw value: '{title}'. "
                "Fix: enter a title. Item skipped."
            ))
            for issue in row_issues:
                emit(issue)
            total_error += sum(1 for x in row_issues if x.level == "ERROR")
            skipped += 1
            blocking_errors_found = True
            continue

        received = parse_date(received_str, i, "Received")
        expires = parse_date(expires_str, i, "Expires")
        if received is None or expires is None:
            skipped += 1
            continue

        if received > expires:
            row_issues.append(Issue(
                "ERROR",
                f"Row {i}: date range is invalid for '{title}'. "
                f"Received='{received_str}', Expires='{expires_str}'. "
                "Fix: make sure Received is on or before Expires. Item skipped."
            ))
            for issue in row_issues:
                emit(issue)
            total_error += sum(1 for x in row_issues if x.level == "ERROR")
            skipped += 1
            blocking_errors_found = True
            continue

        if not (received <= issue_date <= expires):
            if issue_date < received:
                emit(Issue(
                    "WARN",
                    f"Row {i}: '{title}' excluded by posting window. "
                    f"Issue date '{issue_date_str}' is before Received '{received_str}'. "
                    "Fix: use a later issue date or adjust Received if this is wrong."
                ))
            else:
                emit(Issue(
                    "WARN",
                    f"Row {i}: '{title}' excluded by posting window. "
                    f"Issue date '{issue_date_str}' is after Expires '{expires_str}'. "
                    "Fix: use an earlier issue date or adjust Expires if this is wrong."
                ))
            excluded_by_date += 1
            continue

        section, section_issues = normalize_section(section_raw, i, title)
        row_issues.extend(section_issues)
        if section is None:
            for issue in row_issues:
                emit(issue)
            total_autofix += sum(1 for x in row_issues if x.level == "AUTO-FIX")
            total_warn += sum(1 for x in row_issues if x.level == "WARN")
            total_error += sum(1 for x in row_issues if x.level == "ERROR")
            skipped += 1
            blocking_errors_found = True
            continue

        body = clean_body(body_raw)
        if not body:
            row_issues.append(Issue(
                "WARN",
                f"Row {i}: field 'Text' is empty for '{title}'. Raw value: '{body_raw}'. "
                "Fix: add bulletin text. Item kept, but output may look empty."
            ))

        body, autofix_issues = auto_fix_markdown_links(body, i, title)
        row_issues.extend(autofix_issues)

        link_issues = analyze_links(body, i, title)
        row_issues.extend(link_issues)

        if image and " " in image and not image.startswith(("http://", "https://")):
            row_issues.append(Issue(
                "WARN",
                f"Row {i}: field 'Image' for '{title}' has value '{image}' containing spaces. "
                "Fix: use a clean filename or URL. Local validation is not enforced here, but this may fail later."
            ))

        for issue in row_issues:
            emit(issue)

        total_autofix += sum(1 for x in row_issues if x.level == "AUTO-FIX")
        total_warn += sum(1 for x in row_issues if x.level == "WARN")
        row_error_count = sum(1 for x in row_issues if x.level == "ERROR")
        total_error += row_error_count

        if row_error_count:
            skipped += 1
            blocking_errors_found = True
            continue

        passing.append({
            "Title": title,
            "Body": body,
            "Section": section,
            "Received": received_str,
            "Expires": expires_str,
            "Image": image,
        })

    if blocking_errors_found:
        print(
            f"ERROR: Bulletin preprocess stopped due to unresolved content errors. "
            f"auto-fix={total_autofix}, warnings={total_warn}, errors={total_error}, "
            f"skipped={skipped}, excluded_by_date={excluded_by_date}.",
            file=sys.stderr,
        )
        print(
            "Fix the ERROR items in Bulletins.csv / Chucks-list-MASTER.ods and re-run preprocess.",
            file=sys.stderr,
        )
        return 1

    try:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=OUT_COLS,
                extrasaction="ignore",
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerows(passing)
    except Exception as exc:
        print(f"ERROR writing {OUTPUT_CSV}: {exc}", file=sys.stderr)
        return 1

    print(
        f"  [OK] Bulletins preprocess: {len(passing)} items -> {OUTPUT_CSV} "
        f"(auto-fix={total_autofix}, warnings={total_warn}, skipped={skipped}, "
        f"excluded_by_date={excluded_by_date}, issue_date={issue_date_str})"
    )
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Preprocess Chuck's List bulletins CSV.")
    p.add_argument("--issue-date", required=True, help="Issue date YYYY-MM-DD")
    args = p.parse_args()
    sys.exit(preprocess_bulletins(args.issue_date))