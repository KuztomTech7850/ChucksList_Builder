"""
events/compile_events.py
Role: Compile events_data.csv -> chucks_events_final_output.html
Pipeline stage: COMPILE (runs after preprocess_events_text.py)
Called by: Chucks_List_Builder.py via subprocess

Engineer notes:
- This compiler assumes preprocess_events_text.py has already normalized and validated the data.
- Compile is responsible for organizing and rendering the massaged event rows into final email HTML.
- Image file existence is NOT validated here by design for the current local workflow.
  The HTML is often relocated after compile, and the CSV Image value is treated as trusted.
  If/when this pipeline is migrated to a server, restore strict image/path validation there.
- Markdown links [Label](https://example.com) are supported and preferred.
- Bare URLs/emails are linkified only after escaping.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import textwrap
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR = SCRIPT_DIR.parent
INPUT_CSV = SCRIPT_DIR / "events_data.csv"
OUTPUT_DIR = PROJ_DIR / "ChucksEvents"
OUTPUT_HTML = SCRIPT_DIR / "chucks_events_final_output.html"


PALETTE = {
    "bg": "#FAF6F0",
    "surface": "#F2EDE4",
    "border": "#C8B89A",
    "header_bg": "#2D5A3D",
    "header_text": "#FAF6F0",
    "section_bg": "#3D7A52",
    "section_text": "#FAF6F0",
    "accent": "#8B6914",
    "body_text": "#2C1E0F",
    "muted": "#6E5740",
    "link": "#1A4D6E",
    "toc_bg": "#EDE5D8",
    "hr": "#C8B89A",
}

SECTION_ORDER = [
    "Single Events",
    "Multiple Events",
    "Recurring Events",
]

SECTION_ALIASES = {
    "Single": "Single Events",
    "Single Events": "Single Events",
    "Multiple": "Multiple Events",
    "Multiple Events": "Multiple Events",
    "Recurring": "Recurring Events",
    "Recurring Events": "Recurring Events",
}

TRAILING_PUNCTUATION = ".,;:!?)}]"

MARKDOWN_LINK_RE = re.compile(
    r"\[([^\]\n]{1,300})\]\((https?://[^\s)]+|mailto:[^\s)]+)\)",
    re.IGNORECASE,
)
BULLET_LINE_RE = re.compile(r"^\s*[-*•]\s+(.*)$")
SUBHEAD_RE = re.compile(r"^\s*##\s*(.+?)\s*$")


EMAIL_CSS = f"""
  body {{ margin:0; padding:0; background:{PALETTE['bg']};
    font-family:Georgia,'Times New Roman',serif; }}
  .wrapper {{ max-width:660px; margin:0 auto; background:{PALETTE['bg']}; }}
  .header {{ background:{PALETTE['header_bg']}; color:{PALETTE['header_text']};
    padding:28px 32px 20px 32px; text-align:center; }}
  .header h1 {{ margin:0 0 4px 0; font-size:28px; font-weight:700; letter-spacing:0.5px; }}
  .header .issue-date {{ font-size:15px; opacity:0.85; margin:0; }}
  .toc-box {{ background:{PALETTE['toc_bg']}; border:1px solid {PALETTE['border']};
    padding:18px 24px; margin:0; }}
  .toc-box h2 {{ font-size:17px; font-weight:700; margin:0 0 12px 0; color:{PALETTE['body_text']}; }}
  .toc-box ul {{ margin:0; padding-left:18px; }}
  .toc-box li {{ margin-bottom:6px; }}
  .toc-box a {{ color:{PALETTE['link']}; text-decoration:none; font-size:16px; }}
  .toc-section {{ list-style:none; margin-top:10px; font-weight:700; }}
  .section-label {{ background:{PALETTE['section_bg']}; color:{PALETTE['section_text']};
    padding:10px 28px; font-size:13px; line-height:18px; text-transform:uppercase;
    letter-spacing:1.2px; font-weight:700; }}
  .item-block {{ background:{PALETTE['surface']}; border-bottom:1px solid {PALETTE['border']};
    padding:20px 28px 16px 28px; }}
  .item-title {{ font-size:20px; font-weight:700; margin:0 0 6px 0; color:{PALETTE['body_text']}; }}
  .item-meta {{ font-size:14px; color:{PALETTE['muted']}; margin:0 0 12px 0; }}
  .item-body {{ font-size:18px; line-height:1.75; color:{PALETTE['body_text']}; }}
  .item-body a {{ color:{PALETTE['link']}; text-decoration:underline; }}
  .item-image {{ margin:12px 0 0 0; text-align:center; }}
  .item-image img {{ max-width:100%; height:auto; border-radius:4px;
    border:1px solid {PALETTE['border']}; }}
  .entry-subhead {{ font-size:17px; font-weight:700; color:{PALETTE['accent']}; margin:18px 0 6px 0; }}
  .footer {{ background:{PALETTE['header_bg']}; color:{PALETTE['header_text']};
    padding:18px 32px; text-align:center; font-size:14px; }}
  hr.section-rule {{ border:none; border-top:2px solid {PALETTE['hr']}; margin:0; }}
