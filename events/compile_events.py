# -*- coding: utf-8 -*-
import csv
import html
import os
import re
import sys
import unicodedata
from collections import OrderedDict

# ------------------------------------------------------------
# INPUT / OUTPUT
# ------------------------------------------------------------

INPUT_FILENAME = "events_data.csv"  # preprocessed CSV
OUTPUT_FILENAME = "chucks_events_final_output.html"

INTRO_NOTE = ""
CLOSING_NOTE = ""

# ------------------------------------------------------------
# TOC CONTROLS
# ------------------------------------------------------------

INCLUDE_TOC = True
INCLUDE_ITEM_TOC = True
INCLUDE_READER_TOC_TOGGLE = True
DEFAULT_READER_TOC_MODE = "full"  # "full" or "Section"

# ------------------------------------------------------------
# EVENT SECTIONS
# ------------------------------------------------------------

SECTION_ORDER = [
    "Single Events",
    "Multiple Events",
    "Recurring Events",
]

SECTION_ALIASES = {
    "single": "Single Events",
    "single event": "Single Events",
    "single events": "Single Events",
    "single-event": "Single Events",
    "multiple": "Multiple Events",
    "multiple event": "Multiple Events",
    "multiple events": "Multiple Events",
    "multiple-event": "Multiple Events",
    "recurring": "Recurring Events",
    "recurring event": "Recurring Events",
    "recurring events": "Recurring Events",
    "recurring-event": "Recurring Events",
}

DEFAULT_SECTION = "Single Events"
DEFAULT_TITLE = "UnTitled Event"

# ------------------------------------------------------------
# HEADER ALIASES
# ------------------------------------------------------------

HEADER_ALIASES = {
    "section": "Section",
    "category": "Section",
    "catergory": "Section",
    "group": "Section",
    "type": "Section",
    "title": "Title",
    "subject": "Title",
    "headline": "Title",
    "event title": "Title",
    "text": "Text",
    "body": "Text",
    "description": "Text",
    "content": "Text",
    "details": "Text",
    "image": "Image",
    "image path": "Image",
    "imagepath": "Image",
    "img": "Image",
    "photo": "Image",
}

# ------------------------------------------------------------
# HTML SHELL (trimmed; matches May 28 template)
# ------------------------------------------------------------

