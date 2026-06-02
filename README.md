# Chuck's List Builder

> **One command. Two pipelines. Clean, accessible HTML for every issue.**

A local Python pipeline that transforms ODS editorial spreadsheets into
Zoho-ready HTML email editions for Chuck's List — a community bulletin
board and events newsletter serving Montezuma County and surrounding
communities in southwestern Colorado.

***

## Table of Contents

- [Overview](#overview)
- [Project Context](#project-context)
- [Quick Start](#quick-start)
- [File Map](#file-map)
- [Pipeline Architecture](#pipeline-architecture)
  - [Bulletins Pipeline](#bulletins-pipeline)
  - [Events Pipeline](#events-pipeline)
  - [Stage Contracts](#stage-contracts)
- [CLI Reference](#cli-reference)
- [Source Data Contract](#source-data-contract)
  - [Bulletins CSV Columns](#bulletins-csv-columns)
  - [Events CSV Columns](#events-csv-columns)
  - [Multi-Image Fields](#multi-image-fields)
  - [Date Formats](#date-formats)
  - [Markdown in Body Text](#markdown-in-body-text)
- [Inclusion Rules](#inclusion-rules)
- [Section Ordering](#section-ordering)
- [Output and Zoho Staging](#output-and-zoho-staging)
- [Design Standards](#design-standards)
- [Accessibility Requirements](#accessibility-requirements)
- [Error Handling Philosophy](#error-handling-philosophy)
- [Engineering Standards](#engineering-standards)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Guiding Principles](#guiding-principles)

***

## Overview

Chuck's List Builder reads two CSV exports from `Chucks-list-MASTER.ods`,
validates and filters each for the current issue date, and renders two
separate HTML email files — one for the Bulletin edition and one for the
Events edition. Both outputs are staged for direct upload to Zoho Campaigns.

The full build runs from a single command:

```bash
py Chucks_List_Builder.py --issue-date YYYY-MM-DD
```

***

## Project Context

Chuck's List is a community publishing effort in Montezuma County, Colorado.
It distributes local bulletins (housing, swap market, services, announcements)
and community events to a subscriber list via Zoho Campaigns HTML email.

The editorial workflow is:
1. Staff receive submissions by email or in person.
2. Items are entered into `Chucks-list-MASTER.ods` with received and expiry dates.
3. On publication day, staff export two CSVs and run one command.
4. The builder produces two complete HTML emails ready for Zoho upload.

The system is intentionally plain-text-first and low-dependency. Staff should
not need to understand HTML, CSS, or Python to operate it.

***

## Quick Start

**Requirements:** Python 3.10+, Windows (paths and subprocess behavior are
Windows-oriented), no third-party packages required.

```bash
# Full build — both pipelines
py Chucks_List_Builder.py --issue-date 2026-06-07

# Bulletins only
py Chucks_List_Builder.py --issue-date 2026-06-07 --issue-type bulletin

# Events only
py Chucks_List_Builder.py --issue-date 2026-06-07 --issue-type events

# With custom callout text
py Chucks_List_Builder.py --issue-date 2026-06-07 \
  --callout "Special notice for this issue." \
  --bottom-callout "Thank you for reading Chuck's List."

# Log output to file and skip auto-opening in VS Code
py Chucks_List_Builder.py --issue-date 2026-06-07 --log-to-file --no-open-vscode
```

**Before running,** export the two sheets from `Chucks-list-MASTER.ods`:
- `Bulletins.csv` → project root
- `Events.csv` → project root

***

## File Map

```
ChucksList_Builder/
├── Chucks_List_Builder.py              Orchestration entrypoint
├── Bulletins.csv                       Raw bulletin export (from ODS)
├── Events.csv                          Raw events export (from ODS)
├── Chucks-list-MASTER.ods              Editorial source workbook (not committed)
├── config.py                           Local config (not committed — see template)
├── config.py.template.py               Template for local config
│
├── bulletins/
│   ├── preprocess_bulletin_text.py     Normalize, validate, filter bulletins
│   ├── compile_bulletin.py             Render bulletin HTML
│   ├── bulletins_data.csv              Intermediate CSV (generated)
│   └── chucks_bulletin_final_output.html   Bulletin output (generated)
│
├── events/
│   ├── preprocess_events_text.py       Normalize, validate, filter events
│   ├── compile_events.py               Render events HTML
│   ├── events_data.csv                 Intermediate events CSV (generated)
│   └── chucks_events_final_output.html Events output (generated)
│
├── ChucksBulletin/                     Zoho staging folder — bulletins
├── ChucksEvents/                       Zoho staging folder — events
└── Images/                             Shared image source directory
```

***

## Pipeline Architecture

The builder runs two completely independent pipelines. They share no code,
no state, and no intermediate files. This is intentional.

```
Bulletins.csv ──► preprocess_bulletin_text.py ──► bulletins_data.csv
                                                        │
                                                        ▼
                                             compile_bulletin.py
                                                        │
                                                        ▼
                                   chucks_bulletin_final_output.html

Events.csv ──► preprocess_events_text.py ──► events_data.csv
                                                    │
                                                    ▼
                                          compile_events.py
                                                    │
                                                    ▼
                                 chucks_events_final_output.html
```

### Bulletins Pipeline

| Stage | Script | Input | Output |
|---|---|---|---|
| Preprocess | `preprocess_bulletin_text.py` | `Bulletins.csv` | `bulletins_data.csv` |
| Compile | `compile_bulletin.py` | `bulletins_data.csv` | `chucks_bulletin_final_output.html` |

### Events Pipeline

| Stage | Script | Input | Output |
|---|---|---|---|
| Preprocess | `preprocess_events_text.py` | `Events.csv` | `events_data.csv` |
| Compile | `compile_events.py` | `events_data.csv` | `chucks_events_final_output.html` |

### Stage Contracts

**Preprocess stage responsibilities:**
- Read the raw CSV export and validate all required fields
- Parse and validate dates in all accepted formats
- Apply date-window filtering for the issue date
- Normalize smart characters, line endings, and section aliases
- Auto-fix safe Markdown issues (bare emails → `mailto:`, bare `www.` → `https://`)
- Emit actionable `[WARN]` / `[ERROR]` messages: row number, field, value, fix instruction
- Write the intermediate CSV with `QUOTE_ALL`, UTF-8, `newline=""`
- Exit non-zero if any blocking error occurs, or if all rows were skipped

**Compile stage responsibilities:**
- Read the intermediate CSV
- Render full HTML using the approved Mesa Verde template
- Apply the correct escape-then-linkify order for Zoho link safety
- Build the table of contents with collision-safe anchors
- Render callout boxes (top and bottom)
- Write the final HTML output file

***

## CLI Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `--issue-date` | `YYYY-MM-DD` | **required** | Publication date used for date-window filtering |
| `--issue-type` | `bulletin\|events\|both` | `both` | Which pipeline(s) to run |
| `--callout` | string | hardcoded default | Top callout text for the issue |
| `--bottom-callout` | string | hardcoded default | Bottom callout text for the issue |
| `--debug` | flag | off | Enable debug-level logging |
| `--log-to-file` | flag | off | Write log output to a file alongside the output HTML |
| `--no-open-vscode` | flag | off | Suppress auto-opening output in VS Code |

If `--callout` or `--bottom-callout` are not passed, the builder emits a
`[REMIND]` warning showing the default text and the exact flag to override it.

***

## Source Data Contract

All CSV exports must be **UTF-8, comma-delimited, with text fields double-quoted**.
Export directly from `Chucks-list-MASTER.ods` with no post-processing.

### Bulletins CSV Columns

| Column | Required | Notes |
|---|---|---|
| `Received` | Yes | Date item was received |
| `Expires` | Yes | Last issue date to include this item |
| `Section` | Yes | Must match a canonical section name or alias |
| `Title` | Yes | Plain text |
| `Body` | Yes | Plain text; supports limited Markdown (see below) |
| `Image` | No | Filename(s) in `Images/`; pipe-separated for multiple |
| `notes` | No | Internal staff notes; never rendered |

### Events CSV Columns

| Column | Required | Notes |
|---|---|---|
| `Received` | No | Not used for filtering |
| `Starts` | Yes | First date to include this event |
| `Expires` | Yes | Last date to include this event (maps to `Ends` in output) |
| `Section` | No | Used for grouping |
| `Title` | Yes | Plain text |
| `Text` | Yes | Plain text; supports limited Markdown |
| `Image` | No | Filename(s) in `Images/`; pipe-separated for multiple |
| `notes` | No | Internal staff notes; never rendered |

### Multi-Image Fields

The `Image` column accepts **1 to 3 pipe-separated filenames**:

```
Images/photo1.jpg
Images/photo1.jpg|Images/photo2.jpg
Images/photo1.jpg|Images/photo2.jpg|Images/photo3.jpg
```

- Each filename is trimmed of whitespace before use.
- A 4th image triggers a `[WARN]` and is dropped. Move extras to cloud
  storage and share a link in the body text.
- Each image renders as its own `<img>` tag wrapped in a clickable `<a>`.
- Paths are always normalized to forward-slash URL syntax before HTML output.

### Date Formats

All date fields accept any of these formats:

| Format | Example |
|---|---|
| `YYYY-MM-DD` | `2026-06-07` |
| `M/D/YY` | `6/7/26` |
| `M/D/YYYY` | `6/7/2026` |

`YYYY-MM-DD` is the canonical format. LibreOffice Calc commonly exports dates
as `M/D/YYYY` — the builder accepts all three to avoid all-rows-skipped failures.

**Recommended:** Format the date columns in `Chucks-list-MASTER.ods` as
`YYYY-MM-DD` text before exporting. This eliminates ambiguity entirely.

### Markdown in Body Text

Staff do not need to know Markdown. The builder handles plain text naturally.
For staff who do use it, these patterns are supported:

| Pattern | Renders as |
|---|---|
| Blank line between paragraphs | New paragraph |
| `## Heading text` | Subheading |
| `- item` or `* item` or `• item` | Bulleted list item |
| `[Label](https://url)` | Clickable link |
| `[Label](mailto:email@example.com)` | Email link |

**Rules for links:**
- The label must be human-readable text — never a raw URL or raw email address.
- Bare URLs in body text are flagged as errors (Zoho cannot click-track them).
- Bare email addresses are flagged as warnings and auto-converted to `mailto:` links.

***

## Inclusion Rules

**Bulletins:** A row is included when `Received <= issue_date <= Expires`

**Events:** A row is included when `Starts <= issue_date <= Expires`

Rows outside the date window are silently excluded (not an error).
Rows with missing required fields or invalid dates are skipped with a
`[WARN]` that includes the row number, field name, bad value, and fix
instruction pointing back to `Chucks-list-MASTER.ods`.

***

## Section Ordering

### Bulletins (fixed order)

1. **Urgent Bulletins** — always pinned first when present
2. Housing Opportunities
3. Swap Market
4. Local Services & Help
5. Community Announcements

Section names in the CSV are normalized through an alias map, so minor
variations (capitalization, punctuation) are accepted.

### Events (by type)

1. Single Events
2. Hosts with Multiple Events
3. Recurring Events

***

## Output and Zoho Staging

| Output file | Staging folder |
|---|---|
| `bulletins/chucks_bulletin_final_output.html` | `ChucksBulletin/` |
| `events/chucks_events_final_output.html` | `ChucksEvents/` |

Copy the output HTML into the corresponding staging folder, then upload to
Zoho Campaigns as a custom HTML email. Do not upload if the build reported
any `[ERROR]` lines — partial output is not safe to send.

***

## Design Standards

The visual template reflects **Montezuma County / Mesa Verde, Colorado**:
warm earth tones, canyon reds, desert sage, and sandstone neutrals.

- **Palette:** Mesa Verde / Montezuma color scheme with dark mode overrides
- **Typography:** 18–20px body text, 1.7–1.75 line-height
- **Layout:** Table-based for email client compatibility (no CSS grid/flex)
- **Links:** All links are Zoho-safe: escaped first, then linkified;
  no trailing punctuation in `href`; clean `mailto:` for email addresses
- **Images:** Forward-slash URL paths only; identical path used for both
  `src` and `href`; proper `alt` text on every image

**Do not alter the approved visual design.** Accessibility and identity
choices are final.

***

## Accessibility Requirements

Chuck's List serves elderly and low-vision readers. These requirements are
non-negotiable:

- **Text size:** 18–20px body minimum, never smaller
- **Line spacing:** 1.7–1.75 line-height
- **Contrast:** Strong contrast throughout; no light-gray-on-white body text
- **Live text:** Important information must never be image-only
- **Link text:** Meaningful labels — never raw URLs as visible link text
- **Email client safety:** Renders correctly without JavaScript; table-based
  layout for broad client compatibility

***

## Error Handling Philosophy

The builder is designed to guide the operator, not just fail silently.

- Every `[WARN]` includes: row number, field name, bad value, and an exact
  fix instruction pointing back to `Chucks-list-MASTER.ods`
- `[ERROR]` lines block the pipeline — the operator must fix the data
- `[REMIND]` lines alert the operator to per-issue customization points
  (e.g., callout text not set for this issue)
- A build summary at the end lists every stage result
- A zero-item output after a successful-looking run is treated as a build
  failure (non-zero exit), not a blank issue
- **Do not upload to Zoho if any `[ERROR]` lines appeared in the run.**

***

## Engineering Standards

For anyone modifying this codebase:

1. **Read before touching.** Read the existing script in full before proposing
   changes. Validate against real CSV exports and real issue dates.

2. **Validate Python syntax after every edit:**
   ```bash
   py -m py_compile bulletins\preprocess_bulletin_text.py && echo OK
   ```

3. **Commit working state before editing:**
   ```bash
   git commit -am "working baseline before <description of change>"
   ```

4. **Full file replacements only.** Do not apply speculative partial patches.
   Provide the complete file and let the operator paste it.

5. **Path anchoring:** All script paths must use
   `Path(__file__).resolve().parent` — never `os.getcwd()`.

6. **Asset paths in HTML:** Always normalize to forward-slash URL syntax:
   ```python
   from urllib.parse import quote
   def to_web_path(path):
       return quote(Path(path).as_posix(), safe="/:._-")
   ```
   Use the same normalized path for both `src` and `href` on the same image.

7. **QUOTE_ALL on every DictWriter.** Without it, multi-line cells and cells
   containing `[]()` Markdown syntax may be written unquoted and corrupted
   on read-back.

8. **Split pipe-delimited fields before templating.** Never pass a
   pipe-joined string into `src=` or `href=`.

9. **Do not push to GitHub directly.** Provide code for the operator to
   paste and push manually after local testing.

***

## Known Limitations

- **No database backend.** All data lives in ODS/CSV. This is intentional
  for the current phase.
- **Windows-only.** Subprocess behavior and some path handling assumes Windows.
- **Zoho Campaigns dependency.** The builder produces HTML; delivery is
  handled entirely by Zoho Campaigns. No built-in send capability.
- **Events Markdown validation** is less strict than bulletins — bare URL/email
  checking uses a raw HTML tag scan, not the full `analyze_links` logic.
  Parity is a planned improvement.
- **No "Multiple Events" grouping** — rows sharing the same event title are
  not yet collapsed under one heading. Deferred until pipeline is stable.

***

## Roadmap

| Stage | Goal | Status |
|---|---|---|
| 1 | Document and stabilize current scripts | 🔄 In progress |
| 2 | Harden both preprocessors to parity (validation, date formats, exit codes) | 🔄 In progress |
| 3 | Mirror CSV data into a database | ⬜ Planned |
| 4 | Build admin UI on mcafeefarm.biz | ⬜ Planned |
| 5 | Generate website listings from database | ⬜ Planned |
| 6 | Generate email editions from database | ⬜ Planned |
| 7 | Retire CSV dependence when safe | ⬜ Planned |

***

## Guiding Principles

- **Boring beats clever.** Deterministic transforms over magic.
- **Plain text first.** Staff paste from email — the system adapts.
- **Explicit pipelines.** Bulletins and Events stay separate and documented.
- **Accessibility is core.** Not a polish pass — built in from the start.
- **One command.** The full local build runs from one CLI call.
- **Guide, don't just fail.** CLI output tells the operator what to fix and where.
- **Validate before redesigning.** Understand what exists before changing it.

***

*Chuck's List Builder — Montezuma County community publishing.*
*Reliable. Readable. One command.*