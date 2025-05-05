# JFK Assassination Records - Metadata Cleanup

This repository consolidates every spreadsheet the U.S. National Archives (NARA) has published for the JFK Assassination Records releases (2017–2025) and walks through a complete, reproducible cleanup:

1. Standardize column headers so every file shares the same schema.
2. Deduplicate rows while preserving legitimate one‑to‑many relationships.
3. Repair or remove broken hyperlinks and add PDFs missing from the spreadsheets but present on archives.gov.

## 📂 Directory Layout

| Folder                          | Description                                        |
|----------------------------------|----------------------------------------------------|
| `original/`                     | Raw .xlsx files from archives.gov                  |
| `standardized_columns/`         | Same files, columns harmonized only                |
| `standardized_columns_corrected/`| Final cleaned versions (duplicates merged, links fixed) |

## 1 · Why the Cleanup Matters

| Issue in the Raw Sheets                      | What We Fixed                                                                 |
|----------------------------------------------|-------------------------------------------------------------------------------|
| Duplicate filenames with different Record Numbers | Collapsed to one row, Record Numbers comma‑separated                         |
| Same PDF stored in several folders           | Counted as one logical file                                                  |
| Broken / missing links (2017‑2018)           | Removed six dead links, added two “additional” PDFs                          |
| Inconsistent column names                    | Mapped all sheets to a single header set                                     |

## 2 · Per-Release Result

| Release   | Rows → After Merge         | Notes                                                                                                 |
|-----------|---------------------------|-------------------------------------------------------------------------------------------------------|
| 2017–2018 | 54,636 → 53,547           | 198 multi‑record groups merged, 56 metadata‑diff groups merged, 1 exact duplicate dropped. Two “additional” PDFs added, six dead links removed. |
| 2021      | 1,491 → 1,486             | 5 duplicate filename groups merged.                                                                   |
| 2022      | 13,263 → 13,229           | 34 duplicate filename groups merged.                                                                  |
| 2023      | 2,693 → 2,693             | No duplicates - unchanged.                                                                            |
| 2025      | n/a → hand‑curated        | NARA supplied no spreadsheet; built from website list.                                                |

## 3 · Merge Logic (2017–2018 “Suspect Add-Info” Groups)

- **Text columns:**  
  - One value blank → keep the other  
  - One is substring of the other → keep the longer  
  - Otherwise, join with “, ”
- **Numeric columns:**  
  - Largest non‑blank value
- **Date columns:**  
  - Most recent date
- **Flags / Withheld status:**  
  - Keep the least restrictive label (“Released in Full” > “Redacted” > “Withheld”)

## 4 · Broken & Added Links List (2017–2018)

**Removed (404 on archives.gov):**
- 2018/124-10190-10078
- 2018/124-10188-10363
- 2018/124-10274-10080
- 124-10273-10088_00.pdf
- 124-10188-10365_00.pdf
- 124-10167-10393_00.pdf

**Added (present on website, absent from .xlsx):**
- additional/docid-32423629.pdf
- additional/docid-32423405.pdf
