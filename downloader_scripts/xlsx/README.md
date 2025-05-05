# JFK Assassination Records — Metadata Cleanup

This repository consolidates every spreadsheet the U.S. National Archives (NARA)
has published for the JFK Assassination Records releases (2017–2025) and walks
through a complete, reproducible cleanup:
	1.	Standardise column headers so every file shares the same schema.
	2.	Deduplicate rows while preserving legitimate one‑to‑many relationships.
	3.	Repair or remove broken hyperlinks and add PDFs missing from the
spreadsheets but present on archives.gov.

## 📂 Directory layout

original/                       raw .xlsx files from archives.gov
standardized_columns/           same files, columns harmonised only
standardized_columns_corrected/ final cleaned versions (duplicates merged, links fixed)

## Why the cleanup matters

Issue in the raw sheets	What we fixed
Duplicate filenames with different Record Numbers	Collapsed to one row, Record Numbers comma‑separated
Same PDF stored in several folders (2018/, 08/, additional/)	Counted as one logical file
Broken / missing links (2017‑2018)	Removed six dead links, added two “additional” PDFs
Inconsistent column names	Mapped all sheets to a single header set

## Per‑release result

Release	Rows → after merge	Notes
2017‑2018	54 636 → 53 547	198 multi‑record groups merged, 56 metadata‑diff groups merged, 1 exact duplicate dropped. Two “additional” PDFs added, six dead links removed.
2021	1 491 → 1 486	5 duplicate filename groups merged.
2022	13 263 → 13 229	34 duplicate filename groups merged.
2023	2 693 → 2 693	No duplicates — unchanged.
2025	n/a → hand‑curated	NARA supplied no spreadsheet; built from website list.

## Merge logic (2017‑2018 “suspect add‑info” groups)
	•	Text columns
One value blank → keep the other; one is substring of the other → keep the longer; otherwise join with “, ”.
	•	Numeric columns
Largest non‑blank value.
	•	Date columns
Most recent date.
	•	Flags / Withheld status
Keep the least restrictive label (“Released in Full” > “Redacted” > “Withheld”).

## Outputs

All cleaned files live in standardized_columns_corrected/

File	Format	Notes
*_release_dedup.xlsx (2021, 2022)	Excel	Hyperlinks preserved
*_release_dedup.csv (2017‑2018)	CSV	URL column added
*_release_dedup_audit.csv	CSV	Row‑level merge log (original row numbers & merge type)
national‑archives‑jfk‑assassination‑records‑2023‑release.xlsx	Excel	Unchanged (no duplicates)
national‑archives‑jfk‑assassination‑records‑2025‑release.xlsx	Excel	Manually compiled — NARA did not release a spreadsheet

## Re‑running the workflow

All scripts live in scripts/.  Requirements:

python -m pip install pandas openpyxl xlsxwriter

Run:

python scripts/01_standardise_columns.py
python scripts/02_dedupe.py
python scripts/03_fix_2017_links.py   # removes 6 bad links, adds 2 missing PDFs

Scripts are idempotent: re‑running produces identical outputs.

## Broken & added links list (2017‑2018)

Removed (404 on archives.gov)

2018/124-10190-10078
2018/124-10188-10363
2018/124-10274-10080
124-10273-10088_00.pdf
124-10188-10365_00.pdf
124-10167-10393_00.pdf

Added (present on website, absent from .xlsx)

additional/docid-32423629.pdf
additional/docid-32423405.pdf
