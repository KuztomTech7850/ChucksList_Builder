# Chuck's List Builder — Bug Ledger

> Canonical record of all known bugs, their status, and fix summaries.
> Resolved items remain as permanent history. Append new entries at the
> bottom of the appropriate section. Never delete resolved entries.
> Update status in-place when a bug moves states.
>
> Cross-referenced with commit history starting 2026-05-30.
>
> **Next sequential ID: BUG-026**
> (BUG-020 through BUG-025 are the last valid entries before a cleanup
> on 2026-06-05 removed incorrectly created duplicate/overlap bugs.
> See notes in each affected entry.)

***

## Format Reference

| Field | Acceptable values |
|---|---|
| ID | `BUG-NNN` (sequential) |
| Title | One short phrase |
| Status | `Open` / `In Progress` / `Fixed` / `Deferred` |
| Area | File or subsystem name |
| Symptom | 1–2 sentences describing what the operator sees |
| Cause / Fix | Brief explanation; `Approximate` if reconstructed from history |

***

## In Progress

### BUG-017
| Field | Value |
|---|---|
| **ID** | BUG-017 |
| **Title** | Nested duplicate staging folder created on every build |
| **Status** | In Progress |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | Compilers produce `ChucksBulletin/ChucksBulletin/` and `ChucksEvents/ChucksEvents/` as a side effect of `OUTPUT_DIR` path resolution. The staging copy is nested one level too deep and is not found by the Zoho upload workflow. Also causes duplicate output files outside the intended staging folder (see BUG-031 note below). |
| **Cause / Fix** | `OUTPUT_DIR` was set to `PROJ_DIR / "ChucksBulletin"` inside `compile_bulletin.py`. Since `PROJ_DIR` resolves to `ChucksBulletin/` from inside `ChucksBulletin/bulletins/`, the join creates the nested path. Fix: `OUTPUT_DIR = PROJ_DIR` in both compilers. **Not yet applied.** |
| **Note** | Fixing this also resolves the duplicate output file issue previously tracked as BUG-031. Audit all `open(..., "w")` calls in both compilers during the fix to confirm consolidation to the correct staging path. |

***

## Open — Planned

Priority order: work top to bottom. Do not skip ahead.

### BUG-023
| Field | Value |
|---|---|
| **ID** | BUG-023 |
| **Title** | Log path hardcoded to `logs/` instead of `System/logs/` |
| **Status** | Open |
| **Priority** | 1 — one-line fix, zero risk |
| **Area** | `Chucks_List_Builder.py` — `setup_logging()` |
| **Symptom** | When `--log-to-file` is used, the build log is written to `ChucksList_Builder/logs/` (repo root). The operator moved the logs folder to `ChucksList_Builder/System/logs/`. Logs either land in the wrong place or a new `logs/` directory is silently created at repo root. |
| **Cause / Fix** | **Confirmed not yet fixed as of 2026-06-05.** `setup_logging()` hardcodes `logs_dir = PROJ_DIR / "logs"`. Change to `PROJ_DIR / "System" / "logs"`. One-line fix. |

### BUG-024
| Field | Value |
|---|---|
| **ID** | BUG-024 |
| **Title** | `INTERMEDIATE_CSV` and `OUTPUT_FILES` paths resolve to non-existent repo-root subdirectories |
| **Status** | Open |
| **Priority** | 2 — four-line fix, zero risk |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | On every build, two phantom directories (`ChucksList_Builder/bulletins/` and `ChucksList_Builder/events/`) are created at repo root. The CSV→HTML cross-validation silently finds nothing because `INTERMEDIATE_CSV` and `OUTPUT_FILES` point there instead of to `ChucksBulletin/bulletins/` and `ChucksEvents/events/`. Validation always reports "no data to compare" — a false pass. |
| **Cause / Fix** | **Confirmed not yet fixed as of 2026-06-05.** `PROJ_DIR` in the entry point resolves to the repo root. `INTERMEDIATE_CSV` and `OUTPUT_FILES` are defined as `PROJ_DIR / "bulletins" / ...` and `PROJ_DIR / "events" / ...`, missing the `ChucksBulletin/` and `ChucksEvents/` parent folders. Fix: change both dicts to `PROJ_DIR / "ChucksBulletin" / "bulletins" / ...` and `PROJ_DIR / "ChucksEvents" / "events" / ...`. Four path corrections. |