HTML_HEAD = """<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<meta name="color-scheme" content="light dark" />
<meta name="supported-color-schemes" content="light dark" />
<title>Chucks List Events</title>
<style type="text/css">
body, table, td, p, a {
  margin: 0;
  padding: 0;
  -webkit-text-size-adjust: 100% !important;
  -ms-text-size-adjust: 100% !important;
  text-size-adjust: 100% !important;
}
table {
  border-collapse: collapse;
  border-spacing: 0;
  mso-table-lspace: 0pt;
  mso-table-rspace: 0pt;
}
img {
  border: 0;
  outline: none;
  text-decoration: none;
  display: block;
  max-width: 100%;
  height: auto;
  -ms-interpolation-mode: bicubic;
}
body {
  width: 100% !important;
  min-width: 100%;
  background-color: #f3ede2;
  color: #201a15;
  font-family: Arial, Helvetica, sans-serif;
}
a {
  color: #a95c22;
  text-decoration: underline;
}
.wrapper {
  width: 100%;
  background-color: #f3ede2;
}
.container {
  width: 100%;
  max-width: 720px;
  background-color: #fbf7f0;
  border: 1px solid #d5cab8;
}
.preheader {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 14px;
  line-height: 22px;
  color: #665b50;
}
.hidden-preheader {
  display: none !important;
  visibility: hidden;
  opacity: 0;
  color: transparent;
  height: 0;
  width: 0;
  overflow: hidden;
  mso-hide: all;
  font-size: 1px;
  line-height: 1px;
  max-height: 0;
  max-width: 0;
}
.header-band, .footer-band {
  background-color: #2e3d2f;
}
.header-band {
  border-bottom: 4px solid #b46a2d;
}
.footer-band {
  border-top: 3px solid #b46a2d;
}
.eyebrow {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 12px;
  line-height: 18px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  font-weight: bold;
  color: #bcc8b0;
}
.headline {
  font-family: Georgia, "Times New Roman", Times, serif;
  font-size: 30px;
  line-height: 38px;
  font-weight: bold;
  color: #f7f1e6;
}
.header-body-copy {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 19px;
  line-height: 30px;
  color: #ddd2c3;
}
.section-label {
  background-color: #365c61;
  border-top: 1px solid #284449;
  border-bottom: 1px solid #284449;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13px;
  line-height: 18px;
  text-transform: uppercase;
  letter-spacing: 1.1px;
  font-weight: bold;
  color: #edf5f4;
}
.row-white {
  background-color: #fbf7f0;
}
.row-alt {
  background-color: #f4eee3;
}
.section-title {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 24px;
  line-height: 32px;
  font-weight: bold;
  color: #18130f;
}
.body-copy, .body-copy p, .body-copy li {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 20px;
  line-height: 31px;
  color: #201a15;
}
.small-label, .toc-label {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13px;
  line-height: 20px;
  font-weight: bold;
  color: #4f5e3d;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
.toc-helper {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 15px;
  line-height: 24px;
  color: #5d5248;
}
.callout {
  background-color: #edf2e7;
  border-left: 4px solid #6b7c52;
  border-top: 1px solid #c8d4b8;
  border-right: 1px solid #c8d4b8;
  border-bottom: 1px solid #c8d4b8;
  padding: 16px;
}
.footer-copy {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13px;
  line-height: 21px;
  color: #bcc8b0;
}
.footer-copy a {
  color: #e59b5d;
}
/* Dark mode */
@media (prefers-color-scheme: dark) {
  body, .wrapper {
    background-color: #151513 !important;
  }
  .container {
    background-color: #1d211b !important;
    border-color: #30342d !important;
  }
  .preheader {
    color: #9b8f81 !important;
  }
  .header-band, .footer-band {
    background-color: #1c251d !important;
  }
  .headline {
    color: #f3eadc !important;
  }
  .header-body-copy {
    color: #c0b3a4 !important;
  }
  .section-label {
    background-color: #244348 !important;
    border-color: #1a2f33 !important;
    color: #dbefee !important;
  }
  .row-white {
    background-color: #232923 !important;
  }
  .row-alt {
    background-color: #1d221d !important;
  }
  .section-title {
    color: #f0e0c9 !important;
  }
  .body-copy, .body-copy p, .body-copy li {
    color: #dccfbf !important;
  }
  .small-label, .toc-label {
    color: #a4bb84 !important;
  }
  .toc-helper {
    color: #b7aa9c !important;
  }
  .callout {
    background-color: #1b241c !important;
    border-left-color: #6b7c52 !important;
    border-top-color: #31422f !important;
    border-right-color: #31422f !important;
    border-bottom-color: #31422f !important;
  }
  .hr-rule {
    border-top-color: #3a4038 !important;
  }
  a {
    color: #eba266 !important;
  }
}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f3ede2;">
<div class="hidden-preheader">Local events and activities from Cortez, Dolores, Mancos, Durango, and surrounding communities.</div>
<center class="wrapper" style="width:100%;background-color:#f3ede2;">
"""

HTML_FOOT = """
</center>
</body>
</html>
"""

# ------------------------------------------------------------
# TEXT UTILITIES
# ------------------------------------------------------------

TOKEN_RE = re.compile(r"(https?://[^\s]+|mailto:[^\s]+)")
BULLET_RE = re.compile(r"^[-•\u2022]\s+")
SUBHEAD_RE = re.compile(r"^[_A-Z0-9 .,:;!?'-]+$")

