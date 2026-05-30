import csv
import html
import os
import re
import sys
import unicodedata
from collections import OrderedDict
from datetime import datetime


INPUT_FILENAME = "bulletins_data.csv"
OUTPUT_FILENAME = "chucks_bulletin_final_output.html"


INTRO_NOTE = ""
CLOSING_NOTE = ""


# ============================================================
# TOC CONTROLS
# ============================================================
INCLUDE_TOC = True
INCLUDE_ITEM_TOC = True
INCLUDE_READER_TOC_TOGGLE = True
DEFAULT_READER_TOC_MODE = "full"  # "full" or "Section"


DEFAULT_SECTION = "Community Announcements"
DEFAULT_TITLE = "Untitled Post"


SECTION_ORDER = [
    "Urgent Bulletins",
    "Housing Opportunities",
    "Swap Market",
    "Local Services & Help",
    "Community Announcements",
]

SECTION_RANK = {name: idx for idx, name in enumerate(SECTION_ORDER)}


HEADER_ALIASES = {
    "section": "Section",
    "category": "Section",
    "catergory": "Section",
    "group": "Section",
    "type": "Section",

    "title": "Title",
    "subject": "Title",
    "headline": "Title",
    "post title": "Title",

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

    "expires": "Expires",
    "end": "Expires",
    "ends": "Expires",
    "end date": "Expires",
    "expiration": "Expires",
}


HTML_HEAD = """<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>Chuck's List Bulletin</title>
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

.header-band,
.footer-band {
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

.body-copy,
.body-copy p,
.body-copy li {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 20px;
  line-height: 31px;
  color: #201a15;
}

.small-label,
.toc-label {
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

.hr-rule {
  border-top: 1px solid #d5cab8;
  font-size: 0;
  line-height: 0;
}

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

  .header-band,
  .footer-band {
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

  .body-copy,
  .body-copy p,
  .body-copy li {
    color: #dccfbf !important;
  }

  .small-label,
  .toc-label {
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

@media only screen and (max-width: 620px) {
  .container {
    width: 100% !important;
  }

  .mobile-pad {
    padding-left: 16px !important;
    padding-right: 16px !important;
  }

  .headline {
    font-size: 26px !important;
    line-height: 34px !important;
  }

  .section-title {
    font-size: 22px !important;
    line-height: 30px !important;
  }

  .header-body-copy {
    font-size: 18px !important;
    line-height: 29px !important;
  }

  .body-copy,
  .body-copy p,
  .body-copy li {
    font-size: 19px !important;
    line-height: 30px !important;
  }

  .toc-helper {
    font-size: 14px !important;
    line-height: 23px !important;
  }
}
</style>
</head>
<body style="margin:0; padding:0; background-color:#f3ede2;">
<div class="hidden-preheader">Local bulletin board posts from Cortez, Dolores, Mancos, Durango, and surrounding communities.</div>
<center class="wrapper" style="width:100%; background-color:#f3ede2;">
"""


HTML_FOOT = """</center>
</body>
</html>
"""


TOKEN_RE = re.compile(
    r"(https?://[^\s<>\"'()]+|mailto:[^\s<>\"'()]+|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
)
BULLET_RE = re.compile(r"^(\*|\-|•|–)\s+")
SUBHEAD_RE = re.compile(r"^##\s+")


