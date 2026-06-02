# Chuck's List Builder

**Chuck's List is a long-running community email list where Montezuma County
neighbors share local events, housing, services, and other happenings.**

Started and run by local farmer and community member Chuck McAfee, the list
has connected the Four Corners area for years — delivering announcements, swap
offers, housing leads, event notices, and local news directly to subscribers'
inboxes via Zoho Campaigns.

This repository is the production tooling that powers each issue.

---

## What This Repo Does

Staff maintain a master spreadsheet of submitted items. On publication day,
they export two CSV files and run one command. This builder reads those exports
and produces two complete, ready-to-send HTML emails:

| Edition | What it contains | Output file |
|---|---|---|
| **Bulletin** | Housing, swap market, services, community announcements | `chucks_bulletin_final_output.html` |
| **Events** | Upcoming community events, sorted by type | `chucks_events_final_output.html` |

Both emails are formatted for elderly and low-vision readers — large text, high
contrast, accessible links — and are safe for upload directly to Zoho Campaigns.

---

## Who This Is For

| Person | What they need |
|---|---|
| **Staff / operators** | Read [System/SYSTEM_README.md](System/SYSTEM_README.md) — the complete operator guide |
| **Developers / engineers** | Read [System/ENGINEER_GUIDE.md](System/ENGINEER_GUIDE.md) — architecture, contracts, bug history |
| **Anyone reporting a bug** | See [System/BUG_LIST.md](System/BUG_LIST.md) for the active bug ledger |

---

## Quick Start

```bash
py Chucks_List_Builder.py --issue-date YYYY-MM-DD
```

Before running, place the two CSV exports from Google Drive:
- `Bulletins.csv` → `ChucksBulletin/bulletins/`
- `Events.csv` → `ChucksEvents/events/`

Full pre-run checklist and CLI flag reference: [System/SYSTEM_README.md](System/SYSTEM_README.md)

---

## Active Goals

> The active goal is worked to completion before the next begins.
> Full goal definitions and engineering context live in
> [System/ENGINEER_GUIDE.md](System/ENGINEER_GUIDE.md).

| # | Goal | Status |
|---|---|---|
| **1** | **Refine all four primary documentation files** — README, SYSTEM_README, ENGINEER_GUIDE, BUG_LIST accurately reflect the current pipeline, short-term cPanel migration plan, and long-term GUI vision. | 🔄 **Active** |
| 2 | **Validate files and plan cPanel migration** — Identify all files, paths, configs, and Windows-specific assumptions that must change for a faithful server-side deployment. | ⬜ Next |
| 3 | **Execute migration to cPanel** — Move the pipeline to the server, keep behavior identical to local, document any differences. | ⬜ Staged |
| 4 | **BUG-017 — Fix nested output folder** — Resolve the `ChucksBulletin/ChucksBulletin/` double-nesting in both compilers. | ⬜ Staged |
| 5 | **Open bugs — BUG-018, BUG-019, BUG-023** — Section sort order, single-item TOC suppression, log path correction. | ⬜ Staged |

---

## Recent Fixes *(rolling last 10)*

| ID | Title | Area |
|---|---|---|
| BUG-016 | `Chucks_List_Builder.py` committed as shell artifact instead of Python source | `Chucks_List_Builder.py` |
| BUG-015 | Events TOC structure did not match bulletin TOC | `compile_events.py` |
| BUG-014 | Events compiler not accepting `--callout` / `--bottom-callout` flags | `compile_events.py` |
| BUG-013 | Events compiler skipping valid rows — unrecognized section values | `compile_events.py` |
| BUG-012 | `__main__` block called wrong function name and wrong kwarg | `Chucks_List_Builder.py` |
| BUG-011 | `run_stage` return displaced outside function body — SyntaxError on import | `Chucks_List_Builder.py` |
| BUG-010 | Non-UTF-8 subprocess bytes crash builder on Python 3.14 | `Chucks_List_Builder.py` |
| BUG-009 | Unicode arrow `→` in preprocess message crashes Windows console | Both preprocessors |
| BUG-008 | `--debug` flag not defined in argparse | `Chucks_List_Builder.py` |
| BUG-007 | False-positive Markdown validation errors on URLs with parentheses | `preprocess_bulletin_text.py` |

Full history and open items: [System/BUG_LIST.md](System/BUG_LIST.md)

---

## Where This Is Headed

The pipeline currently runs locally on a Windows machine. The plan, in three phases:

**Phase 1 — Now (stable):**
Local CLI pipeline on Windows. One command produces both HTML emails. This is production.

**Phase 2 — Near term:**
Migrate the existing CLI pipeline to a cPanel server (mcafeefarm.biz / ChucksList.info)
so the build can run from a hosted environment rather than a local machine. No new
features — same pipeline, new home.

**Phase 3 — Long term:**
Web-based GUI on mcafeefarm.biz and/or ChucksList.info. Staff log in, enter submissions,
and generate emails without touching a CSV or command line. Python + SQL backend.
This is months out.

---

## Repository Layout
ChucksList_Builder/
├── Chucks_List_Builder.py Entry point — runs both pipelines
├── ChucksBulletin/ Bulletin pipeline + Zoho staging
│ ├── bulletins/
│ │ ├── preprocess_bulletin_text.py
│ │ ├── compile_bulletin.py
│ │ └── [generated files — not committed]
│ └── Images/ Local only — never committed
├── ChucksEvents/ Events pipeline + Zoho staging
│ ├── events/
│ │ ├── preprocess_events_text.py
│ │ ├── compile_events.py
│ │ └── [generated files — not committed]
│ └── Images/ Local only — never committed
└── System/
├── SYSTEM_README.md Operator guide
├── ENGINEER_GUIDE.md Developer reference
├── BUG_LIST.md Bug ledger
└── logs/ Build logs (--log-to-file output)

text

---

## Current Pipeline Status

| Area | Status |
|---|---|
| Bulletin pipeline | ✅ Stable |
| Events pipeline | ✅ Stable |
| Date parsing (all LibreOffice formats) | ✅ Fixed |
| Markdown link rendering | ✅ Fixed |
| Windows path safety | ✅ Fixed |
| Multi-image fields | ✅ Fixed |
| Nested output folders (BUG-017) | 🔄 In Progress |
| Section ordering by size (BUG-018) | ⬜ Planned |
| Log path correction (BUG-023) | ⬜ Open |
| cPanel migration | ⬜ Next phase |
| Web GUI | ⬜ Long term |

For the full bug and punch list, see [System/BUG_LIST.md](System/BUG_LIST.md).

---

*Chuck's List — Montezuma County, Colorado.*
*Pipeline maintained by KuztomTech. Questions? See the operator guide or open an issue.*