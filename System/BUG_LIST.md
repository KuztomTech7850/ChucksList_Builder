# Chuck's List Builder — Bug Ledger

> Canonical record of all known bugs, their status, and fix summaries.
> Resolved items remain as permanent history. Append new entries at the
> bottom of the appropriate section. Never delete resolved entries.
> Update status in-place when a bug moves states.
>
> Cross-referenced with commit history starting 2026-05-30.

---

## Format Reference

| Field | Acceptable values |
|---|---|
| ID | `BUG-NNN` (sequential) |
| Title | One short phrase |
| Status | `Open` / `In Progress` / `Fixed` / `Deferred` |
| Area | File or subsystem name |
| Symptom | 1–2 sentences describing what the operator sees |
| Cause / Fix | Brief explanation; `Approximate` if reconstructed from history |

---

## In Progress

### BUG-017
| Field | Value |
|---|---|
| **ID** | BUG-017 |
| **Title** | Nested duplicate staging folder created on every build |
| **Status** | In Progress |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | Compilers produce `ChucksBulletin/ChucksBulletin/` and `ChucksEvents/ChucksEvents/` as a side effect of `OUTPUT_DIR` path resolution. The staging copy is nested one level too deep and is not found by the Zoho upload workflow. |
| **Cause / Fix** | `OUTPUT_DIR` was set to `PROJ_DIR / "ChucksBulletin"` inside `compile_bulletin.py`. Since `PROJ_DIR` resolves to `ChucksBulletin/` from inside `ChucksBulletin/bulletins/`, the join creates the nested path. Fix: change `OUTPUT_DIR = PROJ_DIR` in both compilers. **Not yet applied.** |

---

## Open — Planned

### BUG-018
| Field | Value |
|---|---|
| **ID** | BUG-018 |
| **Title** | Bulletin sections not sorted by ascending item count after Urgent |
| **Status** | Open |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Non-Urgent bulletin sections appear in CSV order rather than sorted smallest-to-largest. Short sections may appear after long ones, making the email harder to scan. |
| **Cause / Fix** | No sort applied post-Urgent. Fix: after pinning Urgent, sort remaining sections by `len(items)` ascending before rendering. Change confined to `compile_bulletin.py` only. |

### BUG-019
| Field | Value |
|---|---|
| **ID** | BUG-019 |
| **Title** | TOC shows per-item entries for single-item sections |
| **Status** | Open |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | When a section has exactly one item, the TOC shows a redundant sub-entry under the section heading. The section heading alone is sufficient. |
| **Cause / Fix** | TOC generation emits item links unconditionally. Fix: suppress per-item TOC entries when `len(section_items) == 1`. |

### BUG-023
| Field | Value |
|---|---|
| **ID** | BUG-023 |
| **Title** | Log path hardcoded to `logs/` instead of `System/logs/` |
| **Status** | Open |
| **Area** | `Chucks_List_Builder.py` — `setup_logging()` |
| **Symptom** | When `--log-to-file` is used, the build log is written to `ChucksList_Builder/logs/` (repo root). The operator moved the logs folder to `ChucksList_Builder/System/logs/`. Logs either land in the wrong place or a new `logs/` directory is silently created at repo root. |
| **Cause / Fix** | **Confirmed not yet fixed as of 2026-06-05.** `setup_logging()` hardcodes `logs_dir = PROJ_DIR / "logs"`. Change to `PROJ_DIR / "System" / "logs"`. One-line fix. |

### BUG-024
| Field | Value |
|---|---|
| **ID** | BUG-024 |
| **Title** | **Confirmed not yet fixed as of 2026-06-05.** `INTERMEDIATE_CSV` and `OUTPUT_FILES` paths resolve to non-existent repo-root subdirectories |
| **Status** | Open |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | On every build, two phantom directories (`ChucksList_Builder/bulletins/` and `ChucksList_Builder/events/`) are created at repo root. The CSV→HTML cross-validation silently finds nothing because `INTERMEDIATE_CSV` and `OUTPUT_FILES` point there instead of to `ChucksBulletin/bulletins/` and `ChucksEvents/events/`. Validation always reports "no data to compare" — a false pass. |
| **Cause / Fix** | `PROJ_DIR` in the entry point resolves to the repo root. `INTERMEDIATE_CSV` and `OUTPUT_FILES` are defined as `PROJ_DIR / "bulletins" / ...` and `PROJ_DIR / "events" / ...`, which miss the `ChucksBulletin/` and `ChucksEvents/` parent folders. Fix: change both dicts to `PROJ_DIR / "ChucksBulletin" / "bulletins" / ...` and `PROJ_DIR / "ChucksEvents" / "events" / ...`. Four path corrections in `Chucks_List_Builder.py`. |