def clean_text(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_header(value):
    cleaned = " ".join(clean_text(value).lower().split())
    return HEADER_ALIASES.get(cleaned, cleaned)


def slugify(value):
    text = unicodedata.normalize("NFKD", clean_text(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"


def parse_sort_date(value):
    text = clean_text(value)
    if not text:
        return "9999-12-31"

    for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    return "9999-12-31"


def section_rank(section_name):
    return SECTION_RANK.get(clean_text(section_name), 999)


def render_inline(text):
    if not text:
        return ""

    parts = TOKEN_RE.split(text)
    result = []

    for i, part in enumerate(parts):
        if i % 2 == 0:
            result.append(html.escape(part, quote=False))
        else:
            token = part
            if token.startswith(("http://", "https://", "mailto:")):
                href = html.escape(token, quote=True)
                display = html.escape(token.replace("mailto:", ""), quote=False)
            else:
                href = html.escape("mailto:" + token, quote=True)
                display = html.escape(token, quote=False)

            target = ' target="_blank" rel="noopener noreferrer"' if href.startswith(("http://", "https://")) else ""
            result.append(
                f'<a href="{href}"{target} style="color:#a95c22; text-decoration:underline;">{display}</a>'
            )

    return "".join(result)


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
        if all(SUBHEAD_RE.match(line.strip()) for line in block):
            for line in block:
                heading_text = SUBHEAD_RE.sub("", line.strip()).strip()
                if heading_text:
                    parts.append(
                        '<div class="body-copy" style="padding-top:14px;">'
                        '<span class="small-label" style="font-size:13px; line-height:20px; font-weight:bold; color:#4f5e3d; text-transform:uppercase; letter-spacing:0.6px; font-family:Arial, Helvetica, sans-serif;">'
                        + html.escape(heading_text, quote=False)
                        + "</span></div>"
                    )
            continue

        non_empty = [ln for ln in block if ln.strip()]
        if non_empty and all(BULLET_RE.match(ln.strip()) for ln in non_empty):
            items = []
            for line in non_empty:
                content = BULLET_RE.sub("", line.strip()).strip()
                if content:
                    items.append(f'<li style="margin-bottom:8px;">{render_inline(content)}</li>')
            if items:
                parts.append(
                    '<div class="body-copy" style="padding-top:14px; font-size:20px; line-height:31px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
                    '<ul style="margin:0; padding-left:28px;">'
                    + "".join(items)
                    + "</ul></div>"
                )
            continue

        line_htmls = [render_inline(line.rstrip()) for line in block]
        if line_htmls:
            parts.append(
                '<div class="body-copy" style="padding-top:14px; font-size:20px; line-height:31px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
                + "<br>".join(line_htmls)
                + "</div>"
            )

    return "".join(parts)


def parse_rows(input_path):
    rows = []

    with open(input_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=",")

        for row in reader:
            normalized = {}
            for key, value in row.items():
                if key is None:
                    continue
                normalized[normalize_header(key)] = clean_text(value)

            section = normalized.get("Section") or DEFAULT_SECTION
            title = normalized.get("Title") or DEFAULT_TITLE
            text = normalized.get("Text", "")
            image = normalized.get("Image", "")
            expires = normalized.get("Expires", "")

            if title or text or image:
                rows.append({
                    "Section": section,
                    "Title": title,
                    "Text": text,
                    "Image": image,
                    "Expires": expires,
                    "_sort_expires": parse_sort_date(expires),
                })

    rows.sort(
        key=lambda row: (
            section_rank(row.get("Section", "")),
            row.get("_sort_expires", "9999-12-31"),
            clean_text(row.get("Title", "")).lower(),
        )
    )

    return rows


def group_rows(rows):
    grouped = OrderedDict()
    used_ids = set()
    section_ids = {}

    for row in rows:
        section = row["Section"] or DEFAULT_SECTION

        if section not in grouped:
            grouped[section] = []

        item_id = slugify(row["Title"])
        if item_id in used_ids:
            base = item_id
            n = 2
            while f"{base}-{n}" in used_ids:
                n += 1
            item_id = f"{base}-{n}"

        used_ids.add(item_id)
        row["item_id"] = item_id

        if section not in section_ids:
            section_ids[section] = slugify(section)

        row["Section_id"] = section_ids[section]
        grouped[section].append(row)

    return grouped


def render_preheader():
    return (
        '\n<!-- PREHEADER BAR -->\n'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; background-color:#f3ede2;">'
        '<tr><td align="center" style="padding:18px 12px 8px 12px;">'
        '<table role="presentation" class="container" width="720" cellpadding="0" cellspacing="0" border="0" style="width:100%; max-width:720px; background-color:#fbf7f0; border:1px solid #d5cab8;">'
        '<tr><td class="preheader mobile-pad" align="center" style="padding:14px 20px; font-size:14px; line-height:22px; color:#665b50; font-family:Arial, Helvetica, sans-serif;">'
        'Can&#39;t read this email easily? '
        '<a href="$[LI:VIEWINBROWSER]$" target="_blank" rel="noopener noreferrer" style="color:#a95c22; text-decoration:underline;">View this email in a browser</a>'
        "</td></tr></table></td></tr></table>"
    )


def render_header():
    return (
        '\n<!-- MAIN EMAIL WRAP START -->\n'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; background-color:#f3ede2;">'
        '<tr><td align="center" style="padding:0 12px 18px 12px;">'
        '<table role="presentation" class="container" width="720" cellpadding="0" cellspacing="0" border="0" style="width:100%; max-width:720px; background-color:#fbf7f0; border:1px solid #d5cab8;">'
        '\n<!-- HEADER BAND -->\n'
        '<tr><td class="header-band mobile-pad" style="padding:30px 28px 28px 28px; background-color:#2e3d2f; border-bottom:4px solid #b46a2d;">'
        '<div class="eyebrow" style="font-size:12px; line-height:18px; text-transform:uppercase; letter-spacing:1.2px; font-weight:bold; color:#bcc8b0; font-family:Arial, Helvetica, sans-serif;">Chuck&#39;s List &mdash; Bulletin</div>'
        '<div class="headline" style="padding-top:8px; font-size:30px; line-height:38px; font-weight:bold; color:#f7f1e6; font-family:Georgia, Times New Roman, Times, serif;">Local bulletin board posts from around our community</div>'
        '<div class="header-body-copy" style="padding-top:12px; font-size:19px; line-height:30px; color:#ddd2c3; font-family:Arial, Helvetica, sans-serif;">Serving Cortez, Dolores, Mancos, Durango, and surrounding communities. Use this bulletin for housing, goods, services, items for sale, items wanted, local offers, and other practical community notices. If you do not see your post listed, please resubmit it.</div>'
        "</td></tr>"
    )


def render_intro_note():
    if not INTRO_NOTE.strip():
        return ""

    return (
        '\n<!-- OPTIONAL INTRO NOTE -->\n'
        '<tr><td class="row-white mobile-pad" style="padding:22px 28px; background-color:#fbf7f0;">'
        '<div class="callout body-copy" style="background-color:#edf2e7; border-left:4px solid #6b7c52; border-top:1px solid #c8d4b8; border-right:1px solid #c8d4b8; border-bottom:1px solid #c8d4b8; padding:16px; font-size:20px; line-height:31px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
        + render_inline(INTRO_NOTE)
        + "</div></td></tr>"
    )


def render_reader_toc_toggle():
    if not INCLUDE_READER_TOC_TOGGLE:
        return ""

    return (
        '\n<!-- TOC VIEW TOGGLE -->\n'
        '<div class="toc-helper" style="padding-top:10px; font-size:15px; line-height:24px; color:#5d5248; font-family:Arial, Helvetica, sans-serif;">'
        'Choose your view: '
        '<a href="#toc-sections" style="color:#a95c22; text-decoration:underline;">Jump to sections only</a>'
        ' &nbsp;&middot;&nbsp; '
        '<a href="#toc-full" style="color:#a95c22; text-decoration:underline;">Show full contents</a>'
        '</div>'
        '<div class="toc-helper" style="padding-top:8px; font-size:15px; line-height:24px; color:#5d5248; font-family:Arial, Helvetica, sans-serif;">'
        'If your email app does not jump when you tap a link, just keep scrolling — the bulletin is fully readable in order.'
        '</div>'
    )


def render_section_only_toc(grouped):
    out = []
    out.append(
        '<a name="toc-sections"></a><div id="toc-sections" class="toc-label" style="font-size:13px; line-height:20px; font-weight:bold; color:#4f5e3d; text-transform:uppercase; letter-spacing:0.6px; font-family:Arial, Helvetica, sans-serif; border-bottom:1px solid #d5cab8; padding-bottom:4px;">Sections only</div>'
    )
    out.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">')

    for section, items in grouped.items():
        section_id = items[0]["Section_id"] if items else slugify(section)
        out.append(
            f'<tr><td style="padding:14px 0 6px 0; font-size:20px; line-height:30px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
            f'<a href="#{section_id}" style="color:#a95c22; text-decoration:underline; font-weight:bold;">{html.escape(section)}</a>'
            f'</td></tr>'
        )

    out.append("</table>")
    return "".join(out)


def render_full_toc(grouped):
    out = []
    out.append(
        '<a name="toc-full"></a><div id="toc-full" class="toc-label" style="font-size:13px; line-height:20px; font-weight:bold; color:#4f5e3d; text-transform:uppercase; letter-spacing:0.6px; font-family:Arial, Helvetica, sans-serif; border-bottom:1px solid #d5cab8; padding-bottom:4px;">Full contents</div>'
    )
    out.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">')

    for section, items in grouped.items():
        section_id = items[0]["Section_id"] if items else slugify(section)
        out.append(
            f'<tr><td style="padding:14px 0 6px 0; font-size:20px; line-height:30px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
            f'<a href="#{section_id}" style="color:#a95c22; text-decoration:underline; font-weight:bold;">{html.escape(section)}</a>'
            f'</td></tr>'
        )
        if INCLUDE_ITEM_TOC:
            for item in items:
                out.append(
                    f'<tr><td style="padding:0 0 8px 18px; font-size:18px; line-height:28px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
                    f'&#8226; <a href="#{item["item_id"]}" style="color:#a95c22; text-decoration:underline;">{html.escape(item["Title"])}</a>'
                    f'</td></tr>'
                )

    out.append("</table>")
    return "".join(out)


def render_toc(grouped):
    if not INCLUDE_TOC:
        return ""

    parts = [
        '\n<!-- TABLE OF CONTENTS -->\n',
        '<tr><td class="row-white mobile-pad" style="padding:22px 28px 24px 28px; background-color:#fbf7f0;">',
        '<div class="body-copy" style="font-size:20px; line-height:31px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
        '<span class="toc-label" style="font-size:13px; line-height:20px; font-weight:bold; color:#4f5e3d; text-transform:uppercase; letter-spacing:0.6px; font-family:Arial, Helvetica, sans-serif;">In this bulletin</span>'
        '</div>'
    ]

    if INCLUDE_READER_TOC_TOGGLE:
        parts.append(render_reader_toc_toggle())

    if DEFAULT_READER_TOC_MODE == "Section":
        parts.append('<div style="padding-top:14px;">')
        parts.append(render_section_only_toc(grouped))
        parts.append('</div>')
        if INCLUDE_ITEM_TOC:
            parts.append('<div style="padding-top:18px;">')
            parts.append(render_full_toc(grouped))
            parts.append('</div>')
    else:
        parts.append('<div style="padding-top:14px;">')
        parts.append(render_full_toc(grouped))
        parts.append('</div>')
        parts.append('<div style="padding-top:18px;">')
        parts.append(render_section_only_toc(grouped))
        parts.append('</div>')

    parts.append("</td></tr>")
    return "".join(parts)


def render_image(image_value, alt_text, row_class):
    images = [part.strip() for part in image_value.split("&") if part.strip()]
    if not images:
        return ""

    out = []
    for img in images:
        href = html.escape(img, quote=True)
        alt = html.escape(alt_text if alt_text else "Bulletin image.", quote=True)
        bg = "#fbf7f0" if row_class == "row-white" else "#f4eee3"
        out.append(
            '\n<!-- OPTIONAL IMAGE BLOCK -->\n'
            f'<tr><td class="mobile-pad" style="padding:0 28px 22px 28px; background-color:{bg};">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; background-color:#efe7da; border:1px solid #d5cab8;">'
            f'<tr><td style="padding:12px;"><a href="{href}" target="_blank" rel="noopener noreferrer" style="display:block; text-decoration:none;"><img src="{href}" alt="{alt}" style="display:block; width:100%; max-width:100%; height:auto;"></a></td></tr>'
            "</table></td></tr>"
        )

    return "".join(out)


def render_item(row, row_class):
    bg = "#fbf7f0" if row_class == "row-white" else "#f4eee3"
    body = render_text_to_body_html(row.get("Text", ""))

    item = [
        f'\n<!-- BULLETIN ITEM: {html.escape(row["Title"], quote=False)} -->\n',
        f'<tr><td class="{row_class} mobile-pad" style="padding:22px 28px; background-color:{bg};">',
        f'<a name="{row["item_id"]}"></a>',
        f'<div id="{row["item_id"]}" class="section-title" style="font-size:24px; line-height:32px; font-weight:bold; color:#18130f; font-family:Arial, Helvetica, sans-serif;">{html.escape(row["Title"])}</div>',
        body,
        "</td></tr>",
    ]

    if row.get("Image"):
        item.append(render_image(row["Image"], row["Title"], row_class))

    item.append(
        f'<tr><td style="padding:0; background-color:{bg};"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td class="hr-rule" style="border-top:1px solid #d5cab8; font-size:0; line-height:0;">&nbsp;</td></tr></table></td></tr>'
    )

    return "".join(item)


def render_sections(grouped):
    out = []
    row_toggle = True
    first_section = True

    for section, items in grouped.items():
        if not first_section:
            out.append(
                '\n<!-- SECTION BREAK -->\n'
                '<tr><td style="padding:0; background-color:#fbf7f0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td class="hr-rule" style="border-top:1px solid #d5cab8; font-size:0; line-height:0;">&nbsp;</td></tr></table></td></tr>'
            )
        first_section = False

        section_id = items[0]["Section_id"] if items else slugify(section)
        out.append(
            f'\n<!-- SECTION: {html.escape(section, quote=False)} -->\n'
            f'<tr><td class="section-label mobile-pad" style="padding:10px 28px; background-color:#365c61; border-top:1px solid #284449; border-bottom:1px solid #284449; font-size:13px; line-height:18px; text-transform:uppercase; letter-spacing:1.1px; font-weight:bold; color:#edf5f4; font-family:Arial, Helvetica, sans-serif;">'
            f'<a name="{section_id}"></a><div id="{section_id}" style="margin:0; padding:0;">{html.escape(section)}</div>'
            f'</td></tr>'
        )

        for row in items:
            out.append(render_item(row, "row-white" if row_toggle else "row-alt"))
            row_toggle = not row_toggle

    return "".join(out)


def render_closing_note():
    if not CLOSING_NOTE.strip():
        return ""

    return (
        '\n<!-- OPTIONAL CLOSING NOTE -->\n'
        '<tr><td class="row-white mobile-pad" style="padding:22px 28px; background-color:#fbf7f0;">'
        '<div class="callout body-copy" style="background-color:#edf2e7; border-left:4px solid #6b7c52; border-top:1px solid #c8d4b8; border-right:1px solid #c8d4b8; border-bottom:1px solid #c8d4b8; padding:16px; font-size:20px; line-height:31px; color:#201a15; font-family:Arial, Helvetica, sans-serif;">'
        + render_inline(CLOSING_NOTE)
        + "</div></td></tr>"
    )


def render_footer():
    return (
        '\n<!-- FOOTER -->\n'
        '<tr><td style="padding:18px 0 0 0; background-color:#f3ede2;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; background-color:#2e3d2f; border-top:3px solid #b46a2d;" class="footer-band">'
        '<tr><td class="mobile-pad footer-copy" align="center" style="padding:20px 24px 6px 24px; font-size:13px; line-height:19px; color:#bcc8b0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;">This email was sent by <a href="mailto:ChucksList@McAfeeFarm.biz" style="color:#e59b5d; text-decoration:underline;">ChucksList@McAfeeFarm.biz</a> to <a href="mailto:$[UD:CONTACT_EMAIL]$" style="color:#e59b5d; text-decoration:underline;">$[UD:CONTACT_EMAIL]$</a></td></tr>'
        '<tr><td class="mobile-pad footer-copy" align="center" style="padding:6px 24px; font-size:13px; line-height:19px; color:#bcc8b0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;">Not interested? <a href="$[LI:UNSUBSCRIBE]$" target="_blank" rel="noopener noreferrer" style="color:#e59b5d; text-decoration:underline;">Unsubscribe</a></td></tr>'
        '<tr><td class="mobile-pad footer-copy" align="center" style="padding:6px 24px; font-size:13px; line-height:19px; color:#bcc8b0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;">Feedback or corrections: <a href="mailto:THill@techspecific.com" style="color:#e59b5d; text-decoration:underline;">THill@techspecific.com</a> &nbsp;&middot;&nbsp; <a href="mailto:Chuck@mcafeefarm.biz" style="color:#e59b5d; text-decoration:underline;">Chuck@mcafeefarm.biz</a></td></tr>'
        '<tr><td class="mobile-pad footer-copy" align="center" style="padding:6px 24px 24px 24px; font-size:13px; line-height:19px; color:#bcc8b0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;">Chuck&#39;s List powered by <a href="https://www.techspecific.com" target="_blank" rel="noopener noreferrer" style="color:#e59b5d; text-decoration:underline;">TechSpecific</a></td></tr>'
        "</table></td></tr></table></td></tr></table>"
    )


def build_html(rows):
    grouped = group_rows(rows)
    return "".join([
        HTML_HEAD,
        render_preheader(),
        render_header(),
        render_intro_note(),
        render_toc(grouped),
        render_sections(grouped),
        render_closing_note(),
        render_footer(),
        HTML_FOOT,
    ])


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, INPUT_FILENAME)
    output_path = os.path.join(base_dir, OUTPUT_FILENAME)

    rows = parse_rows(input_path)
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