"""


def make_anchor(title: str, seen: dict[str, int]) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    slug = slug[:60] or "item"
    slug = f"item-{slug}"
    count = seen.get(slug, 0) + 1
    seen[slug] = count
    return slug if count == 1 else f"{slug}-{count}"


def split_trailing_punctuation(token: str) -> tuple[str, str]:
    clean = token.rstrip(TRAILING_PUNCTUATION)
    trailing = token[len(clean):]
    return clean, trailing


def protect_markdown_links(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        label = html.escape(match.group(1).strip())
        href = html.escape(match.group(2).strip(), quote=True)
        token = f"__MDLINK_{counter}__"

        if href.lower().startswith("mailto:"):
            replacements[token] = f'<a href="{href}">{label}</a>'
        else:
            replacements[token] = (
                f'<a href="{href}" target="_blank" rel="noopener noreferrer">{label}</a>'
            )
        return token

    return MARKDOWN_LINK_RE.sub(repl, text), replacements


def restore_markdown_links(text: str, replacements: dict[str, str]) -> str:
    for token, replacement in replacements.items():
        text = text.replace(token, replacement)
    return text


def linkify_escaped_text(escaped_text: str) -> str:
    token_re = re.compile(
        r"(https?://[^\s<>\"]+|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
    )

    parts = token_re.split(escaped_text)
    out: list[str] = []

    for part in parts:
        if not part:
            continue

        clean, trailing = split_trailing_punctuation(part)

        if re.match(r"^https?://", clean, re.IGNORECASE):
            out.append(
                f'<a href="{clean}" target="_blank" rel="noopener noreferrer">{clean}</a>{trailing}'
            )
        elif re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", clean):
            out.append(f'<a href="mailto:{clean}">{clean}</a>{trailing}')
        else:
            out.append(part)

    return "".join(out)


def escape_then_linkify(text: str) -> str:
    protected, replacements = protect_markdown_links(text)
    escaped = html.escape(protected)
    linked = linkify_escaped_text(escaped)
    return restore_markdown_links(linked, replacements)


def render_body(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""

    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n{2,}", normalized)
    html_blocks: list[str] = []

    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n")]
        if not any(line.strip() for line in lines):
            continue

        paragraph_lines: list[str] = []
        list_items: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph_lines
            if not paragraph_lines:
                return
            joined = "<br>\n".join(escape_then_linkify(line) for line in paragraph_lines)
            html_blocks.append(f'<p style="margin:0 0 14px 0;line-height:1.7;">{joined}</p>')
            paragraph_lines = []

        def flush_list() -> None:
            nonlocal list_items
            if not list_items:
                return
            items = "".join(f'<li style="margin-bottom:6px;">{item}</li>' for item in list_items)
            html_blocks.append(
                f'<ul style="margin:0 0 14px 0;padding-left:22px;">{items}</ul>'
            )
            list_items = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                flush_paragraph()
                flush_list()
                continue

            subhead_match = SUBHEAD_RE.match(line)
            bullet_match = BULLET_LINE_RE.match(line)

            if subhead_match:
                flush_paragraph()
                flush_list()
                html_blocks.append(
                    f'<div class="entry-subhead">{escape_then_linkify(subhead_match.group(1).strip())}</div>'
                )
                continue

            if bullet_match:
                flush_paragraph()
                list_items.append(escape_then_linkify(bullet_match.group(1).strip()))
                continue

            flush_list()
            paragraph_lines.append(line)

        flush_paragraph()
        flush_list()

    return "\n".join(html_blocks)


def build_image_html(image_path: str, title: str) -> str:
    """
    Current local workflow:
    - trust the CSV Image value
    - emit the image block directly
    - do not validate the file on disk here

    Server migration note:
    - restore path/file validation when the pipeline runs in a fixed hosted environment
    """
    if not image_path or not image_path.strip():
        return ""

    src = html.escape(image_path.strip(), quote=True)
    alt = html.escape(title, quote=True)

    return (
        f'<div class="item-image">'
        f'<a href="{src}" target="_blank" rel="noopener noreferrer">'
        f'<img src="{src}" alt="{alt}" width="580" style="max-width:100%;">'
        f'</a></div>'
    )


def read_rows() -> list[tuple[int, dict[str, str]]]:
    if not INPUT_CSV.exists():
        print(f"ERROR: Input CSV not found: {INPUT_CSV}", file=sys.stderr)
        return []

    rows: list[tuple[int, dict[str, str]]] = []
    try:
        with open(INPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print("ERROR: events_data.csv appears empty or has no header row.", file=sys.stderr)
                return []

            required_cols = {"Title", "Body", "Starts", "Ends"}
            actual_cols = set(reader.fieldnames)
            missing = required_cols - actual_cols
            if missing:
                print(
                    "ERROR: events_data.csv is missing required columns: "
                    f"{', '.join(sorted(missing))}\n"
                    f"  Found columns: {', '.join(sorted(actual_cols))}\n"
                    "  Fix: Re-export from Chucks-list-MASTER.ods and re-run preprocess.",
                    file=sys.stderr,
                )
                return []

            for i, row in enumerate(reader, start=2):
                rows.append((i, row))
    except Exception as exc:
        print(f"ERROR reading {INPUT_CSV}: {exc}", file=sys.stderr)
        return []

    return rows


def group_rows(
    rows: list[tuple[int, dict[str, str]]]
) -> list[tuple[str, list[tuple[int, dict[str, str]]]]]:
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {name: [] for name in SECTION_ORDER}

    for row_num, row in rows:
        raw_section = (row.get("Section") or "").strip()
        section = SECTION_ALIASES.get(raw_section, raw_section)
        title = (row.get("Title") or "").strip()

        if not title:
            print(
                f"  [WARN] Row {row_num}: field 'Title' is empty. Fix: enter a title. Item skipped.",
                file=sys.stderr,
            )
            continue

        # Default empty/unknown sections to Single Events
        if not section:
            section = "Single Events"

        if section not in SECTION_ORDER:
            print(
                f"  [WARN] Row {row_num}: field 'Section' has value '{raw_section}' for item '{title}'. "
                f"Fix: use one of: {', '.join(SECTION_ORDER)}. Item skipped.",
                file=sys.stderr,
            )
            continue

        grouped[section].append((row_num, row))

    return [(section, grouped[section]) for section in SECTION_ORDER if grouped[section]]


def compile_events(issue_date: str) -> int:
    rows = read_rows()
    if rows is None:
        return 1

    if not rows:
        print(
            f"  [WARN] events_data.csv has no data rows for issue date {issue_date}. "
            "The output will be an empty events email.",
            file=sys.stderr,
        )

    def sort_key(item: tuple[int, dict[str, str]]) -> tuple[str, str]:
        _, row = item
        return ((row.get("Starts") or "9999-99-99"), (row.get("Title") or "").strip().lower())

    rows.sort(key=sort_key)
    grouped_sections = group_rows(rows)

    seen_anchors: dict[str, int] = {}
    item_anchor_map: dict[tuple[str, int], str] = {}

    for section_name, items in grouped_sections:
        for row_num, row in items:
            title = (row.get("Title") or "").strip()
            item_anchor_map[(section_name, row_num)] = make_anchor(title, seen_anchors)

    toc_lines: list[str] = []
    body_blocks: list[str] = []

    for section_name, items in grouped_sections:
        toc_lines.append(f'<li class="toc-section">{html.escape(section_name)}</li>')
        for row_num, row in items:
            title = (row.get("Title") or "").strip()
            starts = (row.get("Starts") or "").strip()
            anchor = item_anchor_map[(section_name, row_num)]
            toc_label = title if not starts else f"{title} ({starts})"
            toc_lines.append(f'<li><a href="#{anchor}">{html.escape(toc_label)}</a></li>')

    toc_html = (
        f'<div class="toc-box">'
        f'<h2>Upcoming Events</h2>'
        f'<ul style="list-style:none;padding-left:0;">{"".join(toc_lines)}</ul>'
        f'</div>'
    )

    for section_name, items in grouped_sections:
        body_blocks.append(f'<div class="section-label">{html.escape(section_name)}</div>')

        for row_num, row in items:
            title = (row.get("Title") or "").strip()
            body_raw = (row.get("Body") or "").strip()
            starts = (row.get("Starts") or "").strip()
            ends = (row.get("Ends") or "").strip()
            location = (row.get("Location") or "").strip()
            contact = (row.get("Contact") or "").strip()
            phone = (row.get("Phone") or "").strip()
            image = (row.get("Image") or "").strip()

            anchor = item_anchor_map[(section_name, row_num)]

            meta_parts = []
            if starts and ends and starts != ends:
                meta_parts.append(f"Dates: {html.escape(starts)} – {html.escape(ends)}")
            elif starts:
                meta_parts.append(f"Date: {html.escape(starts)}")
            if location:
                meta_parts.append(f"Location: {html.escape(location)}")
            if contact:
                meta_parts.append(f"Contact: {html.escape(contact)}")
            if phone:
                meta_parts.append(f"Phone: {html.escape(phone)}")
            meta_html = " &nbsp;|&nbsp; ".join(meta_parts)

            body_html = render_body(body_raw)
            image_html = build_image_html(image, title)

            body_blocks.append(
                f'<div class="item-block" id="{anchor}">'
                f'  <div class="item-title">{html.escape(title)}</div>'
                f'  <div class="item-meta">{meta_html}</div>'
                f'  <div class="item-body">{body_html}</div>'
                f'  {image_html}'
                f'</div>'
                f'<hr class="section-rule">'
            )

    full_html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Chuck's List Events — {html.escape(issue_date)}</title>
      <style>
    {EMAIL_CSS}
      </style>
    </head>
    <body>
    <div class="wrapper">
      <div class="header">
        <h1>Chuck's List Events</h1>
        <p class="issue-date">Issue Date: {html.escape(issue_date)}</p>
      </div>
      {toc_html}
      {"".join(body_blocks) if body_blocks else '<div style="padding:28px;text-align:center;color:#6E5740;">No events scheduled for this period.</div>'}
      <div class="footer">
        &copy; Chuck's List &mdash; Montezuma County, Colorado
      </div>
    </div>
    </body>
    </html>
    """)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        OUTPUT_HTML.write_text(full_html, encoding="utf-8")
        staging_copy = OUTPUT_DIR / "chucks_events_final_output.html"
        staging_copy.write_text(full_html, encoding="utf-8")
        print(f"  [OK] Events HTML written: {OUTPUT_HTML}")
        print(f"  [OK] Events staging copy: {staging_copy}")
    except Exception as exc:
        print(f"ERROR writing output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile events HTML output.")
    parser.add_argument("--issue-date", required=True, help="Issue date YYYY-MM-DD")
    args = parser.parse_args()
    sys.exit(compile_events(args.issue_date))