### BUG-025
| Field | Value |
|---|---|
| **ID** | BUG-025 |
| **Title** | Callout `[REMIND]` not firing on events output |
| **Status** | Open |
| **Area** | `Chucks_List_Builder.py` — `emit_callout_reminders()` |
| **Symptom** | The `[REMIND]` callout signal appears for bulletins but not for the events pipeline. Operator has no visual signal to review or override the default callout text when compiling events. Needs verification (`##double check##`). |
| **Cause / Fix** | `emit_callout_reminders()` may not be called (or may short-circuit) for the events branch. Verify the orchestrator calls the reminder for both pipelines and that `compile_events.py` respects `--callout` / `--bottom-callout` in all code paths. |

### BUG-026
| Field | Value |
|---|---|
| **ID** | BUG-026 |
| **Title** | Inverted Markdown link syntax `()[]` not auto-corrected |
| **Status** | Open |
| **Area** | `preprocess_bulletin_text.py`, `preprocess_events_text.py` |
| **Symptom** | Operators occasionally enter links in the flipped form `(url)[Label]` instead of the correct `[Label](url)`. The compiler emits a validation `[ERROR]` but takes no corrective action, leaving the link broken in output HTML. |
| **Cause / Fix** | Preprocessors validate but do not auto-fix known transposition patterns. Add an auto-correct pass before validation: detect `\(([^)]+)\)\[([^\]]+)\]` and rewrite to `[\2](\1)`. Emit a `[WARN AUTO-FIX]` log line per correction so the operator is informed. This is a clear, unambiguous flip with no false-positive risk. |

### BUG-027
| Field | Value |
|---|---|
| **ID** | BUG-027 |
| **Title** | "Hosts with Multiple Events" grouping renders each event as an independent item |
| **Status** | Open |
| **Area** | `compile_events.py` |
| **Symptom** | When a host has multiple events, each row renders as a standalone item under the section rather than being visually grouped under a shared host heading. The section heading exists but sub-grouping by host is absent, making the layout difficult to scan. Related to BUG-020. |
| **Cause / Fix** | No host-level sub-grouping in current compiler. Proposed approach: add a script-level tagging pass in the preprocessor that detects rows sharing the same host name (or lead image) and stamps them with a shared `HostGroup` tag. Compiler then renders a host-level `<h3>` heading followed by indented entries for each group. Operator notes that host identification may rely on keywords already present in event titles — design to be finalized. |

### BUG-028
| Field | Value |
|---|---|
| **ID** | BUG-028 |
| **Title** | Multi-image `[WARN]` fires incorrectly — pipe delimiter is valid syntax |
| **Status** | Open |
| **Area** | `compile_bulletin.py`, `compile_events.py` — `build_image_html()` |
| **Symptom** | When an item contains a pipe-delimited image list (e.g., `Images/a.jpg\|Images/b.jpg\|Images/c.jpg`), a `[WARN]` is emitted suggesting an error condition. The pipe is intentional syntax indicating multiple images; the warning is misleading noise in the build log. |
| **Cause / Fix** | Remove or reclassify the warning in `build_image_html()`. If a maximum image count per item is desired, document it explicitly and only warn above that threshold with a clearer message. Note: BUG-006's resolved entry references this `[WARN]` — it was correct for the original single-string bug but is now outdated behavior. |

### BUG-029
| Field | Value |
|---|---|
| **ID** | BUG-029 |
| **Title** | Callout message requires two trailing newlines for single-line intent |
| **Status** | Open |
| **Area** | `compile_bulletin.py`, `compile_events.py` — callout block renderer |
| **Symptom** | The callout block requires two `\n` characters at the end of the message to render as a clean single-line callout. Operators entering natural single-line text get malformed spacing in HTML output. |
| **Cause / Fix** | Callout renderer likely emits an extra blank line unconditionally. Fix: strip trailing whitespace/newlines from callout text in the renderer before wrapping in HTML so operators can enter clean single-line text without workarounds. |