### BUG-030
| Field | Value |
|---|---|
| **ID** | BUG-030 |
| **Title** | VS Code opens application rather than specific output files |
| **Status** | Open |
| **Priority** | 3 — simple CLI argument fix |
| **Area** | `Chucks_List_Builder.py` — post-build file-open logic |
| **Symptom** | After a successful build, the orchestrator launches VS Code (the application) but does not pass the output files as arguments. Operator must manually navigate to and open the compiled HTML files. |
| **Cause / Fix** | The `code` CLI call is missing file path arguments. Fix: pass specific output file paths to `subprocess.run(["code", str(output_file_1), str(output_file_2), ...])` so VS Code opens directly to the compiled files on build completion. |

### BUG-029
| Field | Value |
|---|---|
| **ID** | BUG-029 |
| **Title** | Callout message requires two trailing newlines for single-line intent |
| **Status** | Open |
| **Priority** | 4 — renderer strip, low risk |
| **Area** | `compile_bulletin.py`, `compile_events.py` — callout block renderer |
| **Symptom** | The callout block requires two `\n` characters at the end of the message to render as a clean single-line callout. Operators entering natural single-line text get malformed spacing in HTML output. |
| **Cause / Fix** | Callout renderer likely emits an extra blank line unconditionally. Fix: strip trailing whitespace/newlines from callout text before wrapping in HTML. |

### BUG-025
| Field | Value |
|---|---|
| **ID** | BUG-025 |
| **Title** | Callout `[REMIND]` not firing on events output |
| **Status** | Open |
| **Priority** | 5 — verify code path before fixing |
| **Area** | `Chucks_List_Builder.py` — `emit_callout_reminders()` |
| **Symptom** | The `[REMIND]` callout signal appears for bulletins but not for the events pipeline. Operator has no visual signal to review or override the default callout text when compiling events. |
| **Cause / Fix** | `emit_callout_reminders()` may not be called (or may short-circuit) for the events branch. **Verify first:** confirm whether the orchestrator calls the reminder for both pipelines and whether `compile_events.py` respects `--callout` / `--bottom-callout` in all code paths. Fix only after code path is confirmed. |

### BUG-026
| Field | Value |
|---|---|
| **ID** | BUG-026 |
| **Title** | Inverted Markdown link syntax `()[]` not auto-corrected |
| **Status** | Open |
| **Priority** | 6 |
| **Area** | `preprocess_bulletin_text.py`, `preprocess_events_text.py` |
| **Symptom** | Operators occasionally enter links in the flipped form `(url)[Label]` instead of the correct `[Label](url)`. The compiler emits a validation `[ERROR]` but takes no corrective action, leaving the link broken in output HTML. |
| **Cause / Fix** | Preprocessors validate but do not auto-fix known transposition patterns. Add an auto-correct pass before validation: detect `\(([^)]+)\)\[([^\]]+)\]` and rewrite to `[\2](\1)`. Emit a `[WARN AUTO-FIX]` log line per correction so the operator is informed. |

### BUG-019
| Field | Value |
|---|---|
| **ID** | BUG-019 |
| **Title** | TOC shows per-item entries for single-item sections |
| **Status** | Open |
| **Priority** | 7 |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | When a section has exactly one item, the TOC shows a redundant sub-entry under the section heading. The section heading alone is sufficient. |
| **Cause / Fix** | TOC generation emits item links unconditionally. Fix: suppress per-item TOC entries when `len(section_items) == 1`. |

### BUG-018
| Field | Value |
|---|---|
| **ID** | BUG-018 |
| **Title** | Bulletin sections not sorted by ascending item count after Urgent |
| **Status** | Open |
| **Priority** | 8 |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Non-Urgent bulletin sections appear in CSV order rather than sorted smallest-to-largest. Short sections may appear after long ones, making the email harder to scan. |
| **Cause / Fix** | No sort applied post-Urgent. Fix: after pinning Urgent, sort remaining sections by `len(items)` ascending before rendering. Change confined to `compile_bulletin.py` only. |

### BUG-028
| Field | Value |
|---|---|
| **ID** | BUG-028 |
| **Title** | Multi-image `[WARN]` fires on valid pipe-delimited syntax — reconcile with BUG-006 behavior |
| **Status** | Open |
| **Priority** | 9 — requires design decision before fix |
| **Area** | `compile_bulletin.py`, `compile_events.py` — `build_image_html()` |
| **Symptom** | When an item contains a pipe-delimited image list (e.g., `Images/a.jpg\|Images/b.jpg\|Images/c.jpg`), a `[WARN]` is emitted suggesting an error condition. The pipe is intentional syntax; the warning is misleading noise. |
| **Cause / Fix** | BUG-006's resolved fix documented that a 4th pipe-segment triggers `[WARN]` and is dropped — that's intended behavior. The issue is that the warn fires at 1–3 segments as well, which is incorrect. Fix: suppress the `[WARN]` for 1–3 images; retain it only for a 4th entry. Clarify the max-image threshold in a code comment. |

