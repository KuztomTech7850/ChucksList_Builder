# Chuck's List Builder — Engineer Guide

> The technical almanac. Read this before touching any file in the codebase.

This guide is for developers — anyone modifying, debugging, extending, or
handing off this pipeline. The [README](README.md) covers operator use.
This document covers the *why* behind every technical decision.

---

## Table of Contents

- [Before You Touch Anything](#before-you-touch-anything)
- [Architecture Contracts](#architecture-contracts)
- [File Roles](#file-roles)
- [Path Anchoring](#path-anchoring)
- [The Escape-Then-Linkify Pipeline](#the-escape-then-linkify-pipeline)
- [Date Parsing](#date-parsing)
- [Image Handling](#image-handling)
- [CSV Contract](#csv-contract)
- [CLI Message Tags](#cli-message-tags)
- [Bug History](#bug-history)
- [Open Punch List](#open-punch-list)
- [Migration Path](#migration-path-local-cli--cpanel--web-gui)
- [Engineering Standards](#engineering-standards)
- [What Not to Do](#what-not-to-do)

---

## Before You Touch Anything

1. **Read the existing script in full.** Every file in this repo has a docstring
   that explains its role, contracts, and changelog. Read it.

2. **Commit a working baseline before editing:**
   ```bash
   git commit -am "working baseline before <description>"
   ```

3. **Validate Python syntax after every save:**
   ```bash
   py -m py_compile ChucksBulletin\bulletins\compile_bulletin.py && echo OK
   ```

4. **Test against real CSVs and a real issue date.** The bugs in this project's
   history were almost all caught only when real LibreOffice export data was used.

5. **Do not push to GitHub directly.** Provide code for the operator to paste
   and push manually after local testing.

---

## Architecture Contracts

These contracts must not be broken by any change:

1. **Two separate pipelines — keep them separate.**
   Bulletins and Events share no code, no state, and no intermediate files.
   Do not introduce shared modules, shared base classes, or merged stages.

2. **Preprocess and compile are intentionally separate stages.**
   Preprocess validates and normalizes; compile renders. Never combine them.

3. **Bulletin inclusion rule:** `Received <= issue_date <= Expires`
   **Events inclusion rule:** `Starts <= issue_date <= Expires`
   The Events CSV column is named `Expires`; it maps to `Ends` in `events_data.csv`.

4. **Bulletin section order is fixed. Urgent always first.**
   Non-Urgent sections are sorted by ascending item count after Urgent.
Urgent Bulletins
Housing Opportunities
Swap Market
Local Services & Help
Community Announcements

text

5. **CSV contract:** UTF-8, comma-delimited, `QUOTE_ALL`, Python `csv` with `newline=""`.

6. **Path anchoring:** ALL paths in all scripts use `Path(__file__).resolve().parent`.
Never `os.getcwd()`. Never hardcoded absolute paths.

7. **Date formats accepted (both preprocessors must handle all three):**
```python
DATE_RE_ISO   = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
DATE_RE_LONG  = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
```
All three must be defined at module level. `DATE_RE_LONG` handles the
`M/D/YYYY` format LibreOffice Calc commonly exports.

8. **Asset paths in HTML must use forward-slash URL syntax.** Never Windows
backslashes. Use this helper in both compilers:
```python
from urllib.parse import quote
def to_web_path(path):
    return quote(Path(path).as_posix(), safe="/:._-")
```
Both `href` and `src` for the same image must use the identical normalized path.

9. **Multi-image field contract:** The `Image` column accepts 1–3
pipe-separated filenames. Split on `|` and render one `<img>/<a>` pair
per entry. A 4th pipe-segment triggers `[WARN]` and is dropped.
Never emit `src="img1.png | img2.png"`.

10. **Image paths resolve relative to the pipeline's staging folder root.**
 `ChucksBulletin/` for bulletins, `ChucksEvents/` for events.
 `Images/`, `ChucksBulletin/Images/`, and `ChucksEvents/Images/` are all
 local-only and must never be committed to git.

11. **The `notes` column is never rendered and never written to intermediate CSVs.**
 It exists only in the raw source CSVs as a staff annotation field.

12. **CLI message tags are machine-parseable by design:**
 `[WARN]`, `[ERROR]`, `[REMIND]`, `[AUTO-FIX]`
 This structure supports a future GUI log panel. Do not change the tag format.

---

## File Roles

| File | Role |
|---|---|
| `Chucks_List_Builder.py` | Orchestration entrypoint — calls both pipelines via subprocess |
| `ChucksBulletin/bulletins/preprocess_bulletin_text.py` | Normalize, validate, and date-filter bulletin rows; write intermediate CSV |
| `ChucksBulletin/bulletins/compile_bulletin.py` | Render intermediate bulletin CSV into final HTML email |
| `ChucksEvents/events/preprocess_events_text.py` | Normalize, validate, and date-filter event rows; write intermediate CSV |
| `ChucksEvents/events/compile_events.py` | Render intermediate events CSV into final HTML email |
| `System/SYSTEM_README.md` | Operator guide — keep current after every significant change |
| `System/ENGINEER_GUIDE.md` | This file — technical almanac for developers |
| `System/BUG_LIST.md` | Bug ledger — IDs, status, area, symptom, cause/fix. Prioritizes stopper/functional bugs. Historical entries may use `Approximate` where exact details are unknown. |
| `System/config.py.template.py` | Template for local config (config.py itself is git-ignored) |
| `System/logs/` | Timestamped build logs written by `--log-to-file`; git-ignored |

**Generated files (not committed):**
- `bulletins_data.csv` / `events_data.csv` — intermediate CSVs
- `chucks_bulletin_final_output.html` / `chucks_events_final_output.html` — HTML outputs
- `Bulletins.csv` / `Events.csv` — raw source exports from Google Drive

---

## Path Anchoring

Every script resolves all paths from its own location:

```python
SCRIPT_DIR = Path(__file__).resolve().parent
PROJ_DIR   = SCRIPT_DIR.parent   # one level up from bulletins/ or events/
```

For the compilers, `PROJ_DIR` is `ChucksBulletin/` or `ChucksEvents/` —
the staging folder root. Output is written to both the script subfolder
and to `PROJ_DIR` directly so Zoho staging always has the latest file.

**The P1-C bug** was caused by compilers setting `OUTPUT_DIR = PROJ_DIR / "ChucksBulletin"`,
which from inside `ChucksBulletin/bulletins/` resolved to
`ChucksBulletin/ChucksBulletin/`. The fix is `OUTPUT_DIR = PROJ_DIR`.

---

## The Escape-Then-Linkify Pipeline

This is the single most important correctness guarantee in the compilers.
The order must never be reversed.
protect_markdown_links() → extract Label tokens before escaping
↓
html.escape() → escape all remaining < > & " '
↓
linkify_escaped_text() → linkify bare URLs/emails in the now-safe text
↓
restore_markdown_links() → reinsert the pre-built <a> tags

text

**Why this order?** If you linkify before escaping, the `<a href="...">` tags
you just built get their angle brackets escaped into `&lt;a href=...&gt;`.
If you escape before protecting Markdown links, the `[]()` syntax gets
mangled. The protect → escape → linkify → restore sequence handles both.

Bare URL linkification uses a bounded regex — no catastrophic backtracking,
and trailing punctuation is stripped from `href` values before use.

---

## Date Parsing

All three formats must be handled. The most common failure mode in this
project's history was a missing `DATE_RE_LONG` handler — LibreOffice Calc
exports dates as `M/D/YYYY` by default, which caused every row to be
skipped with no error when the handler was absent (Bug 4).

```python
DATE_RE_ISO   = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")       # 2026-06-07
DATE_RE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")   # 6/7/26
DATE_RE_LONG  = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")   # 6/7/2026
```

Two-digit years in `DATE_RE_SHORT` are interpreted as `2000 + YY`.

All three must be defined at module level in both preprocessors.
The parse function must try all three and return `None` (not raise) on
no match, so the caller can emit a `[WARN]` and skip the row gracefully.

---

## Image Handling

### Path normalization

```python
from urllib.parse import quote
def to_web_path(path: str) -> str:
    return quote(Path(path).as_posix(), safe="/:._-")
```

Apply to every path before writing it into `src=` or `href=`.
`safe="/:._-"` preserves path separators and common filename characters.

### Prefix enforcement

If an operator enters `photo.jpg` instead of `Images/photo.jpg`, the
compiler auto-prepends the prefix and emits a `[WARN]`. This is done in
`ensure_images_prefix()` in both compilers.

### Pipe-split contract

```python
raw_entries = [e.strip() for e in image_field.split("|") if e.strip()]
```

This split **must** happen before any path enters `src=` or `href=`.
Bug 6 was caused by passing the unsplit pipe-joined string directly into
the template.

### MAX_INLINE_IMAGES = 3

A 4th entry is dropped with a `[WARN]`. The operator is told to use a
link in the body text for the additional image.

---

## CSV Contract

Every `DictWriter` in this project must use:

```python
writer = csv.DictWriter(
    f,
    fieldnames=FIELDNAMES,
    quoting=csv.QUOTE_ALL,
    lineterminator="\n",
)
```

And every file open for CSV writing must use `newline=""`:

```python
with open(path, "w", newline="", encoding="utf-8") as f:
```

**Why QUOTE_ALL?** Bug 2 was caused by a missing `QUOTE_ALL` on the events
preprocessor. Multi-line cells and cells containing `[]()` Markdown syntax
were written unquoted; the compiler's `MARKDOWN_LINK_RE` failed to match
them on read-back, and links rendered as raw text.

---

## CLI Message Tags

| Tag | Use case | Behavior |
|---|---|---|
| `[WARN]` | Row skipped or field auto-corrected | Includes row, field, value, fix instruction |
| `[ERROR]` | Blocking failure | Pipeline stops; must fix before retrying |
| `[REMIND]` | Per-issue customization not set | Informs operator; does not stop pipeline |
| `[AUTO-FIX]` | Safe automatic correction applied | Logged; operator can review |

These are written to `stderr` by preprocessors and compilers so the
orchestrator (`Chucks_List_Builder.py`) can capture and forward them.
The Builder forwards `[REMIND]` lines from stderr as `WARNING` level logs.

---

## Bug History

See [BUG_LIST](BUG_LIST.md)

---

## README.md Maintenance Contract

The README is a living dashboard, not a one-time document. It must be updated
in the same commit as any change to goals or BUG_LIST status.

**After every session that closes a bug or advances a goal:**

| README section | When to update |
|---|---|
| **What's Being Worked On** | Any time the active goal or active bug list changes |
| **Where This Is Headed** | Only if a phase completes or the long-term plan changes — rarely |

**Rules:**
- "What's Being Worked On" should list the 3–5 bugs currently in flight, each with
  a one-line plain-English description. Remove a bug when it moves to Fixed.
- Keep the language non-technical — this section is for anyone landing on the repo,
  not just engineers.
- Never remove the "Up next" line — always name the next milestone so the status
  is self-evident without opening BUG_LIST.md.
- Full bug history, priority order, and status details live in
  [System/BUG_LIST.md](System/BUG_LIST.md) — do not duplicate them in the README.

---

## Open Punch List

### Priority 1 — Pipeline safety

**P1-C — Nested duplicate staging folders**
Compilers produce `ChucksBulletin/ChucksBulletin/` and `ChucksEvents/ChucksEvents/`
as a side effect of `OUTPUT_DIR` path resolution.
Fix: `OUTPUT_DIR = PROJ_DIR` in both compilers (was `PROJ_DIR / "ChucksBulletin"`).

### Priority 2 — Layout and UX

**P2-A — Section ordering by size (Bulletins)**
After Urgent, sort non-Urgent sections by ascending item count.
Change in `compile_bulletin.py` only.

**P2-B — TOC single-item hiding (both compilers)**
Conditionally suppress per-item TOC entries for sections with exactly one item.
Show the section heading only in those cases.

### Priority 3 — Content quality

**P3-A — Multiple Events grouping**
Rows sharing a title or lead image in "Hosts with Multiple Events" should be
grouped under one heading. Implement after P1 items are resolved.

**P3-B — Bulletin rotation within same-date groups**
When multiple bulletins in the same section share the same `Received` date,
rotate their order across issues so no submitter is always last.
Implement in `compile_bulletin.py` only. CSV-based for now; replace with
SQL at database migration.

**P3-C — "NEW" badge on first-issue entries**
Compare current intermediate CSV against the prior issue's intermediate CSV
(stored in `System/` with issue-date filenames). Items not present in the
prior run receive a `[NEW]` indicator in the HTML.
CSV-diff version for now; replace with SQL query at migration.

### Priority 4 — Deferred (post-database migration)

- P4-A: Interactive stage-confirm loop in CLI
- P4-B: Click-tracking stubs and error trend logging
- P4-C: Full layout/grouping/rotation refinement using SQL queries

---

---

## Migration Path: Local CLI → cPanel → Web GUI

This section documents the three-phase plan and the concrete engineering
work required at each transition. It is the authoritative reference for
anyone executing Phase 2 or planning Phase 3.

---

### Phase 1 — Local CLI (current production)

The pipeline runs on a local Windows machine. One command produces both
HTML emails. **This is production until Phase 2 is tested and verified
equivalent.**

Nothing in Phase 1 should be changed to accommodate Phase 2 or 3.
The local pipeline is the fallback if server deployment fails.

---

### Phase 2 — cPanel Migration (near term)

**Goal:** Run the identical Python pipeline on the cPanel server.
Same behavior, same output, new hosting environment. No new features.

#### Server environment (confirmed 2026-06-02)

| Item | Value |
|---|---|
| Host | server.cortezweb.com |
| OS | CentOS Linux 7.9 (CloudLinux ELS) |
| Architecture | x86_64 |
| cPanel version | 110.0 (build 124) |
| Shell access | SSH, user `mcafeefa`, home `/home/mcafeefa` |
| Python 3 on system PATH | ❌ Not available (`python3` not found) |
| Python 3 via CloudLinux alt | ✅ `/opt/alt/python311/bin/python3` — version 3.11.9 |
| Cron daemon | ✅ `crond` running — scheduled builds are possible |
| Console encoding | UTF-8 (`LANG=en_US.UTF-8`) |
| MySQL / MariaDB | 10.6.19 — available for Phase 3 |

#### Windows-specific assumptions that break on the server

Every item below must be addressed before the pipeline can run on cPanel.

| Assumption | Local behavior | Server behavior | Fix |
|---|---|---|---|
| `py` launcher | `py Chucks_List_Builder.py` works on Windows | `py` does not exist on Linux | Use explicit Python path (see virtualenv setup below) |
| `python3` on PATH | Not used locally | Also not on PATH on this server | Use virtualenv; invoke via `~/virtualenv/chuckslist/bin/python` |
| `subprocess.Popen('code "..."', shell=True)` | Opens VS Code on Windows | `code` does not exist on server; call will silently fail or error | Always pass `--no-open-vscode` on server; gate the Popen call on platform |
| `pathlib.Path` separator | Emits backslashes on Windows (mitigated by `to_web_path()`) | Emits forward slashes natively — no issue | No change needed; `to_web_path()` is still correct and should remain |
| Console encoding cp1252 | Possible on Windows (BUG-009 fixed known cases) | UTF-8 natively — no cp1252 risk | No change needed |
| Interactive callout wizard (`input()`) | Works in Windows terminal | Works in SSH terminal; **does not work in cron** | Pass `--callout` and `--bottom-callout` as CLI flags for any cron-triggered build; wizard is only for interactive use |
| VS Code HTML preview | Operator reviews output in VS Code before upload | No VS Code on server | Operator downloads HTML via SFTP or cPanel File Manager for review |

#### Phase 2 server setup — step by step

**Step 1 — Upload the repository**

Option A (preferred): Clone via Git if Git is available on the server:
```bash
cd /home/mcafeefa
git clone https://github.com/KuztomTech7850/ChucksList_Builder.git
```

Option B: Upload via SFTP or cPanel File Manager and extract.

Confirm the repo root is at `/home/mcafeefa/ChucksList_Builder/`.

**Step 2 — Create a Python virtualenv**

```bash
/opt/alt/python311/bin/python3 -m venv /home/mcafeefa/virtualenv/chuckslist
source /home/mcafeefa/virtualenv/chuckslist/bin/activate
python --version   # should report Python 3.11.9
```

The pipeline uses only the Python standard library (`argparse`, `csv`,
`pathlib`, `subprocess`, `re`, `logging`, `datetime`, `urllib.parse`).
No `pip install` step is required.

Deactivate when done:
```bash
deactivate
```

**Step 3 — Verify the pipeline resolves paths correctly**

```bash
cd /home/mcafeefa/ChucksList_Builder
/home/mcafeefa/virtualenv/chuckslist/bin/python Chucks_List_Builder.py --help
```

Expected: argparse help text. Any `ModuleNotFoundError` or path error
means the repo layout is wrong — confirm the working directory.

**Step 4 — Place CSV exports on the server**

Before running a build, the operator must upload both CSV exports:
- `Bulletins.csv` → `/home/mcafeefa/ChucksList_Builder/ChucksBulletin/bulletins/`
- `Events.csv` → `/home/mcafeefa/ChucksList_Builder/ChucksEvents/events/`

Upload via SFTP (FileZilla or equivalent) or cPanel File Manager.

**Step 5 — Run the build interactively (first test)**

```bash
cd /home/mcafeefa/ChucksList_Builder
/home/mcafeefa/virtualenv/chuckslist/bin/python Chucks_List_Builder.py \
  --issue-date 2026-06-07 \
  --callout "Your callout text here." \
  --no-open-vscode
```

`--no-open-vscode` is **mandatory** on the server. `--callout` is
required for any non-interactive invocation (cron or script).

**Step 6 — Retrieve the output HTML**

After a successful build, download via SFTP:
- `ChucksBulletin/chucks_bulletin_final_output.html`
- `ChucksEvents/chucks_events_final_output.html`

Then upload to Zoho Campaigns as normal.

**Step 7 — Optional: cron-triggered build**

If the operator wants the build to run on a schedule, add a cPanel Cron
job (`crond` is confirmed running). Example for every Tuesday at 8 AM
server time:
0 8 * * 2 cd /home/mcafeefa/ChucksList_Builder && /home/mcafeefa/virtualenv/chuckslist/bin/python Chucks_List_Builder.py --issue-date $(date +%Y-%m-%d) --callout "This week's issue." --no-open-vscode >> /home/mcafeefa/ChucksList_Builder/System/logs/cron.log 2>&1

text

Note: cron does not run the callout wizard. `--callout` must always be
provided. The issue date in a cron context is the run date — confirm
this matches the intended publication date.

#### Phase 2 acceptance criteria

The migration is considered complete when:
- [ ] Pipeline runs on the server without error against real CSV exports
- [ ] Output HTML is visually identical to a local build for the same CSV input
- [ ] `--no-open-vscode` confirmed working (no errors, no VS Code attempt)
- [ ] Log file written correctly to `System/logs/` with `--log-to-file`
- [ ] BUG-017 (nested output folder) resolved before or during migration
- [ ] Operator has confirmed the SFTP retrieval + Zoho upload workflow

**The local CLI pipeline remains production until all acceptance criteria
are met and the operator explicitly signs off.**

---

### Phase 3 — Web GUI (long term)

A browser-based interface for staff to manage submissions and generate
email editions without a terminal or CSV.

#### Architecture decision — language for Phase 3

The pipeline is currently Python. The server has PHP 8.3 natively
integrated with Apache/cPanel, which would require no additional runtime
setup. Both are viable for the Phase 3 backend.

| Option | Pros | Cons |
|---|---|---|
| **Python (Flask or FastAPI via WSGI)** | Reuse existing pipeline logic directly; no rewrite of preprocess/compile | Requires WSGI configuration in cPanel (Python App setup); slightly more cPanel config |
| **PHP** | Native to Apache/cPanel; zero additional runtime config; cPanel MySQL integration is seamless | Full rewrite of all pipeline logic in PHP; no code reuse from current scripts |

**Decision:** Deferred. Revisit when Phase 2 is stable. Either path is
valid — the choice will depend on operator preference and available
development resources at that time. Document the decision here when made.

#### Phase 3 scope (preliminary)

- Staff login (session-based auth)
- Submission entry form (replaces Google Sheets + CSV export)
- MySQL/MariaDB backend (confirmed available: MariaDB 10.6.19)
- Build trigger via web UI (replaces CLI command)
- Output preview in browser before Zoho upload
- CSV pipeline retired when server version is proven stable

**Timeline:** Several months out. No Phase 3 work begins until Phase 2
acceptance criteria are met.

---

## Engineering Standards

1. **Full file replacements only.** Provide the complete file for the
   operator to paste. No partial patches or diffs.

2. **Validate syntax after every edit:**
   ```bash
   py -m py_compile <file>.py && echo OK
   ```

3. **Commit working state before every edit session.**

4. **Never emit filesystem paths into HTML.** Always use `to_web_path()`.

5. **Never validate Markdown with raw parenthesis counting.**
   Parse `[label](target)` segments structurally.

6. **`QUOTE_ALL` on every `DictWriter`.** No exceptions.

7. **Split pipe-delimited fields before templating.** Never pass a
   pipe-joined string into `src=` or `href=`.

8. **Zero-item preprocess output that exits 0 is a silent build failure.**
   Exit non-zero when `passing == 0` and `skipped > 0`.

9. **Do not push to GitHub directly.** Provide code; let operator push
   after local testing.

---

## What Not to Do

- Do not redesign toward the database/GUI end state in the current CLI
- Do not replace Zoho Campaigns as the send engine
- Do not collapse Bulletins and Events into one pipeline
- Do not alter the approved visual design (colors, fonts, layout)
- Do not invent abstraction layers not already present
- Do not commit images to git under any circumstances
- Do not use `os.getcwd()` for path resolution
- Do not reverse the escape-then-linkify order

---

*Chuck's List Builder — Engineer Guide*
*Read it. Know it. Then go change things carefully.*