### BUG-030
| Field | Value |
|---|---|
| **ID** | BUG-030 |
| **Title** | VS Code opens application rather than specific output files |
| **Status** | Open |
| **Area** | `Chucks_List_Builder.py` — post-build file-open logic |
| **Symptom** | After a successful build, the orchestrator launches VS Code (the application) but does not pass the output files as arguments. Operator must manually navigate to and open the compiled HTML files. |
| **Cause / Fix** | The `code` CLI call is missing file path arguments. Fix: pass specific output file paths to `subprocess.run(["code", str(output_file_1), str(output_file_2), ...])` so VS Code opens directly to the compiled files on build completion. |

### BUG-031
| Field | Value |
|---|---|
| **ID** | BUG-031 |
| **Title** | Final output files duplicated outside staging folder |
| **Status** | Open |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | When final HTML files are written, duplicate copies are created outside the intended staging folder. Expected sole destination: `C:\Users\Travis\Desktop\ChucksList\ChucksList_Builder\Chucks*`. Extra copies create ambiguity about which file is authoritative for Zoho upload. Related to BUG-017. |
| **Cause / Fix** | Output path logic writes to multiple destinations. Fix: audit all `open(..., "w")` calls in both compilers and consolidate to the `Chucks*` staging path only. Cross-reference with BUG-017 fix to avoid reintroducing the nested-directory issue. |

### BUG-032
| Field | Value |
|---|---|
| **ID** | BUG-032 |
| **Title** | TOC group headers not visually distinct; items not indented under group |
| **Status** | Open |
| **Area** | `compile_bulletin.py`, `compile_events.py` — TOC renderer |
| **Symptom** | TOC section group headings and their child item links render at the same visual level. Groups are not styled as prominent headers with items indented beneath them, making the TOC difficult to scan. A "New" prefix on first-appearance entries would also help readers identify fresh content. |
| **Cause / Fix** | TOC HTML uses a flat list structure. Fix: (1) render each group as a styled `<strong>` or `<h4>` TOC header; (2) indent child item links under their group via `margin-left` or a nested `<ul>`; (3) prepend "New" to TOC entries for first-appearance items (coordinate with BUG-022 when available; a placeholder hook is acceptable in the interim). |

### BUG-033
| Field | Value |
|---|---|
| **ID** | BUG-033 |
| **Title** | Inline formatting stripped from entries even when source cell is styled |
| **Status** | Open |
| **Area** | `preprocess_bulletin_text.py`, `preprocess_events_text.py` — CSV ingestion |
| **Symptom** | Rich text formatting (bold, italic, centering) applied to source cells in LibreOffice/Google Sheets is not preserved in compiled HTML output. CSV is a plain-text format — cell styling metadata is never written to `.csv` and cannot be recovered at compile time. |
| **Cause / Fix** | Short-term: document the limitation; encourage operators to use inline Markdown (`**bold**`, `_italic_`, `<center>...</center>`) in cell text rather than spreadsheet cell formatting. Long-term: a database + cron job + direct email-to-database ingestion pipeline would capture structured input without CSV formatting loss — Phase 3 architectural item, tracked alongside the database migration. |

---

## Deferred — Post-Phase 2

### BUG-020
| Field | Value |
|---|---|
| **ID** | BUG-020 |
| **Title** | Multiple Events not grouped under a shared heading |
| **Status** | Deferred |
| **Area** | `compile_events.py` |
| **Symptom** | Event rows sharing a title or lead image in "Hosts with Multiple Events" each render as independent items rather than grouped under one heading. |
| **Cause / Fix** | No grouping logic in current compiler. Planned after BUG-017 is resolved. |

### BUG-021
| Field | Value |
|---|---|
| **ID** | BUG-021 |
| **Title** | No rotation of same-date bulletin items within a section |
| **Status** | Deferred |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Multiple bulletins in the same section with the same `Received` date always appear in CSV order. The same submitter is always first or last across every issue. |
| **Cause / Fix** | No rotation logic. CSV-based rotation planned for current phase; replace with SQL query at database migration. Deferred until BUG-017 and Phase 2 are resolved. |

### BUG-022
| Field | Value |
|---|---|
| **ID** | BUG-022 |
| **Title** | No `NEW` badge on first-appearance bulletin items |
| **Status** | Deferred |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Items appearing for the first time are not visually distinguished from returning items. |
| **Cause / Fix** | No prior-issue comparison logic. Plan: compare current intermediate CSV against the prior issue's stored intermediate CSV. CSV-diff for current phase; replace with SQL at Phase 3 migration. Deferred until BUG-017 and Phase 2 are resolved. |

