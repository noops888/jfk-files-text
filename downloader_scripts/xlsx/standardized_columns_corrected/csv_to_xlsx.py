#!/usr/bin/env python3
"""
csv_to_xlsx_hyperlinks.py

Convert the deduped CSV (with a `URL` column) back to Excel, attaching each
URL as a hyperlink to the File Name cell (column A).

Usage:
    python csv_to_xlsx_hyperlinks.py input.csv output.xlsx
"""

import sys
import pandas as pd

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python csv_to_xlsx_hyperlinks.py input.csv output.xlsx")
        sys.exit(1)

    csv_path, xlsx_path = sys.argv[1], sys.argv[2]

    # Read the CSV as strings so nothing gets coerced
    df = pd.read_csv(csv_path, dtype=str).fillna("")

    # Locate the URL column (usually named exactly "URL")
    url_col = next((c for c in df.columns if c.lower() == "url"), None)
    if url_col is None:
        raise ValueError("Could not find a URL column in the CSV file.")

    # Create the workbook with xlsxwriter
    with pd.ExcelWriter(xlsx_path, engine="xlsxwriter") as writer:
        # Drop the URL column so it doesn’t appear twice
        df_no_url = df.drop(columns=[url_col])
        df_no_url.to_excel(writer, index=False, sheet_name="Sheet1")

        workbook  = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Attach each hyperlink to the File Name cell (row offset +1 for header)
        for row_idx, (url, fname) in enumerate(zip(df[url_col], df.iloc[:, 0]), start=1):
            if url:                     # skip blanks
                worksheet.write_url(row_idx, 0, url, string=fname)

    print(f"✔ Wrote {xlsx_path}")

if __name__ == "__main__":
    main()
