#!/usr/bin/env python3
"""
add_metadata.py
===============

• Injects YAML front‑matter (built 1‑to‑1 from every spreadsheet column)
  into each markdown file, dropping the old “# filename” heading.

• Writes the transformed files to a MIRROR tree under the output root.

• Records any .md that had no matching spreadsheet row in
    <out_root>/unmatched_no_meta.txt

USAGE ── run from anywhere
──────────────────────────
python add_metadata.py \
       --root   /path/to/markdown/root \
       --sheets "/path/to/sheets/*.xlsx"  "/more/*.xlsx" \
       --out    /path/for/converted_files

If you omit an option:
  --root   defaults to "."            (current dir)
  --sheets defaults to "*.xlsx"       (in --root)
  --out    defaults to "<root>/yaml_ready"
"""

from pathlib import Path
import argparse, openpyxl, os, sys, glob

# ──────────────────────────────────────────────────────────────────────────────
# 1. Command‑line arguments
# ──────────────────────────────────────────────────────────────────────────────
cli = argparse.ArgumentParser(description="Inject YAML front‑matter into .md files.")
cli.add_argument("--root",   default=".", help="root folder containing markdown files")
cli.add_argument("--sheets", nargs="+", default=["*.xlsx"],
                 help="one or more .xlsx paths OR glob patterns OR directories")
cli.add_argument("--out",    default=None, help="output root for the mirrored tree")
args = cli.parse_args()

ROOT_DIR = Path(args.root).expanduser().resolve()
if not ROOT_DIR.is_dir():
    sys.exit(f"[ERROR] --root folder not found: {ROOT_DIR}")

# Expand --sheets patterns & directories → concrete file list
sheet_paths = []
for pattern in args.sheets:
    p = Path(pattern).expanduser()
    if p.is_dir():
        sheet_paths.extend(p.glob("*.xlsx"))
    else:
        sheet_paths.extend(Path(x).resolve() for x in glob.glob(str(p), recursive=True))

sheet_paths = [p for p in sheet_paths if p.suffix.lower() == ".xlsx"]
if not sheet_paths:
    sys.exit("[ERROR] No .xlsx files matched the --sheets argument(s).")

OUT_ROOT = Path(args.out).expanduser().resolve() if args.out else ROOT_DIR / "yaml_ready"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2. Build spreadsheet‑lookup  (basename → row‑dict)
# ──────────────────────────────────────────────────────────────────────────────
def build_lookup(paths):
    lookup = {}
    for xlsx in paths:
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        ws = wb.active
        header = [h.strip() if h else "" for h in next(ws.iter_rows(values_only=True))]
        try:
            idx = header.index("File Name")
        except ValueError:
            print(f"[WARN] 'File Name' column not found in {xlsx.name}; skipped.")
            continue
        for row in ws.iter_rows(values_only=True):
            fname = row[idx]
            if not fname:
                continue
            key = Path(str(fname)).stem.lower()
            if key not in lookup:           # first sheet wins
                lookup[key] = dict(zip(header, row))
    return lookup

META = build_lookup(sheet_paths)

# ──────────────────────────────────────────────────────────────────────────────
# 3. Helper functions
# ──────────────────────────────────────────────────────────────────────────────
def make_yaml(meta: dict[str, str]) -> list[str]:
    out = ["---"]
    for k, v in meta.items():
        key = k.lower().replace(" ", "_")
        val = "" if v is None else str(v)
        if ":" in val:
            val = f'"{val}"'
        out.append(f"{key}: {val}")
    out.append("---")
    return out

def transform(md: Path, unmatched: list[str]) -> str:
    key  = md.stem.lower()
    meta = META.get(key, {})
    if not meta:
        unmatched.append(str(md.relative_to(ROOT_DIR)))

    lines = md.read_text(encoding="utf‑8").splitlines()
    body_start = 1 + (len(lines) > 1 and lines[1].strip() == "")
    body = lines[body_start:]
    return "\n".join(make_yaml(meta) + [""] + body)

def write_mirror(src: Path, text: str):
    dst = OUT_ROOT / src.relative_to(ROOT_DIR)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf‑8")

# ──────────────────────────────────────────────────────────────────────────────
# 4. Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    os.environ.update({              # tame OpenBLAS threading spam
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })

    unmatched = []
    processed = 0
    for md in ROOT_DIR.rglob("*.md"):
        if md.is_relative_to(OUT_ROOT):
            continue                 # skip already‑converted copies
        new_text = transform(md, unmatched)
        write_mirror(md, new_text)
        processed += 1

    list_path = OUT_ROOT / "unmatched_no_meta.txt"
    list_path.write_text("\n".join(unmatched), encoding="utf‑8")

    # robust summary printing
    try:
        display_path = list_path.relative_to(ROOT_DIR)
    except ValueError:
        display_path = list_path
    print(f"✅  Processed {processed:,} markdown file(s).")
    print(f"📝  {len(unmatched)} file(s) lacked spreadsheet metadata "
          f"(see {display_path})")

if __name__ == "__main__":
    main()