---

## Resolved

### BUG-001
| Field | Value |
|---|---|
| **ID** | BUG-001 |
| **Title** | Callout boxes never prompted; operator had no signal to customize |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Builder called compilers with no `--callout` or `--bottom-callout` argument. Default callout text was used silently every issue with no reminder to the operator. |
| **Cause / Fix** | `emit_callout_reminders()` added to orchestrator. `--callout` and `--bottom-callout` flags wired through entrypoint to both compilers. `[REMIND]` tag emitted when flags are absent so operator sees the default text and the exact override flag. |

### BUG-002
| Field | Value |
|---|---|
| **ID** | BUG-002 |
| **Title** | Markdown links rendered as raw text in events email |
| **Status** | Fixed |
| **Area** | `ChucksEvents/events/preprocess_events_text.py` |
| **Symptom** | Links written as `[Label](url)` in the Events CSV appeared as literal bracketed text in the output HTML rather than as clickable `<a>` tags. |
| **Cause / Fix** | `preprocess_events_text.py` was missing `QUOTE_ALL` on its `DictWriter`. Cells containing `[]()` Markdown syntax were written unquoted; the compiler's `MARKDOWN_LINK_RE` failed to match on read-back. Fix: `quoting=csv.QUOTE_ALL` added to events preprocessor `DictWriter`. |

### BUG-003
| Field | Value |
|---|---|
| **ID** | BUG-003 |
| **Title** | "here" link not rendering in events output |
| **Status** | Fixed |
| **Area** | `ChucksEvents/events/preprocess_events_text.py` |
| **Symptom** | A specific `[here](url)` Markdown link in an events item failed to render as a hyperlink. |
| **Cause / Fix** | Approximate — root cause was the same missing `QUOTE_ALL` as BUG-002. Resolved by the same fix. |

### BUG-004
| Field | Value |
|---|---|
| **ID** | BUG-004 |
| **Title** | All bulletins skipped; zero-item output exits 0 silently |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py` (originally); both preprocessors (final fix) |
| **Symptom** | Running the builder against a real LibreOffice CSV export produced zero items. No error was reported; the pipeline exited 0 as if successful and produced a blank-issue HTML. |
| **Cause / Fix** | `parse_date()` had no handler for the `M/D/YYYY` format LibreOffice Calc exports by default (e.g., `5/21/2026`). Every row hit the fallthrough and was silently skipped. Fix: `DATE_RE_LONG = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")` added at module level in both preprocessors. Zero-item output now exits non-zero to prevent a silent blank issue. |

### BUG-005
| Field | Value |
|---|---|
| **ID** | BUG-005 |
| **Title** | Windows backslash paths written into HTML `src` and `href` |
| **Status** | Fixed |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | Image `src` and `href` attributes in HTML output contained Windows-style backslash paths (e.g., `Images\photo.jpg`). Images failed to load in browsers and Zoho Campaigns. |
| **Cause / Fix** | `pathlib.Path` on Windows emits backslashes. Fix: `to_web_path()` helper added to both compilers using `Path.as_posix()` + `urllib.parse.quote(..., safe="/:._-")`. Both `href` and `src` for the same image now use the identical normalized forward-slash path. |

### BUG-006
| Field | Value |
|---|---|
| **ID** | BUG-006 |
| **Title** | Pipe-delimited image field not split before render |
| **Status** | Fixed |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | When an item had multiple images in the CSV (e.g., `Images/a.jpg\|Images/b.jpg`), the entire pipe-joined string was passed directly into `src=`, producing a broken image tag. |
| **Cause / Fix** | `build_image_html()` in both compilers now splits the `Image` field on `\|` before rendering. Each entry gets its own `<img>/<a>` pair. A 4th pipe-segment triggers `[WARN]` and is dropped. |