***

## Deferred — Post-Migration

### BUG-020
| Field | Value |
|---|---|
| **ID** | BUG-020 |
| **Title** | Multiple Events not grouped under a shared heading |
| **Status** | Deferred |
| **Area** | `compile_events.py` |
| **Symptom** | Event rows sharing a title or lead image in "Hosts with Multiple Events" each render as independent items rather than grouped under one heading. |
| **Cause / Fix** | No grouping logic in current compiler. Deferred until after migration. A host-level tagging pass in the preprocessor is the likely approach — design to be finalized post-migration. |

### BUG-021
| Field | Value |
|---|---|
| **ID** | BUG-021 |
| **Title** | No rotation of same-date bulletin items within a section |
| **Status** | Deferred |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Multiple bulletins in the same section with the same `Received` date always appear in CSV order. The same submitter is always first or last across every issue. |
| **Cause / Fix** | No rotation logic. CSV-based rotation planned; replace with SQL query at database migration. Deferred until after migration. |

### BUG-022
| Field | Value |
|---|---|
| **ID** | BUG-022 |
| **Title** | No `NEW` badge on first-appearance bulletin items |
| **Status** | Deferred |
| **Area** | `compile_bulletin.py` |
| **Symptom** | Items appearing for the first time are not visually distinguished from returning items. |
| **Cause / Fix** | No prior-issue comparison logic. Compare current intermediate CSV against prior issue's stored CSV. CSV-diff for now; replace with SQL at Phase 3. Deferred until after migration. |

***

## Resolved

### BUG-001
| Field | Value |
|---|---|
| **ID** | BUG-001 |
| **Title** | Callout boxes never prompted; operator had no signal to customize |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Builder called compilers with no `--callout` or `--bottom-callout` argument. Default callout text was used silently every issue. |
| **Cause / Fix** | `emit_callout_reminders()` added to orchestrator. `--callout` and `--bottom-callout` flags wired through entrypoint to both compilers. `[REMIND]` tag emitted when flags are absent. |

### BUG-002
| Field | Value |
|---|---|
| **ID** | BUG-002 |
| **Title** | Markdown links rendered as raw text in events email |
| **Status** | Fixed |
| **Area** | `ChucksEvents/events/preprocess_events_text.py` |
| **Symptom** | Links written as `[Label](url)` in the Events CSV appeared as literal bracketed text in output HTML. |
| **Cause / Fix** | `preprocess_events_text.py` was missing `QUOTE_ALL` on its `DictWriter`. Fix: `quoting=csv.QUOTE_ALL` added. |

### BUG-003
| Field | Value |
|---|---|
| **ID** | BUG-003 |
| **Title** | "here" link not rendering in events output |
| **Status** | Fixed |
| **Area** | `ChucksEvents/events/preprocess_events_text.py` |
| **Symptom** | A specific `[here](url)` Markdown link failed to render as a hyperlink. |
| **Cause / Fix** | Approximate — root cause was the same missing `QUOTE_ALL` as BUG-002. Resolved by the same fix. |

### BUG-004
| Field | Value |
|---|---|
| **ID** | BUG-004 |
| **Title** | All bulletins skipped; zero-item output exits 0 silently |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py` (originally); both preprocessors (final fix) |
| **Symptom** | Running the builder against a real LibreOffice CSV export produced zero items with no error. |
| **Cause / Fix** | `parse_date()` had no handler for the `M/D/YYYY` format LibreOffice Calc exports. Every row hit the fallthrough and was silently skipped. Fix: `DATE_RE_LONG` added at module level in both preprocessors. Zero-item output now exits non-zero. |

### BUG-005
| Field | Value |
|---|---|
| **ID** | BUG-005 |
| **Title** | Windows backslash paths written into HTML `src` and `href` |
| **Status** | Fixed |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | Image `src` and `href` attributes contained Windows-style backslash paths. Images failed to load in browsers and Zoho Campaigns. |
| **Cause / Fix** | `pathlib.Path` on Windows emits backslashes. Fix: `to_web_path()` helper added using `Path.as_posix()` + `urllib.parse.quote(..., safe="/:._-")`. |

### BUG-006
| Field | Value |
|---|---|
| **ID** | BUG-006 |
| **Title** | Pipe-delimited image field not split before render |
| **Status** | Fixed |
| **Area** | `compile_bulletin.py`, `compile_events.py` |
| **Symptom** | When an item had multiple images in the CSV, the entire pipe-joined string was passed directly into `src=`, producing a broken image tag. |
| **Cause / Fix** | `build_image_html()` in both compilers now splits the `Image` field on `\|` before rendering. Each entry gets its own `<img>/<a>` pair. A 4th pipe-segment triggers `[WARN]` and is dropped. Note: if the `[WARN]` fires incorrectly at fewer than 4 images, see BUG-028. |

### BUG-007
| Field | Value |
|---|---|
| **ID** | BUG-007 |
| **Title** | False-positive Markdown validation errors on valid URLs containing parentheses |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py` |
| **Symptom** | URLs with balanced parentheses in the body triggered `[ERROR]` validation failures. |
| **Cause / Fix** | Validator used naive parenthesis counting across the entire `Body` field. Fix: replaced with segment-targeted `[label](target)` structural parsing. |

