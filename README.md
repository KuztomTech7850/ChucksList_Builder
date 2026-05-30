
### Canonical Bulletin Section Order

1. Urgent Bulletins
2. Housing Opportunities
3. Swap Market
4. Local Services & Help
5. Community Announcements

---

## Design Requirements

### Accessibility (Non-Negotiable)

Chuck's List serves elderly and low-vision readers. The HTML output must:

- Use large, readable text with generous line spacing
- Maintain strong color contrast throughout
- Use live text — important information must never be image-only
- Render clearly in email clients without JavaScript
- Use meaningful link text, not bare raw URLs

### Visual Identity

The color scheme reflects **Montezuma County / Mesa Verde, Colorado**:
warm earth tones, canyon reds, desert sage, and sandstone neutrals —
readable and dignified, not marketing-flashy.

### Images

- Included in email where present
- Clickable/openable in a new tab where appropriate
- Proper alt text required
- Path resolution must be consistent across both pipelines

### Text and Formatting

- Paragraph breaks are defined by blank lines (`\n\n`) in source text
- List-like blocks (lines starting with `- `, `* `, `•`) render as `<ul><li>`
- Plain-text authoring is the model — no Markdown literacy required from staff
- Poster-supplied spacing and formatting must survive into rendered output

### Table of Contents

- Every section/entry has a deterministic anchor
- TOC links must land the reader at the **top** of the correct entry
- Duplicate titles must not cause anchor collisions

---

## CLI Behavior

The builder is designed to guide the operator, not just fail.

- Date format errors produce a clear fix instruction
- Missing scripts produce a path-specific error message
- Stage failures stop the pipeline immediately with the error surfaced
- A build summary lists every passed and failed stage
- Failed builds explicitly warn: **do not upload partial output to Zoho**

---

## Long-Term Goals

### Website Platform — [mcafeefarm.biz](https://www.mcafeefarm.biz)

- Move publishing workflow to the web
- Staff login and admin content management
- Approved subscriber submission forms
- Moderation and review workflow
- Website listings generated from database records
- Email editions generated from database records

### Database Migration

- Store bulletins and events in a normalized database
- Support searchable bulletin boards, event calendars, and archives
- Preserve plain-text-first authoring in web forms
- Keep automation incremental with human validation at key steps

### Email Automation

- Continue using Zoho Campaigns for delivery in the near term
- Evaluate direct-send alternatives when the web platform is stable
- Generate email editions from database records instead of CSV exports

---

## Guiding Principles

- **Boring beats clever.** Deterministic transforms over magic.
- **Plain text first.** Staff paste from email — the system adapts.
- **Explicit pipelines.** Bulletins and Events stay separate and documented.
- **Accessibility is core.** Not a polish pass — built in from the start.
- **One command.** The full local build runs from one CLI call.
- **Guide, don't just fail.** CLI output tells the operator what to fix.
- **Validate before redesigning.** Understand what exists before changing it.

---

## Staged Migration Roadmap

| Stage | Goal | Status |
|---|---|---|
| 1 | Document and stabilize current scripts | 🔄 In progress |
| 2 | Mirror CSV data into a database | ⬜ Planned |
| 3 | Build admin UI on mcafeefarm.biz | ⬜ Planned |
| 4 | Generate website listings from database | ⬜ Planned |
| 5 | Generate email editions from database | ⬜ Planned |
| 6 | Retire CSV dependence when safe | ⬜ Planned |

---

## Contributing / Engineering Notes

- Read existing scripts before proposing changes
- Do not assume current code is fully working — treat every engagement as a validation
- Validate against real CSV exports and real issue dates
- Prefer full-file replacements over speculative partial patches
- Label every file you touch with its role in the pipeline
- Write concise engineer-facing comments and docstrings
- Do not push complexity ahead of proven need

---

*Chuck's List Builder — Montezuma County community publishing.*
*Reliable. Readable. One command.*