### BUG-007
| Field | Value |
|---|---|
| **ID** | BUG-007 |
| **Title** | False-positive Markdown validation errors on valid URLs containing parentheses |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py` |
| **Symptom** | Bulletin items containing URLs with balanced parentheses in the body triggered `[ERROR]` Markdown validation failures even though the links were correctly formed. |
| **Cause / Fix** | Validator used naive parenthesis counting across the entire `Body` field. Any URL containing `( )` fired a false positive. Fix: replaced with segment-targeted `[label](target)` structural parsing that validates each Markdown link token individually. |

### BUG-008
| Field | Value |
|---|---|
| **ID** | BUG-008 |
| **Title** | `--debug` flag not defined in argparse |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Passing `--debug` on the CLI caused an `unrecognized arguments` error and immediate exit. |
| **Cause / Fix** | `add_argument("--debug", action="store_true")` was missing from the argparse setup. Added. |

### BUG-009
| Field | Value |
|---|---|
| **ID** | BUG-009 |
| **Title** | Unicode arrow `→` in preprocess success message crashes Windows console |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py`, `preprocess_events_text.py` |
| **Symptom** | On Windows with cp1252 console encoding, the preprocess scripts crashed when printing the OK status message containing a literal `→` (U+2192) character. |
| **Cause / Fix** | Replaced `→` with ASCII `->` in both preprocess scripts' success print statements. |

### BUG-010
| Field | Value |
|---|---|
| **ID** | BUG-010 |
| **Title** | Non-UTF-8 bytes in subprocess output crash builder on Python 3.14 |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | On Python 3.14, the subprocess reader raised `UnicodeDecodeError` when compile scripts emitted cp1252 `0xa0` non-breaking space bytes from CSV source data. `result.stderr` was left as `None`, crashing the builder after the HTML was already written. |
| **Cause / Fix** | Added `errors="replace"` to `subprocess.run()`. Added `None` guards on `stdout` and `stderr` before `.strip()`. Returns empty string fallback instead of `None` to caller. |

### BUG-011
| Field | Value |
|---|---|
| **ID** | BUG-011 |
| **Title** | `run_stage` return statement displaced outside function body — SyntaxError on import |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Repeated in-place patches caused the `return` statement inside `run_stage()` to be pushed outside the function body, producing a `SyntaxError` at import time. Pipeline appeared to run but did nothing; exit code 0. |
| **Cause / Fix** | Full rewrite of `Chucks_List_Builder.py` from scratch. Indentation corrected throughout. |

### BUG-012
| Field | Value |
|---|---|
| **ID** | BUG-012 |
| **Title** | `__main__` block called wrong function name and used wrong kwarg |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | The bulletin pipeline's `__main__` call invoked `compile_events(...)` instead of `compile_bulletins(...)`, and passed `callout=` instead of the correct `top_callout=`. Bulletins were never compiled regardless of CLI flags. A 3-space indent on `parser.add_argument("--callout"...)` also caused an `IndentationError` at import time. |
| **Cause / Fix** | Corrected function name to `compile_bulletins(...)`, kwarg to `top_callout=args.callout`, and indent to 4 spaces. |

### BUG-013
| Field | Value |
|---|---|
| **ID** | BUG-013 |
| **Title** | Events compiler skipping valid rows due to unrecognized section values |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | Valid event rows with `Section` values of `Single`, `Multiple`, or `Recurring` were silently skipped. Output HTML was empty or nearly empty even with a populated `events_data.csv`. |
| **Cause / Fix** | Approximate — section grouping logic was checking for values that did not match the canonical names from the preprocessor. Fix: updated to accept `Single Events`, `Hosts with Multiple Events`, `Recurring Events`. |

### BUG-014
| Field | Value |
|---|---|
| **ID** | BUG-014 |
| **Title** | Events compiler not accepting `--callout` / `--bottom-callout` CLI flags |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | Passing `--callout` or `--bottom-callout` to the builder had no effect on events output. Events email always showed hardcoded default callout text. |
| **Cause / Fix** | `compile_events.py` did not define these flags in its argparse setup. Added with safe defaults matching the bulletin compiler pattern. |

### BUG-015
| Field | Value |
|---|---|
| **ID** | BUG-015 |
| **Title** | Events TOC structure did not match bulletin TOC |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | The events email used a flat TOC list rather than the section-heading-with-linked-items structure used in the bulletin. Harder to scan in an email client. |
| **Cause / Fix** | Events compiler TOC rebuilt to match bulletin pattern: section headings are linked anchors; item titles are listed under each section heading. |

### BUG-016
| Field | Value |
|---|---|
| **ID** | BUG-016 |
| **Title** | `Chucks_List_Builder.py` committed containing shell-command artifact instead of Python source |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | File contained a shell command artifact rather than valid Python source. Script failed to execute entirely. |
| **Cause / Fix** | File replaced with correct Python source. |

---

*Chuck's List Builder — Bug Ledger*
*Append new entries at the bottom of the appropriate section. Never delete resolved entries.*