def clean_text(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()

def normalize_header(key):
    cleaned = "".join((key or "").strip().lower().split())
    return HEADER_ALIASES.get(cleaned, cleaned.capitalize())

def slugify(value):
    text = clean_text(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"

def render_inline(text):
    if not text:
        return ""
    parts = TOKEN_RE.split(text)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(html.escape(part, quote=False))
        else:
            token = part
            if token.startswith(("http://", "https://", "mailto:")):
                href = html.escape(token, quote=True)
                display = html.escape(token.replace("mailto:", ""), quote=False)
                target = ' target="_blank" rel="noopener noreferrer"' if href.startswith(("http://", "https://")) else ""
                out.append(f'<a href="{href}"{target} style="color:#a95c22;text-decoration:underline;">{display}</a>')
            else:
                out.append(html.escape(token, quote=False))
    return "".join(out)

def split_blocks(text):
    lines = (text or "").split("\n")
    blocks = []
    current = []
    for line in lines:
        if line.strip():
            current.append(line.rstrip())
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks

def render_text_to_body_html(text):
    text = clean_text(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return ""
    parts = []
    for block in split_blocks(text):
        nonempty = [ln for ln in block if ln.strip()]
        if nonempty and all(SUBHEAD_RE.match(ln.strip()) for ln in nonempty):
            heading_text = SUBHEAD_RE.sub("", nonempty[0].strip()).strip() or nonempty[0].strip()
            parts.append(
                '<div class="body-copy" style="padding-top:14px;">'
                '<span class="small-label" style="font-size:13px;line-height:20px;font-weight:bold;color:#4f5e3d;text-transform:uppercase;letter-spacing:0.6px;font-family:Arial, Helvetica, sans-serif;">'
                f'{html.escape(heading_text, quote=False)}'
                '</span></div>'
            )
            continue
        if nonempty and all(BULLET_RE.match(ln.strip()) for ln in nonempty):
            items = []
            for line in nonempty:
                content = BULLET_RE.sub("", line.strip())
                if content:
                    items.append(f'<li style="margin-bottom:8px;">{render_inline(content)}</li>')
            if items:
                parts.append(
                    '<div class="body-copy" style="padding-top:14px;font-size:20px;line-height:31px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">'
                    '<ul style="margin:0;padding-left:28px;">'
                    + "".join(items) +
                    '</ul></div>'
                )
            continue
        line_htmls = [render_inline(line.rstrip()) for line in block]
        parts.append(
            '<div class="body-copy" style="padding-top:14px;font-size:20px;line-height:31px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">'
            + "<br>".join(line_htmls) +
            "</div>"
        )
    return "".join(parts)

def normalize_section(sec):
    secclean = clean_text(sec).lower() if sec else ""
    if not secclean:
        return DEFAULT_SECTION
    return SECTION_ALIASES.get(secclean, clean_text(sec))

# ------------------------------------------------------------
# ROW PARSING AND GROUPING
# ------------------------------------------------------------

def parse_rows(input_path):
    rows = []
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found", file=sys.stderr)
        return rows
    with open(input_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=",")
        print(f"Raw fieldnames: {reader.fieldnames}", file=sys.stderr)
        for row in reader:
            normalized = {}
            for key, value in row.items():
                if key is None:
                    continue
                normalized_key = normalize_header(key)
                normalized[normalized_key] = clean_text(value)
            section = normalize_section(normalized.get("Section"))
            title = normalized.get("Title") or DEFAULT_TITLE
            text = normalized.get("Text")
            image = normalized.get("Image")
            if title or text or image:
                rows.append(
                    {
                        "Section": section,
                        "Title": title,
                        "Text": text,
                        "Image": image,
                    }
                )
    print(f"Loaded {len(rows)} events from {input_path}", file=sys.stderr)
    return rows

def group_rows(rows):
    grouped = OrderedDict()
    # Initialize canonical sections in desired order
    for sec in SECTION_ORDER:
        grouped[sec] = []
    # Put each row into its section
    for row in rows:
        section_name = row["Section"] or DEFAULT_SECTION
        if section_name not in grouped:
            grouped[section_name] = []
        grouped[section_name].append(row)
    total_items = sum(len(v) for v in grouped.values())
    print(f"group_rows: sections={list(grouped.keys())}, total_items={total_items}", file=sys.stderr)
    return grouped

def derive_ids(grouped):
    used_item_ids = set()
    for section_name, items in grouped.items():
        section_id = slugify(section_name)
        for item in items:
            item["section_id"] = section_id
            item_id = slugify(item["Title"])
            if item_id in used_item_ids:
                base = item_id
                n = 2
                while f"{base}-{n}" in used_item_ids:
                    n += 1
                item_id = f"{base}-{n}"
            used_item_ids.add(item_id)
            item["item_id"] = item_id
    print(
        "derive_ids: sections after ids="
        + str([(k, len(v)) for k, v in grouped.items()]),
        file=sys.stderr,
    )
    return grouped

# ------------------------------------------------------------
# RENDER: PREHEADER, HEADER, TOC
# ------------------------------------------------------------

def render_preheader():
    return """
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#f3ede2;">
  <tr>
    <td align="center" style="padding:18px 12px 8px 12px;">
      <table role="presentation" class="container" width="720" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:720px;background-color:#fbf7f0;border:1px solid #d5cab8;">
        <tr>
          <td class="preheader mobile-pad" align="center" style="padding:14px 20px;font-size:14px;line-height:22px;color:#665b50;font-family:Arial, Helvetica, sans-serif;">
            Can't read this email easily? <a href="LIVIEWINBROWSER" target="_blank" rel="noopener noreferrer" style="color:#a95c22;text-decoration:underline;">View this email in a browser</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""

def render_header():
    return """
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#f3ede2;">
  <tr>
    <td align="center" style="padding:0 12px 18px 12px;">
      <table role="presentation" class="container" width="720" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:720px;background-color:#fbf7f0;border:1px solid #d5cab8;">
        <tr>
          <td class="header-band mobile-pad" style="padding:30px 28px 28px 28px;background-color:#2e3d2f;border-bottom:4px solid #b46a2d;">
            <div class="eyebrow" style="font-size:12px;line-height:18px;text-transform:uppercase;letter-spacing:1.2px;font-weight:bold;color:#bcc8b0;font-family:Arial, Helvetica, sans-serif;">Chuck's List &mdash; Events Calendar</div>
            <div class="headline" style="padding-top:8px;font-size:30px;line-height:38px;font-weight:bold;color:#f7f1e6;font-family:Georgia, 'Times New Roman', Times, serif;">Upcoming events and activities around our community</div>
            <div class="header-body-copy" style="padding-top:12px;font-size:19px;line-height:30px;color:#ddd2c3;font-family:Arial, Helvetica, sans-serif;">
              Serving Cortez, Dolores, Mancos, Durango, and surrounding communities. Use this events email for local happenings, classes, performances, and community gatherings. If you do not see your event listed, please resubmit it.
            </div>
          </td>
        </tr>
"""

def render_intro_note():
    if not INTRO_NOTE.strip():
        return ""
    return """
        <tr>
          <td class="row-white mobile-pad" style="padding:22px 28px;background-color:#fbf7f0;">
            <div class="callout body-copy" style="background-color:#edf2e7;border-left:4px solid #6b7c52;border-top:1px solid #c8d4b8;border-right:1px solid #c8d4b8;border-bottom:1px solid #c8d4b8;padding:16px;font-size:20px;line-height:31px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">
              %s
            </div>
          </td>
        </tr>
""" % render_inline(INTRO_NOTE)

def render_reader_toc_toggle():
    if not INCLUDE_READER_TOC_TOGGLE:
        return ""
    if DEFAULT_READER_TOC_MODE == "Section":
        section_note = "You are viewing the shorter section list."
        full_note = "Need more detail? Use the full contents list below."
    else:
        section_note = "Want a shorter list? Jump to the section-only contents."
        full_note = "You are viewing the full contents list."
    return f"""
        <div class="toc-helper" style="padding-top:10px;font-size:15px;line-height:24px;color:#5d5248;font-family:Arial, Helvetica, sans-serif;">
          Choose your view:
          <a href="#toc-sections" style="color:#a95c22;text-decoration:underline;">Jump to sections only</a>
          &nbsp;&middot;&nbsp;
          <a href="#toc-full" style="color:#a95c22;text-decoration:underline;">Show full contents</a>
        </div>
        <div class="toc-helper" style="padding-top:8px;font-size:15px;line-height:24px;color:#5d5248;font-family:Arial, Helvetica, sans-serif;">
          {html.escape(section_note, quote=False)} {html.escape(full_note, quote=False)}
        </div>
"""

def render_section_only_toc(grouped):
    out = []
    out.append('<a name="toc-sections"></a>')
    out.append('<div id="toc-sections" class="toc-label" style="font-size:13px;line-height:20px;font-weight:bold;color:#4f5e3d;text-transform:uppercase;letter-spacing:0.6px;font-family:Arial, Helvetica, sans-serif;border-bottom:1px solid #d5cab8;padding-bottom:4px;">Sections only</div>')
    out.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">')
    for section_name, items in grouped.items():
        if not items:
            continue
        section_id = items[0].get("section_id") or slugify(section_name)
        out.append(
            f'<tr><td style="padding:14px 0 6px 0;font-size:20px;line-height:30px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">'
            f'<a href="#{section_id}" style="color:#a95c22;text-decoration:underline;font-weight:bold;">{html.escape(section_name)}</a>'
            f'</td></tr>'
        )
    out.append("</table>")
    return "".join(out)

def render_full_toc(grouped):
    out = []
    out.append('<a name="toc-full"></a>')
    out.append('<div id="toc-full" class="toc-label" style="font-size:13px;line-height:20px;font-weight:bold;color:#4f5e3d;text-transform:uppercase;letter-spacing:0.6px;font-family:Arial, Helvetica, sans-serif;border-bottom:1px solid #d5cab8;padding-bottom:4px;">Full contents</div>')
    out.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">')
    for section_name, items in grouped.items():
        if not items:
            continue
        section_id = items[0].get("section_id") or slugify(section_name)
        out.append(
            f'<tr><td style="padding:14px 0 6px 0;font-size:20px;line-height:30px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">'
            f'<a href="#{section_id}" style="color:#a95c22;text-decoration:underline;font-weight:bold;">{html.escape(section_name)}</a>'
            f'</td></tr>'
        )
        if INCLUDE_ITEM_TOC:
            for item in items:
                out.append(
                    f'<tr><td style="padding:0 0 8px 18px;font-size:18px;line-height:28px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">'
                    f'&#8226; <a href="#{item["item_id"]}" style="color:#a95c22;text-decoration:underline;">{html.escape(item["Title"])}</a>'
                    f'</td></tr>'
                )
    out.append("</table>")
    return "".join(out)

def render_toc(grouped):
    if not INCLUDE_TOC or not grouped:
        return ""
    parts = []
    parts.append("""
        <tr>
          <td class="row-white mobile-pad" style="padding:22px 28px 24px 28px;background-color:#fbf7f0;">
            <div class="body-copy" style="font-size:20px;line-height:31px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">
              <span class="toc-label" style="font-size:13px;line-height:20px;font-weight:bold;color:#4f5e3d;text-transform:uppercase;letter-spacing:0.6px;font-family:Arial, Helvetica, sans-serif;">In this events calendar</span>
            </div>
""")
    parts.append(render_reader_toc_toggle())
    if DEFAULT_READER_TOC_MODE == "Section":
        parts.append('<div style="padding-top:14px;">')
        parts.append(render_section_only_toc(grouped))
        parts.append("</div>")
        if INCLUDE_ITEM_TOC:
            parts.append('<div style="padding-top:18px;">')
            parts.append(render_full_toc(grouped))
            parts.append("</div>")
    else:
        parts.append('<div style="padding-top:14px;">')
        parts.append(render_full_toc(grouped))
        parts.append("</div>")
        parts.append('<div style="padding-top:18px;">')
        parts.append(render_section_only_toc(grouped))
        parts.append("</div>")
    parts.append("""
          </td>
        </tr>
""")
    return "".join(parts)

# ------------------------------------------------------------
# RENDER: ITEMS AND SECTIONS
# ------------------------------------------------------------

def render_image_block(image_value, alt_text, row_class):
    images = [part.strip() for part in (image_value or "").split(",") if part.strip()]
    if not images:
        return ""
    out = []
    bg = "#fbf7f0" if row_class == "row-white" else "#f4eee3"
    for img in images:
        href = html.escape(img, quote=True)
        alt = html.escape(alt_text if alt_text else "Event Image.", quote=True)
        out.append(
            f"""<!-- OPTIONAL IMAGE BLOCK -->
<tr>
  <td class="mobile-pad" style="padding:0 28px 22px 28px;background-color:{bg};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#efe7da;border:1px solid #d5cab8;">
      <tr>
        <td style="padding:12px;">
          <a href="{href}" target="_blank" rel="noopener noreferrer" style="display:block;text-decoration:none;">
            <img src="{href}" alt="{alt}" style="display:block;width:100%;max-width:100%;height:auto;" />
          </a>
        </td>
      </tr>
    </table>
  </td>
</tr>
"""
        )
    return "".join(out)

def render_item(row, row_class):
    bg = "#fbf7f0" if row_class == "row-white" else "#f4eee3"
    body = render_text_to_body_html(row.get("Text"))
    item_id = row["item_id"]
    title = row["Title"]
    out = []
    out.append(
        f"""<!-- EVENT ITEM {html.escape(title, quote=False)} -->
<tr>
  <td class="{row_class} mobile-pad" style="padding:22px 28px;background-color:{bg};">
    <a name="{item_id}"></a>
    <div id="{item_id}" class="section-title" style="font-size:24px;line-height:32px;font-weight:bold;color:#18130f;font-family:Arial, Helvetica, sans-serif;">
      {html.escape(title, quote=False)}
    </div>
    {body}
  </td>
</tr>
"""
    )
    if row.get("Image"):
        out.append(render_image_block(row["Image"], title, row_class))
    out.append(
        f"""<tr>
  <td style="padding:0;background-color:{bg};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="hr-rule" style="border-top:1px solid #d5cab8;font-size:0;line-height:0;">&nbsp;</td>
      </tr>
    </table>
  </td>
</tr>
"""
    )
    return "".join(out)

def render_sections(grouped):
    out = []
    row_toggle = True
    first_section = True
    for section_name, items in grouped.items():
        if not items:
            continue
        if not first_section:
            out.append("""
<tr>
  <td style="padding:0;background-color:#fbf7f0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="hr-rule" style="border-top:1px solid #d5cab8;font-size:0;line-height:0;">&nbsp;</td>
      </tr>
    </table>
  </td>
</tr>
""")
        first_section = False
        section_id = items[0].get("section_id") or slugify(section_name)
        out.append(
            f"""<!-- SECTION {html.escape(section_name, quote=False)} -->
<tr>
  <td class="section-label mobile-pad" style="padding:10px 28px;background-color:#365c61;border-top:1px solid #284449;border-bottom:1px solid #284449;font-size:13px;line-height:18px;text-transform:uppercase;letter-spacing:1.1px;font-weight:bold;color:#edf5f4;font-family:Arial, Helvetica, sans-serif;">
    <a name="{section_id}"></a>
    <div id="{section_id}" style="margin:0;padding:0;">{html.escape(section_name, quote=False)}</div>
  </td>
</tr>
"""
        )
        for row in items:
            out.append(render_item(row, "row-white" if row_toggle else "row-alt"))
            row_toggle = not row_toggle
    return "".join(out)

def render_closing_note():
    if not CLOSING_NOTE.strip():
        return ""
    return """
<tr>
  <td class="row-white mobile-pad" style="padding:22px 28px;background-color:#fbf7f0;">
    <div class="callout body-copy" style="background-color:#edf2e7;border-left:4px solid #6b7c52;border-top:1px solid #c8d4b8;border-right:1px solid #c8d4b8;border-bottom:1px solid #c8d4b8;padding:16px;font-size:20px;line-height:31px;color:#201a15;font-family:Arial, Helvetica, sans-serif;">
      %s
    </div>
  </td>
</tr>
""" % render_inline(CLOSING_NOTE)

def render_footer():
    return """
<tr>
  <td style="padding:18px 0 0 0;background-color:#f3ede2;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#2e3d2f;border-top:3px solid #b46a2d;" class="footer-band">
      <tr>
        <td class="mobile-pad footer-copy" align="center" style="padding:20px 24px 6px 24px;font-size:13px;line-height:19px;color:#bcc8b0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
          This email was sent by <a href="mailto:ChucksList@McAfeeFarm.biz" style="color:#e59b5d;text-decoration:underline;">ChucksList@McAfeeFarm.biz</a> to <a href="mailto:UDCONTACTEMAIL" style="color:#e59b5d;text-decoration:underline;">UDCONTACTEMAIL</a>.
        </td>
      </tr>
      <tr>
        <td class="mobile-pad footer-copy" align="center" style="padding:6px 24px;font-size:13px;line-height:19px;color:#bcc8b0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
          Not interested? <a href="LIUNSUBSCRIBE" target="_blank" rel="noopener noreferrer" style="color:#e59b5d;text-decoration:underline;">Unsubscribe</a>.
        </td>
      </tr>
      <tr>
        <td class="mobile-pad footer-copy" align="center" style="padding:6px 24px;font-size:13px;line-height:19px;color:#bcc8b0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
          Feedback or corrections? <a href="mailto:THill@techspecific.com" style="color:#e59b5d;text-decoration:underline;">THill@techspecific.com</a> &nbsp;&middot;&nbsp;
          <a href="mailto:Chuck@mcafeefarm.biz" style="color:#e59b5d;text-decoration:underline;">Chuck@mcafeefarm.biz</a>
        </td>
      </tr>
      <tr>
        <td class="mobile-pad footer-copy" align="center" style="padding:6px 24px 24px 24px;font-size:13px;line-height:19px;color:#bcc8b0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
          Chuck's List powered by <a href="https://www.techspecific.com" target="_blank" rel="noopener noreferrer" style="color:#e59b5d;text-decoration:underline;">TechSpecific</a>.
        </td>
      </tr>
    </table>
  </td>
</tr>
"""

# ------------------------------------------------------------
# MAIN BUILD
# ------------------------------------------------------------

def build_html(rows):
    grouped = group_rows(rows)
    grouped = derive_ids(grouped)
    return "".join(
        [
            HTML_HEAD,
            render_preheader(),
            render_header(),
            render_intro_note(),
            render_toc(grouped),
            render_sections(grouped),
            render_closing_note(),
            render_footer(),
            "</table></td></tr></table></td></tr></table>",
            HTML_FOOT,
        ]
    )

def main():
    basedir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(basedir, INPUT_FILENAME)
    output_path = os.path.join(basedir, OUTPUT_FILENAME)
    rows = parse_rows(input_path)
    if not rows:
        print("Warning: No events found in events_data.csv", file=sys.stderr)
    html_output = build_html(rows)
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(html_output)
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Compile failed: {exc}", file=sys.stderr)
        raise SystemExit(1)