### BUG-008
| Field | Value |
|---|---|
| **ID** | BUG-008 |
| **Title** | `--debug` flag not defined in argparse |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Passing `--debug` on the CLI caused an `unrecognized arguments` error. |
| **Cause / Fix** | `add_argument("--debug", action="store_true")` was missing. Added. |

### BUG-009
| Field | Value |
|---|---|
| **ID** | BUG-009 |
| **Title** | Unicode arrow `→` in preprocess success message crashes Windows console |
| **Status** | Fixed |
| **Area** | `preprocess_bulletin_text.py`, `preprocess_events_text.py` |
| **Symptom** | On Windows with cp1252 console encoding, the scripts crashed printing a `→` character. |
| **Cause / Fix** | Replaced `→` with ASCII `->` in both preprocess scripts. |

### BUG-010
| Field | Value |
|---|---|
| **ID** | BUG-010 |
| **Title** | Non-UTF-8 subprocess bytes crash builder on Python 3.14 |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | On Python 3.14, the subprocess reader raised `UnicodeDecodeError` when compile scripts emitted cp1252 bytes. |
| **Cause / Fix** | Added `errors="replace"` to `subprocess.run()`. Added `None` guards on `stdout` and `stderr` before `.strip()`. |

### BUG-011
| Field | Value |
|---|---|
| **ID** | BUG-011 |
| **Title** | `run_stage` return displaced outside function body — SyntaxError on import |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | Repeated in-place patches pushed the `return` statement outside `run_stage()`, producing a `SyntaxError` at import time. Pipeline appeared to run but did nothing. |
| **Cause / Fix** | Full rewrite of `Chucks_List_Builder.py` from scratch. Indentation corrected throughout. |

### BUG-012
| Field | Value |
|---|---|
| **ID** | BUG-012 |
| **Title** | `__main__` block called wrong function name and used wrong kwarg |
| **Status** | Fixed |
| **Area** | `Chucks_List_Builder.py` |
| **Symptom** | The bulletin pipeline's `__main__` call invoked `compile_events(...)` instead of `compile_bulletins(...)`. Bulletins were never compiled regardless of CLI flags. |
| **Cause / Fix** | Corrected function name to `compile_bulletins(...)`, kwarg to `top_callout=args.callout`, and indent to 4 spaces. |

### BUG-013
| Field | Value |
|---|---|
| **ID** | BUG-013 |
| **Title** | Events compiler skipping valid rows due to unrecognized section values |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | Valid event rows with `Section` values of `Single`, `Multiple`, or `Recurring` were silently skipped. |
| **Cause / Fix** | Approximate — section grouping logic checked for values that did not match canonical names. Fix: updated to accept `Single Events`, `Hosts with Multiple Events`, `Recurring Events`. |

### BUG-014
| Field | Value |
|---|---|
| **ID** | BUG-014 |
| **Title** | Events compiler not accepting `--callout` / `--bottom-callout` CLI flags |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | Passing `--callout` or `--bottom-callout` had no effect on events output. Events email always showed hardcoded default callout text. |
| **Cause / Fix** | `compile_events.py` did not define these flags in its argparse setup. Added with safe defaults matching the bulletin compiler pattern. |

### BUG-015
| Field | Value |
|---|---|
| **ID** | BUG-015 |
| **Title** | Events TOC structure did not match bulletin TOC |
| **Status** | Fixed |
| **Area** | `compile_events.py` |
| **Symptom** | The events email used a flat TOC list rather than the section-heading-with-linked-items structure used in the bulletin. |
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

***

*Chuck's List Builder — Bug Ledger*
*Append new entries at the bottom of the appropriate section. Never delete resolved entries.*