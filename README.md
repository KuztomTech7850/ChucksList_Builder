# Chuck's List Builder

**Chuck's List is a long-running community email list where Montezuma County
neighbors share local events, housing, services, and other happenings.**

Started and run by local activist Chuck McAfee, the list has connected the Four
Corners area for years — delivering announcements, swap offers, housing leads,
event notices, and local news directly to subscribers' email inboxes.

This repository is the production tooling that powers each issue and is leading the future.

***

## What This Tool Does

Staff maintain a master spreadsheet of submitted items. The evening before publication day,
they export two CSV files and run one command. This builder reads those exports
and produces two complete, ready-to-send HTML emails:

| Edition | What it contains | Output file |
|---|---|---|
| **Bulletin** | Housing, swap market, services, community announcements | `chucks_bulletin_final_output.html` |
| **Events** | Upcoming community events, sorted by type | `chucks_events_final_output.html` |

Both emails are formatted for elderly and low-vision readers — large text, high
contrast, accessible links — and are safe for upload directly to Zoho Campaigns.

***

## What's Being Worked On

> This section is updated each session. It tells you where active development stands
> without requiring a deep dive into the technical files.

**Active Goal: Bug Cleanup — stabilizing the pipeline before server migration.**

Current focus:
- **BUG-023** — Fix log path (writes to wrong folder — one-line fix)
- **BUG-024** — Fix cross-validation paths (silent false-pass on every build — four-line fix)
- **BUG-017** — Fix nested staging folder (`ChucksBulletin/ChucksBulletin/`)

Up next: Migrate the pipeline to the cPanel server once the above are resolved.

For the full bug ledger and priority sequence: [System/BUG_LIST.md](System/BUG_LIST.md)

***

## Where This Is Headed

The pipeline currently runs locally on a Windows machine. The plan in three phases:

**Phase 1 — Now (stable):** Local CLI on Windows. One command, two HTML emails. This is production.

**Phase 2 — Near term:** Migrate the existing CLI to a cPanel server so the build
can run from a hosted environment. No new features — same pipeline, new home.

**Phase 3 — Long term:** Web-based GUI on mcafeefarm.biz / ChucksList.info. Staff log in,
enter submissions, and generate emails without touching a CSV or command line. Months out.

***

## Who Should Read What

| You are... | Start here |
|---|---|
| **An operator running a build** | [System/SYSTEM_README.md](System/SYSTEM_README.md) — full operator guide, pre-run checklist, CSV contracts, CLI flags |
| **A developer or engineer** | [System/ENGINEER_GUIDE.md](System/ENGINEER_GUIDE.md) — architecture, contracts, migration path, standards |
| **Reporting or reviewing a bug** | [System/BUG_LIST.md](System/BUG_LIST.md) — all known bugs, statuses, causes, and fixes |

***

*Chuck's List — Montezuma County, Colorado.*
*Pipeline maintained by KuztomTech. Questions? See the operator guide or open an issue.*