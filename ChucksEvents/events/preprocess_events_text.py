"""
ChucksEvents/events/preprocess_events_text.py
Role: Read raw Events.csv, validate, filter by issue_date, write events_data.csv
Pipeline stage: PREPROCESS
Called by: Chucks_List_Builder.py via subprocess

CSV column contract (actual Events.csv headers):
  Received, Starts, Expires, Section, Title, Text, Image, notes

Accepted date formats:
  - YYYY-MM-DD   (ISO canonical)
  - M/D/YY       (2-digit year)
  - M/D/YYYY     (4-digit year — common LibreOffice Calc export format)

Inclusion rule:
  Starts <= issue_date <= Expires

Preprocess responsibilities:
  - validate required columns
  - normalize smart characters in Body (curly quotes, em-dashes, NBSP)
  - auto-fix safe link issues (bare email/www targets in markdown)
  - validate links: ERROR on bare URLs, raw HTML, raw-URL-as-label; WARN on bare emails
  - block pipeline on unresolved content errors (exit 1)
  - exit non-zero when passing == 0 and skipped > 0 (P1-A silent blank-issue guard)

Design notes:
  - No HEADER_ALIASES / normalize_headers() — Events.csv headers are used directly.
  - No normalize_section() — Section is passed through verbatim (no canonical alias map).
  - starts > expires is a WARN only; item is still included if it falls in the date window.

CHANGELOG
  2026-05-31  Bug 2 fix: add quoting=csv.QUOTE_ALL to DictWriter so that
              multi-line cells and cells containing []() markdown link syntax
              survive the CSV round-trip intact.
              Improved skip messages: each skip now logs row, field, value,
              and fix instruction.
  2026-06-01  Parity pass against preprocess_bulletin_text.py:
              - DATE_RE_LONG (M/D/YYYY 4-digit year) added at module level.
              - Issue dataclass + emit() pattern replaces bare print() calls.
              - auto_fix_markdown_links() added (bare email/www -> proper scheme).
              - analyze_links() added with segment-targeted paren check (Bug 7).
              - SMART_CHAR_MAP applied in clean_body().
              - blocking_errors_found gate: pipeline halts on content errors.
              - P1-A: exit non-zero when passing == 0 and skipped > 0.
              - Empty-row guard moved before field reads.
              - Image field space warning added.
              - argparse moved to top-level imports.
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

REQUIRED_COLS = ["Received", "Starts", "Expires", "Title", "Text"]
OUT_COLS      = ["Title", "Body", "Starts", "Ends", "Section", "Image"]

# ---------------------------------------------------------------------------
# Date patterns — all three slash/ISO variants must be handled.
# LibreOffice Calc exports dates as M/D/YYYY; accept all three so the
# operator does not need to pre-format the ODS date column.
# ---------------------------------------------------------------------------
DATE_RE_ISO   = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
DATE_RE_LONG  = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

# ---------------------------------------------------------------------------
# Link / content patterns
# ---------------------------------------------------------------------------
EMAIL_RE         = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
INLINE_EMAIL_RE  = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL_RE           = re.compile(r"https?://[^\s<>\"]+")
WWW_TARGET_RE    = re.compile(r"^www\.[^\s)]+$", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")
TRAILING_PUNCTUATION = ".,;:!?)}]"

# ---------------------------------------------------------------------------
# Smart-character normalization
# ---------------------------------------------------------------------------
SMART_CHAR_MAP = str.maketrans({
    "\u2018": "'",   # left single quotation mark
    "\u2019": "'",   # right single quotation mark / apostrophe
    "\u201C": '"',   # left double quotation mark
    "\u201D": '"',   # right double quotation mark
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u00A0": " ",   # non-breaking space
})


# ---------------------------------------------------------------------------
# Issue reporting
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    level: str   # AUTO-FIX | WARN | ERROR
    message: str


def emit(issue: Issue) -> None:
    print(f"  [{issue.level}] {issue.message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(val: str, row_num: int, field: str) -> date | None:
    raw = (val or "").strip()
    if not raw:
        emit(Issue(
            "WARN",
            f"Row {row_num}: field '{field}' is empty — date is required. "
            f"Fix: Open Chucks-list-MASTER.ods, locate row {row_num}, fill in '{field}'."
        ))
        return None

    if DATE_RE_ISO.match(raw):
        try:
            return date.fromisoformat(raw)
        except ValueError as e:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' value '{raw}' is not a valid date: {e} "
                f"Fix: Correct to YYYY-MM-DD format in Chucks-list-MASTER.ods."
            ))
            return None

    short_match = DATE_RE_SHORT.match(raw)
    if short_match:
        try:
            return date(2000 + int(short_match.group(3)), int(short_match.group(1)), int(short_match.group(2)))
        except ValueError as e:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' value '{raw}' is not a valid date: {e} "
                f"Fix: Correct the month/day/year in Chucks-list-MASTER.ods."
            ))
            return None

    long_match = DATE_RE_LONG.match(raw)
    if long_match:
        try:
            return date(int(long_match.group(3)), int(long_match.group(1)), int(long_match.group(2)))
        except ValueError as e:
            emit(Issue(
                "WARN",
                f"Row {row_num}: field '{field}' value '{raw}' is not a valid date: {e} "
                f"Fix: Correct the month/day/year in Chucks-list-MASTER.ods."
            ))
            return None

    emit(Issue(
        "WARN",
        f"Row {row_num}: field '{field}' value '{raw}' is not a recognized date format. "
        f"Expected YYYY-MM-DD, M/D/YY, or M/D/YYYY. "
        f"Fix: Re-enter '{field}' in Chucks-list-MASTER.ods row {row_num}."
    ))
    return None


# ---------------------------------------------------------------------------
# Body normalization
# ---------------------------------------------------------------------------

def clean_body(text: str) -> str:
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    body = body.translate(SMART_CHAR_MAP)
    lines = body.split("\n")
    cleaned = [re.sub(r"[ \t]+", " ", line).rstrip() for line in lines]
    body = "\n".join(cleaned)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


# ---------------------------------------------------------------------------
# Link helpers
# ---------------------------------------------------------------------------

def split_trailing_punctuation(token: str) -> tuple[str, str]:
    clean = token.rstrip(TRAILING_PUNCTUATION)
    trailing = token[len(clean):]
    return clean, trailing


def looks_like_email_target(target: str) -> bool:
    return bool(EMAIL_RE.fullmatch(target.strip()))


def looks_like_www_target(target: str) -> bool:
    return bool(WWW_TARGET_RE.fullmatch(target.strip()))


def auto_fix_markdown_links(body: str, row_num: int, title: str) -> tuple[str, list[Issue]]:
    """Convert bare email and www.* targets inside [label](target) to proper schemes."""
    issues: list[Issue] = []

    def repl(match: re.Match[str]) -> str:
        label  = match.group(1).strip()
        target = match.group(2).strip()
        fixed  = target

        if looks_like_email_target(target):
            fixed = f"mailto:{target}"
            issues.append(Issue(
                "AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target "
                f"'{target}' to '{fixed}'."
            ))
        elif looks_like_www_target(target):
            fixed = f"https://{target}"
            issues.append(Issue(
                "AUTO-FIX",
                f"Row {row_num}: field 'Text' for '{title}' converted markdown target "
                f"'{target}' to '{fixed}'."
            ))

        return f"[{label}]({fixed})"

    fixed_body = MARKDOWN_LINK_RE.sub(repl, body)
    return fixed_body, issues


def analyze_links(body: str, row_num: int, title: str) -> list[Issue]:
    """
    Validate links in the Body field.

    Square-bracket balance is counted globally — unbalanced [ ] always
    indicates a broken markdown label.

    Parenthesis balance is checked only within identified [label](target)
    segments (Bug 7 fix). Balanced parens inside valid URL targets (e.g.,
    Wikipedia URLs, event URLs with parenthetical slugs) must NOT fire as
    false positives.
    """
    issues: list[Issue] = []
    lower = body.lower()

    # Raw HTML anchors — always an error
    if "href=" in lower or "<a " in lower:
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains raw HTML anchor tags. "
            "Fix: replace <a href=\"..\"> with markdown: [label](https://url)."
        ))

    # Square-bracket balance (safe to count globally)
    if body.count("[") != body.count("]"):
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' has unbalanced square brackets. "
            "Fix: repair markdown link text like [label](target)."
        ))

    # Paren balance: only within [label](...) segments — not the full field
    for match in MARKDOWN_LINK_RE.finditer(body):
        target = match.group(2)
        if target.count("(") != target.count(")"):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' has a markdown link with "
                f"unbalanced parentheses in target '{target}'. "
                "Fix: ensure the link target's parentheses are balanced, e.g. [label](https://example.com)."
            ))

    # Validate each [label](target) pair
    for label, target in MARKDOWN_LINK_RE.findall(body):
        label  = label.strip()
        target = target.strip()

        # Raw URL as label (P2-C)
        if URL_RE.fullmatch(label):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw URL as markdown "
                f"label '[{label}]({target})'. "
                "Fix: replace the visible label with descriptive text, e.g. [More details](https://example.com)."
            ))

        # Raw email as label
        if INLINE_EMAIL_RE.fullmatch(label):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' exposes a raw email as markdown "
                f"label '[{label}]({target})'. "
                "Fix: use descriptive text, e.g. [Email organizer](mailto:name@example.com)."
            ))

        # Target has no usable scheme
        if not (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("mailto:")
            or looks_like_email_target(target)
            or looks_like_www_target(target)
        ):
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' has markdown target '{target}' "
                "without a usable scheme or email format. "
                "Fix: use https://example.com, mailto:name@example.com, or a plain email address."
            ))

    # Bare URLs outside markdown links
    masked_body = MARKDOWN_LINK_RE.sub("[LINK]", body)

    for match in URL_RE.finditer(masked_body):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)
        if trailing:
            issues.append(Issue(
                "ERROR",
                f"Row {row_num}: field 'Text' for '{title}' contains URL '{token}' with "
                f"trailing punctuation. Fix: move '{trailing}' outside the URL → '{clean}'."
            ))
        issues.append(Issue(
            "ERROR",
            f"Row {row_num}: field 'Text' for '{title}' contains bare URL '{clean}'. "
            "Fix: convert to markdown, e.g. [More details](https://example.com)."
        ))

    # Bare emails outside markdown links — WARN (compiler can linkify safely)
    for match in INLINE_EMAIL_RE.finditer(masked_body):
        token = match.group(0)
        clean, trailing = split_trailing_punctuation(token)
        if trailing:
            issues.append(Issue(
                "WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains email '{token}' with "
                f"trailing punctuation. Fix: move '{trailing}' outside the address → '{clean}'."
            ))
        else:
            issues.append(Issue(
                "WARN",
                f"Row {row_num}: field 'Text' for '{title}' contains bare email '{clean}'. "
                "Review: compiler can safely linkify this, but markdown with descriptive text is preferred."
            ))

    return issues


# ---------------------------------------------------------------------------
# Main preprocess
# ---------------------------------------------------------------------------

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

    passing:              list[dict[str, str]] = []
    skipped             = 0
    excluded_by_date    = 0
    total_autofix       = 0
    total_warn          = 0
    total_error         = 0
    blocking_errors_found = False

    for i, row in enumerate(all_rows, start=2):
        # Empty-row guard first — before any field reads
        if not any((v or "").strip() for v in row.values()):
            continue

        row_issues: list[Issue] = []

        title       = (row.get("Title")   or "").strip()
        section     = (row.get("Section") or "").strip()
        body_raw    = (row.get("Text")    or "")
        image       = (row.get("Image")   or "").strip()
        starts_str  = (row.get("Starts")  or "").strip()
        expires_str = (row.get("Expires") or "").strip()

        if not title:
            row_issues.append(Issue(
                "ERROR",
                f"Row {i}: field 'Title' is empty — item cannot be published. "
                f"Fix: Add a Title in Chucks-list-MASTER.ods row {i}."
            ))
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

        # starts > expires is a warning only; item still published if in window
        if starts > expires:
            row_issues.append(Issue(
                "WARN",
                f"Row {i}: '{title}' — Starts ({starts_str}) is after Expires ({expires_str}). "
                f"Fix: Correct Starts or Expires in Chucks-list-MASTER.ods row {i}."
            ))

        if not (starts <= issue_date <= expires):
            for issue in row_issues:
                emit(issue)
            excluded_by_date += 1
            continue

        body = clean_body(body_raw)

        body, autofix_issues = auto_fix_markdown_links(body, i, title)
        row_issues.extend(autofix_issues)

        link_issues = analyze_links(body, i, title)
        row_issues.extend(link_issues)

        if image and " " in image and not image.startswith(("http://", "https://")):
            row_issues.append(Issue(
                "WARN",
                f"Row {i}: field 'Image' for '{title}' has value '{image}' containing spaces. "
                "Fix: use a clean filename or URL. This may fail during compile."
            ))

        for issue in row_issues:
            emit(issue)

        total_autofix   += sum(1 for x in row_issues if x.level == "AUTO-FIX")
        total_warn      += sum(1 for x in row_issues if x.level == "WARN")
        row_error_count  = sum(1 for x in row_issues if x.level == "ERROR")
        total_error     += row_error_count

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

    # Halt on unresolved content errors — do not write partial output
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

    # P1-A: silent blank-issue guard.
    # A zero-item output that exits 0 looks like a clean build of a blank issue.
    # If every row was skipped (bad dates, empty titles) exit non-zero so the
    # Builder halts rather than advancing to compile with an empty CSV.
    if len(passing) == 0 and skipped > 0:
        print(
            f"ERROR: Events preprocess produced 0 passing items "
            f"(skipped={skipped}, excluded_by_date={excluded_by_date}). "
            "No output written. Fix the skipped rows listed above and re-run.",
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
    except Exception as e:
        print(f"ERROR writing {OUTPUT_CSV}: {e}", file=sys.stderr)
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