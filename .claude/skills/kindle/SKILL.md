---
name: kindle
description: Prepare a PDF for Kindle — clean margins, convert to EPUB, open in Kindle Previewer 3
argument-hint: "<path_to_pdf>"
allowed-tools:
  - Bash
---

Format a PDF for Kindle using the path provided in $ARGUMENTS.

**Pre-flight check** — verify Calibre is installed:
```bash
which ebook-convert
```
If missing, tell the user: "Calibre must be installed. Download from https://calibre-ebook.com and ensure `ebook-convert` is on your PATH."

**Run the formatter** from the repo root:
```bash
uv run .claude/skills/kindle/scripts/kindle.py <absolute_pdf_path>
```

The pipeline:
1. Analyzes embedded images for low-resolution warnings
2. Crops 10% from top and bottom of every page (removes headers/footers)
3. Extracts or renders the cover image
4. Converts to EPUB via Calibre (`ebook-convert`)
5. Opens the EPUB in Kindle Previewer 3 (macOS)

All output files are written to a timestamped directory next to the source PDF
(e.g. `mybook_20260502_143201/`).

Report the output EPUB path. If there were low-resolution image warnings, surface them
with the count and affected page numbers.
